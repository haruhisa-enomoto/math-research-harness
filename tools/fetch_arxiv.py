from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Callable
from urllib.parse import urlparse

try:
    from tools.reference_catalog import audit_items, refresh_catalog_items
    from tools.reference_utils import sha256, write_json_atomic
except ModuleNotFoundError:  # Direct execution starts with tools/ on sys.path.
    from reference_catalog import audit_items, refresh_catalog_items
    from reference_utils import sha256, write_json_atomic


def describe_item(root: Path, item_id: str) -> None:
    """Extract bibliographic identity for one freshly filed item.

    The repository citation scan is skipped here; a full
    `tools/reference_metadata.py` run refreshes it.
    """
    try:
        from tools.reference_metadata import refresh_items
    except ModuleNotFoundError:
        from reference_metadata import refresh_items
    refresh_items(
        root,
        Path(__file__).resolve().parents[1],
        only=item_id,
        scan_citations=False,
        update_catalog=False,
    )


MODERN_ID = re.compile(r"\d{4}\.\d{4,5}(?:v\d+)?", re.IGNORECASE)
OLD_ID = re.compile(r"[a-z][a-z0-9.-]*/\d{7}(?:v\d+)?", re.IGNORECASE)
VERSION = re.compile(r"v\d+$", re.IGNORECASE)
MAX_ARCHIVE_MEMBERS = 20_000
MAX_ARCHIVE_BYTES = 2 * 1024 * 1024 * 1024
DEFAULT_USER_AGENT = os.environ.get(
    "RESEARCH_HARNESS_USER_AGENT",
    "math-research-harness/0.1 (literature helper)",
)


def normalize_arxiv_id(value: str) -> str:
    """Return a validated identifier from an identifier or official item URL."""
    candidate = value.strip()
    if candidate.casefold().startswith("arxiv:"):
        candidate = candidate.split(":", 1)[1].strip()

    if "://" in candidate:
        parsed = urlparse(candidate)
        if parsed.netloc.casefold() not in {"arxiv.org", "www.arxiv.org", "export.arxiv.org"}:
            raise ValueError(f"not an arXiv URL: {value!r}")
        path = parsed.path.strip("/")
        for prefix in ("abs/", "pdf/", "e-print/"):
            if path.startswith(prefix):
                candidate = path[len(prefix) :]
                break
        else:
            raise ValueError(f"arXiv URL has no abs/pdf/e-print identifier: {value!r}")

    candidate = candidate.removesuffix(".pdf").strip("/")
    if not (MODERN_ID.fullmatch(candidate) or OLD_ID.fullmatch(candidate)):
        raise ValueError(f"invalid arXiv identifier: {value!r}")
    return candidate


def item_key(arxiv_id: str) -> str:
    return arxiv_id.casefold().replace("/", "-")


def read_headers(path: Path) -> dict[str, str]:
    headers: dict[str, str] = {}
    for raw_line in path.read_text(encoding="iso-8859-1").splitlines():
        line = raw_line.strip()
        if line.startswith("HTTP/"):
            headers = {":status": line}
        elif ":" in line:
            name, value = line.split(":", 1)
            headers[name.casefold().strip()] = value.strip()
    return headers


def curl_download(
    url: str,
    destination: Path,
    headers: Path,
    *,
    user_agent: str = DEFAULT_USER_AGENT,
) -> dict[str, object]:
    """Download one direct resource with restrained retry behavior."""
    command = [
        "curl",
        "--fail-with-body",
        "--location",
        "--retry",
        "2",
        "--retry-delay",
        "5",
        "--connect-timeout",
        "20",
        "--max-time",
        "600",
        "--user-agent",
        user_agent,
        "--dump-header",
        str(headers),
        "--output",
        str(destination),
        "--write-out",
        "%{url_effective}\n%{http_code}\n",
        url,
    ]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    output = completed.stdout.rstrip("\n").splitlines()
    return {
        "request_url": url,
        "effective_url": output[-2] if len(output) >= 2 else url,
        "http_status": output[-1] if output else "unknown",
        "headers": read_headers(headers),
    }


