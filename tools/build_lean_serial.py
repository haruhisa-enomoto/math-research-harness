"""Build Lake's out-of-date dependency frontier one target at a time.

Lake remains responsible for dependency discovery and cache validity. Each
--no-build probe reports the first outdated targets on dependency branches;
their prerequisites are current, so building them individually avoids launching
several compiler processes. Requires the pinned Lake 5 diagnostic format and
GNU time. Logs and per-invocation peak RSS (KiB) are retained in --output.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import tempfile
import time


def pending_targets(output: str) -> list[str]:
    """Reject unknown failures instead of mistaking them for outdated modules."""
    errors = [line for line in output.splitlines() if line.startswith("error:")]
    if not errors or any(
        line != "error: target is out-of-date and needs to be rebuilt"
        for line in errors
    ):
        raise RuntimeError("Lake probe failed for a reason other than stale targets")
    marker = "Some required targets logged failures:\n"
    if marker not in output:
        raise RuntimeError("Lake did not report its outdated dependency frontier")
    lines = output.rsplit(marker, 1)[1].splitlines()
    targets = [line[2:] for line in lines if line.startswith("- ")]
    if not targets or any(not re.fullmatch(r"[\w.]+", t) for t in targets):
        raise RuntimeError("Unexpected Lake target syntax; inspect the probe log")
    return list(dict.fromkeys(targets))


def process_tree_usage(pid: int) -> tuple[int, int, int]:
    """Sample tree RSS, Lean RSS, and Lean compiler count below `pid`.

    Summed RSS counts shared pages more than once; it is a conservative estimate
    of the build's physical footprint, not proportional set size.
    """
    listing = subprocess.check_output(
        ["ps", "-eo", "pid=,ppid=,rss=,comm="], text=True
    )
    processes = [line.split(maxsplit=3) for line in listing.splitlines()]
    descendants = {pid}
    while True:
        expanded = descendants | {
            int(p) for p, parent, _, _ in processes if int(parent) in descendants
        }
        if expanded == descendants:
            break
        descendants = expanded
    selected = [(int(rss), name) for p, _, rss, name in processes
                if int(p) in descendants]
    return (
        sum(rss for rss, _ in selected),
        sum(rss for rss, name in selected if name == "lean"),
        sum(name == "lean" for _, name in selected),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--max-rss-kib",
        type=int,
        help="terminate the current isolated build step if sampled tree RSS exceeds this limit",
    )
    parser.add_argument("targets", nargs="+")
    args = parser.parse_args()
    package = args.package.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    # Each invocation has its own directory, preserving earlier failed attempts.
    run = Path(tempfile.mkdtemp(prefix="run-", dir=output))
    print(f"Build logs: {run}", flush=True)
    lake = ["lake", "--no-ansi", "--log-level=error"]
    version = subprocess.check_output(["lake", "env", "lean", "--version"],
                                      cwd=package, text=True).strip()
    with (run / "invocation.json").open("w") as handle:
        json.dump({"package": str(package), "targets": args.targets,
                   "lean_version": version}, handle)
    with (run / "metrics.jsonl").open("w") as metrics:
        step = 0
        while True:
            probe = subprocess.run(
                [*lake, "--no-build", "build", *args.targets],
                cwd=package, text=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            (run / f"probe-{step}.log").write_text(probe.stdout)
            if probe.returncode == 0:
                (run / "result.json").write_text(json.dumps(
                    {"exit": 0, "rebuilt_targets": step,
                     "validation_command": [*lake, "--no-build", "build", *args.targets]}
                ) + "\n")
                print("All requested targets are current; Lake validation passed.", flush=True)
                return
            if probe.returncode != 3:
                raise RuntimeError(f"Lake probe exited {probe.returncode}; see {run}")
            frontier = pending_targets(probe.stdout)
            print(f"Outdated frontier: {len(frontier)} targets", flush=True)
            for target in frontier:
                step += 1
                log = run / f"{step}-{target}.log"
                timing = run / f"{step}-{target}.time.json"
                command = [*lake, "build", f"+{target}"]
                print(f"[{step}] {target}", flush=True)
                start = time.monotonic()
                tree_peak = 0
                lean_peak = 0
                compiler_peak = 0
                with log.open("w") as handle:
                    process = subprocess.Popen(
                        ["/usr/bin/time", "-f", '{"peak_rss_kib":%M,"exit":%x}',
                         "-o", str(timing), *command],
                        cwd=package, stdout=handle, stderr=subprocess.STDOUT,
                        start_new_session=True,
                    )
                    try:
                        while process.poll() is None:
                            tree_rss, lean_rss, compilers = process_tree_usage(process.pid)
                            tree_peak = max(tree_peak, tree_rss)
                            lean_peak = max(lean_peak, lean_rss)
                            compiler_peak = max(compiler_peak, compilers)
                            if (args.max_rss_kib is not None and
                                    lean_rss > args.max_rss_kib):
                                raise RuntimeError(
                                    f"Lean compiler exceeded RSS limit: {lean_rss} KiB > "
                                    f"{args.max_rss_kib} KiB"
                                )
                            if compilers > 1:
                                raise RuntimeError("Lake launched multiple Lean compilers; "
                                                   "the dependency frontier was not serial")
                            time.sleep(1)
                    except BaseException:
                        # Stop only this invocation's isolated process group,
                        # including the compiler, if interrupted or monitoring fails.
                        try:
                            os.killpg(process.pid, signal.SIGTERM)
                        except ProcessLookupError:
                            pass
                        process.wait()
                        raise
                # GNU time prefixes a diagnostic when the subprocess fails.
                measurement = json.loads(timing.read_text().splitlines()[-1])
                measurement.update(target=target, command=command,
                                   sampled_tree_peak_rss_kib=tree_peak,
                                   sampled_lean_peak_rss_kib=lean_peak,
                                   sampled_max_lean_processes=compiler_peak,
                                   elapsed_seconds=round(time.monotonic() - start, 2))
                metrics.write(json.dumps(measurement) + "\n")
                metrics.flush()
                print(f"  exit {process.returncode}; peak "
                      f"{measurement['peak_rss_kib'] / 1048576:.2f} GiB; "
                      f"{measurement['elapsed_seconds']} s", flush=True)
                if process.returncode:
                    raise RuntimeError(f"Build failed; see {log}")


if __name__ == "__main__":
    main()
