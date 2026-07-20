# Optional literature-tool environment

The included literature utilities use Python through `uv` plus ordinary
command-line tools.

## Base requirements

Install `uv` to run the bundled Python utilities. The arXiv fetcher also
requires `curl`; it performs no search and fetches one known item at a time.

## PDF support

Synchronize the optional literature dependencies declared by the project and
locked in `uv.lock`:

```bash
uv sync --extra literature
```

This provides native PDF text extraction and page rendering.

After installing the literature extra, run the offline unit and local
integration tests:

```bash
uv run --extra literature python -m unittest discover -s tests
```

## Optional scan and DjVu support

OCR and DjVu preparation use external programs when those modes are requested:

- OCR: `ocrmypdf` and `tesseract`;
- DjVu metadata/text: `djvused` and `djvutxt`;
- DjVu rendering for OCR: `ddjvu`.

The preflight reports what is available without installing, building, or
starting anything:

```bash
uv run --extra literature python tools/literature_preflight.py
```

Missing optional components do not prevent the rest of the harness from being
used.