def safe_extract(archive: tarfile.TarFile, destination: Path) -> list[str]:
    """Extract regular files and directories without trusting archive paths."""
    members = archive.getmembers()
    if len(members) > MAX_ARCHIVE_MEMBERS:
        raise RuntimeError("source archive contains too many entries")
    if sum(max(member.size, 0) for member in members) > MAX_ARCHIVE_BYTES:
        raise RuntimeError("source archive declares too much uncompressed data")

    destination.mkdir(parents=True, exist_ok=True)
    destination_resolved = destination.resolve()
    extracted: list[str] = []
    seen: set[Path] = set()
    for member in members:
        path = PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts or "\\" in member.name:
            raise RuntimeError(f"unsafe path in arXiv source archive: {member.name!r}")
        if member.issym() or member.islnk() or member.isdev():
            raise RuntimeError(f"unsupported special entry in arXiv source archive: {member.name!r}")
        target = destination.joinpath(*path.parts).resolve()
        if not target.is_relative_to(destination_resolved):
            raise RuntimeError(f"unsafe extraction target: {member.name!r}")
        if target in seen and member.isfile():
            raise RuntimeError(f"duplicate file in source archive: {member.name!r}")
        seen.add(target)

        if member.isdir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        if not member.isfile():
            raise RuntimeError(f"unsupported archive entry: {member.name!r}")
        source = archive.extractfile(member)
        if source is None:
            raise RuntimeError(f"cannot read archive entry: {member.name!r}")
        target.parent.mkdir(parents=True, exist_ok=True)
        with source, target.open("wb") as output:
            shutil.copyfileobj(source, output)
        extracted.append(target.relative_to(destination).as_posix())
    return sorted(extracted)


def identify_source(path: Path) -> str:
    with path.open("rb") as handle:
        prefix = handle.read(8)
    if prefix.startswith(b"%PDF-"):
        return "pdf"
    try:
        with tarfile.open(path, "r:*") as archive:
            archive.getmembers()
        return "tar-gzip" if prefix.startswith(b"\x1f\x8b") else "tar"
    except tarfile.TarError:
        pass
    if prefix.startswith(b"\x1f\x8b"):
        return "gzip"
    return "tex"


def install_source(download: Path, original: Path, source: Path) -> tuple[Path, list[str]]:
    kind = identify_source(download)
    stored = original / {
        "pdf": "source.pdf",
        "tar-gzip": "source.tar.gz",
        "tar": "source.tar",
        "gzip": "source.tex.gz",
        "tex": "source.tex",
    }[kind]
    stored.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(download, stored)

    extracted: list[str] = []
    if kind.startswith("tar"):
        with tarfile.open(download, "r:*") as archive:
            extracted = safe_extract(archive, source)
    elif kind == "gzip":
        source.mkdir(parents=True, exist_ok=True)
        target = source / "arxiv-source.tex"
        with gzip.open(download, "rb") as compressed, target.open("wb") as output:
            shutil.copyfileobj(compressed, output)
        extracted = [target.relative_to(source).as_posix()]
    elif kind == "tex":
        source.mkdir(parents=True, exist_ok=True)
        target = source / "arxiv-source.tex"
        shutil.copy2(download, target)
        extracted = [target.relative_to(source).as_posix()]
    return stored, extracted


