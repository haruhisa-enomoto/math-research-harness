# Tool environment

The included utilities use Python through `uv` plus ordinary command-line
tools.

## Computational backends

Record here the engine or engines this project computes with: what each one
owns, how it is invoked, which versions are pinned, and what preflight checks
it before a session depends on it. `docs/COMPUTATIONS.md` explains why that
boundary matters; this file is where the concrete answer lives.

The starter template pins no mathematical backend. When a project adopts one,
add its installation requirements to the table in `README.md`, describe its
invocation here, and add a preflight command alongside
`tools/literature_preflight.py` so that a session can check availability
without starting real work.

## Base requirements

Install `uv` to run the bundled Python utilities. Run `uv sync` to install
PyMuPDF and FontTools from `uv.lock`. The arXiv fetcher also requires `curl`; it
performs no search and fetches explicitly supplied items sequentially. The
Hexagon fetcher uses Hexagon's public read-only API in the same way.

## PDF support

Synchronize the declared Python dependencies:

```bash
uv sync
```

This provides native PDF text extraction and page rendering.

Run the offline unit and local integration tests:

```bash
uv run pytest -q
```

## Optional scan and DjVu support

OCR and DjVu preparation use external programs when those modes are requested:

- OCR: `ocrmypdf` and `tesseract`;
- DjVu metadata/text: `djvused` and `djvutxt`;
- DjVu rendering for OCR: `ddjvu`.

The DjVu integration test also uses `c44` to construct its fixture. It is not
needed for normal source preparation. Tests whose system tools are unavailable
are skipped.

The preflight reports what is available without installing, building, or
starting anything:

```bash
uv run python tools/literature_preflight.py
```

Missing optional components do not prevent the rest of the harness from being
used.

## Lean formalizations

A project that formalizes results in Lean keeps each Lean package under
`formalization/` with its own tracked `lean-toolchain`, `lakefile.toml`, and
`lake-manifest.json`, and its untracked project build under `.lake/build/`. The
project build is package-specific and must not be shared between
formalizations.

Dependency builds under `.lake/packages/` may be shared when both the Lean
toolchain and the complete dependency closure agree. Keep such a shared cache
in a neutral, disposable directory outside the repository (for example
`~/.cache/lean-shared/<toolchain>-deps-<closure-hash>/packages/`) and link each
compatible package's `.lake/packages` to it. These links and all `.lake/`
contents are ignored machine state. A new toolchain or dependency closure gets
a new cache directory rather than mutating an incompatible one.

Normal builds use the committed manifest and do not run `lake update`. On a
machine without a shared cache, fetch Mathlib's precompiled cache from the
package directory before building:

```bash
lake exe cache get
lake build <package-target>
```

Run `lake update` only when intentionally changing dependency pins, and commit
the resulting manifest change with that update.

When a full build would launch too many compiler processes for the machine,
`tools/build_lean_serial.py` builds Lake's out-of-date frontier one target at a
time and keeps logs and per-target peak memory. It needs GNU `time`.

## Adding dependencies

Agents may add a suitable maintained Python package when a concrete task
benefits from it; prefer a dependable existing library to reimplementing a
commodity algorithm. Declare a reusable dependency with `uv add` so that it
enters `pyproject.toml` and `uv.lock`, and keep it only when the measured or
maintenance benefit justifies it.
