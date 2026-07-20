# Literature-tool environment

The included literature utilities use Python through `uv` plus ordinary
command-line tools.

## Base requirements

Install `uv` to run the bundled Python utilities. Run `uv sync` to install
PyMuPDF and FontTools from `uv.lock`. The arXiv fetcher also requires `curl`; it
performs no search and fetches one known item at a time.

## PDF support

Synchronize the declared Python dependencies:

```bash
uv sync
```

This provides native PDF text extraction and page rendering.

Run the offline unit and local integration tests:

```bash
uv run python -m unittest discover -s tests
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