def main_tex_candidates(source: Path) -> list[str]:
    scored: list[tuple[int, str]] = []
    if not source.is_dir():
        return []
    for path in source.rglob("*.tex"):
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        score = 0
        if "\\documentclass" in content:
            score += 8
        if "\\begin{document}" in content:
            score += 4
        if path.stem.casefold() in {"main", "paper", "article", "manuscript"}:
            score += 2
        score += min(len(content) // 100_000, 2)
        scored.append((score, path.relative_to(source).as_posix()))
    return [name for _, name in sorted(scored, key=lambda pair: (-pair[0], pair[1]))]


Download = Callable[[str, Path, Path], dict[str, object]]


def fetch(
    value: str,
    *,
    root: Path = Path("references"),
    want_source: bool = True,
    want_pdf: bool = True,
    force: bool = False,
    downloader: Download | None = None,
    user_agent: str = DEFAULT_USER_AGENT,
    update_catalog: bool = True,
    invocation: list[str] | None = None,
) -> dict[str, object]:
    arxiv_id = normalize_arxiv_id(value)
    key = item_key(arxiv_id)
    root = root.resolve()
    item = root / "items" / "arxiv" / key
    metadata_path = item / "item.json"
    previous: dict[str, object] = {}
    if metadata_path.is_file() and not force:
        previous = json.loads(metadata_path.read_text(encoding="utf-8"))

    previous_resources = previous.get("resources", {})
    resources = dict(previous_resources) if isinstance(previous_resources, dict) else {}
    extracted = list(previous.get("extracted_source_files", []))
    downloaded_this_run = False
    download = downloader or (
        lambda url, destination, headers: curl_download(
            url, destination, headers, user_agent=user_agent
        )
    )

    # Build the complete item beside the destination, then commit it with
    # same-filesystem renames. A failed source/PDF request must not leave an
    # orphan directory that makes the catalog unauditable, and --force must
    # not destroy a valid existing item before its replacement is ready.
    root.mkdir(parents=True, exist_ok=True)
    item.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".fetch-arxiv-", dir=root) as temporary_raw:
        temporary = Path(temporary_raw)
        staged_item = temporary / "item"
        if item.exists() and metadata_path.is_file() and not force:
            shutil.copytree(item, staged_item)
        else:
            staged_item.mkdir()

        original = staged_item / "original"
        source = staged_item / "source"
        staged_metadata_path = staged_item / "item.json"
        original.mkdir(parents=True, exist_ok=True)

        def final_path(staged_path: Path) -> str:
            destination = item / staged_path.relative_to(staged_item)
            return destination.relative_to(root).as_posix()

        if want_source:
            existing_sources = sorted(original.glob("source.*"))
            if existing_sources and not force:
                stored_source = existing_sources[0]
                cached = resources.get("source", {})
                resources["source"] = {
                    **(cached if isinstance(cached, dict) else {}),
                    "status": "cached",
                    "path": final_path(stored_source),
                    "sha256": (
                        cached.get("sha256")
                        if isinstance(cached, dict) and isinstance(cached.get("sha256"), str)
                        else sha256(stored_source)
                    ),
                    "bytes": stored_source.stat().st_size,
                }
            else:
                source_download = temporary / "source.download"
                headers = temporary / "source.headers"
                network = download(
                    f"https://arxiv.org/e-print/{arxiv_id}", source_download, headers
                )
                stored_source, extracted = install_source(source_download, original, source)
                resources["source"] = {
                    "status": "downloaded",
                    "path": final_path(stored_source),
                    "sha256": sha256(stored_source),
                    "bytes": stored_source.stat().st_size,
                    **network,
                }
                downloaded_this_run = True

        if want_pdf:
            stored_pdf = original / "paper.pdf"
            if stored_pdf.exists() and not force:
                cached = resources.get("pdf", {})
                resources["pdf"] = {
                    **(cached if isinstance(cached, dict) else {}),
                    "status": "cached",
                    "path": final_path(stored_pdf),
                    "sha256": (
                        cached.get("sha256")
                        if isinstance(cached, dict) and isinstance(cached.get("sha256"), str)
                        else sha256(stored_pdf)
                    ),
                    "bytes": stored_pdf.stat().st_size,
                }
            else:
                pdf_download = temporary / "paper.pdf"
                headers = temporary / "pdf.headers"
                network = download(f"https://arxiv.org/pdf/{arxiv_id}", pdf_download, headers)
                with pdf_download.open("rb") as handle:
                    if not handle.read(5).startswith(b"%PDF-"):
                        raise RuntimeError("arXiv PDF download did not return a PDF")
                shutil.copy2(pdf_download, stored_pdf)
                resources["pdf"] = {
                    "status": "downloaded",
                    "path": final_path(stored_pdf),
                    "sha256": sha256(stored_pdf),
                    "bytes": stored_pdf.stat().st_size,
                    **network,
                }
                downloaded_this_run = True

        checked_at = datetime.now().astimezone().isoformat(timespec="seconds")
        # Bibliographic enrichment written by tools/reference_metadata.py survives
        # a re-file; only download provenance is rewritten here.
        carried = {
            name: previous[name]
            for name in (
                "bibliographic_identity",
                "metadata_provenance",
                "aliases",
                "derivatives",
                "citations",
                "citation_count",
                "search_text",
                "metadata_refreshed_at",
            )
            if name in previous
        }
        payload: dict[str, object] = {
            **carried,
            "schema_version": 2,
            "id": f"arxiv:{key}",
            "kind": "arxiv",
            "key": key,
            "arxiv_id": arxiv_id,
            "versioned": bool(VERSION.search(arxiv_id)),
            "downloaded_at": (
                checked_at if downloaded_this_run else previous.get("downloaded_at", checked_at)
            ),
            "checked_at": checked_at,
            "item_path": item.relative_to(root).as_posix(),
            "resources": resources,
            "extracted_source_files": extracted,
            "main_tex_candidates": main_tex_candidates(source),
            "invocation": invocation or ["tools/fetch_arxiv.py", value],
        }
        write_json_atomic(staged_metadata_path, payload)

        previous_item = temporary / "previous-item"
        if item.exists():
            item.rename(previous_item)
        try:
            staged_item.rename(item)
        except BaseException:
            if previous_item.exists() and not item.exists():
                previous_item.rename(item)
            raise

    # Describe the committed item even inside a batch, so a fetched source is
    # searchable by author and title without a separate full metadata run.
    if downloaded_this_run or not isinstance(previous.get("bibliographic_identity"), dict):
        describe_item(root, f"arxiv:{key}")

    catalog_result: dict[str, object] | None = None
    audit_result: dict[str, object] | None = None
    if update_catalog:
        catalog_result = refresh_catalog_items(root, [item])
        audit_result = audit_items(root, [item])

    return {
        "arxiv_id": arxiv_id,
        "version_warning": (
            None if payload["versioned"] else "unversioned identifier; hashes pin downloaded bytes"
        ),
        "item": item.relative_to(root).as_posix(),
        "main_tex_candidates": payload["main_tex_candidates"],
        "resources": resources,
        "catalog": catalog_result,
        "audit": audit_result,
    }


