# Local source workspace

This directory is ignored except for this guide. Create subdirectories only as
needed:

- `inbox/` for newly acquired or unclassified sources;
- `items/arxiv/`, `items/papers/`, and `items/books/` for selected sources with
  stable local identities; and
- `derived/` for extracted text, rendered pages, and other derivatives.

Never alter source originals. Keep derivatives traceable to an exact source and
version. Record durable bibliographic identity and claim verification in a
research note or source-check record rather than relying on the presence of a
local file.

Do not force-add source artifacts. See
[`docs/LITERATURE.md`](../docs/LITERATURE.md) for the evidence workflow.

Known arXiv items are filed automatically:

```bash
uv run python tools/fetch_arxiv.py VERSIONED_ARXIV_ID
```

For manually filed sources, start from
[`templates/REFERENCE-ITEM.json`](../templates/REFERENCE-ITEM.json), then refresh
and audit the ignored local catalog:

```bash
uv run python tools/reference_catalog.py --hash path/to/source.pdf
uv run python tools/reference_catalog.py --refresh-catalog --audit
```