def fetch_many(
    values: list[str],
    *,
    root: Path = Path("references"),
    want_source: bool = True,
    want_pdf: bool = True,
    force: bool = False,
    downloader: Download | None = None,
    user_agent: str = DEFAULT_USER_AGENT,
    invocation: list[str] | None = None,
) -> dict[str, object]:
    """Fetch known arXiv items sequentially, then catalog the completed items."""
    if not values:
        raise ValueError("at least one arXiv identifier is required")

    # Reject a malformed batch before making any network request or filesystem change.
    normalized = [normalize_arxiv_id(value) for value in values]
    root = root.resolve()
    results: list[dict[str, object]] = []
    catalog_result: dict[str, object] | None = None
    try:
        for arxiv_id in normalized:
            results.append(
                fetch(
                    arxiv_id,
                    root=root,
                    want_source=want_source,
                    want_pdf=want_pdf,
                    force=force,
                    downloader=downloader,
                    user_agent=user_agent,
                    update_catalog=False,
                    invocation=invocation
                    or ["tools/fetch_arxiv.py", *values],
                )
            )
    finally:
        # Keep successfully completed earlier items discoverable if a later fetch fails.
        completed_items = [root / str(result["item"]) for result in results]
        if completed_items:
            catalog_result = refresh_catalog_items(root, completed_items)

    audit_result = audit_items(root, completed_items)
    return {
        "items": results,
        "catalog": catalog_result,
        "audit": audit_result,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "File known arXiv items by sequential direct source/PDF download; performs no search."
        )
    )
    parser.add_argument(
        "identifiers",
        nargs="+",
        help="one or more arXiv identifiers or official abs/pdf/e-print URLs",
    )
    parser.add_argument("--root", type=Path, default=Path("references"))
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--source-only", action="store_true")
    selection.add_argument("--pdf-only", action="store_true")
    parser.add_argument("--force", action="store_true", help="replace this exact local item")
    parser.add_argument(
        "--user-agent",
        default=DEFAULT_USER_AGENT,
        help="HTTP User-Agent; may also be set with RESEARCH_HARNESS_USER_AGENT",
    )
    args = parser.parse_args()

    common = {
        "root": args.root,
        "want_source": not args.pdf_only,
        "want_pdf": not args.source_only,
        "force": args.force,
        "user_agent": args.user_agent,
        "invocation": ["tools/fetch_arxiv.py", *sys.argv[1:]],
    }
    if len(args.identifiers) == 1:
        result = fetch(args.identifiers[0], **common)
    else:
        result = fetch_many(args.identifiers, **common)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
