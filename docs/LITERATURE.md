# Literature workflow

Literature work is part of the research evidence chain. Discovery, possession,
verification, and canonical use are different stages.

## 1. Start from the research question

State what the source needs to establish: the exact claim, assumptions,
conventions, and scope. Search is more reliable when driven by that statement
rather than by a broad topic label.

Check the existing local catalog first. Then use focused public discovery,
following citations backward or forward when that is useful. Prefer primary
sources for mathematical claims and control the exact version when revisions or
publication differences may matter.

Prefer arXiv TeX when it is available: it usually preserves definitions,
formulas, and structure more reliably than PDF text extraction and provides
checkable line locators. Use the PDF alongside it for diagrams, layout, page or
theorem numbering, and visual verification of load-bearing text.

Literature discovery is normally authorized inside an owner-authorized research
task. It does not independently broaden the mathematical scope.

## 2. Use the local workspace

The gitignored `references/` directory is a working area for source material:

```text
references/
  inbox/                         newly acquired or not yet classified
  items/
    arxiv/<versioned-id>/        fetched source, PDF, and item metadata
    papers/<stable-slug>/        other selected papers
    books/<stable-slug>/         selected books
  derived/
    text/                        page-delimited extracted text and metadata
    pages/                       rendered page images
    ocr/                         searchable OCR derivatives
  CATALOG.json                  generated local inventory
  README.md                     tracked workspace guide
```

Do not modify source originals. Keep derivatives separate and record which
source and version produced them. Do not force-add source files merely because
they were useful in a session.

Local availability is not evidence that the owner knew, read, or endorsed a
source.

The entire working collection remains ignored by Git except for
`references/README.md`. Research notes preserve bibliographic identity and
checkable locators without committing source artifacts.

## 3. File a known arXiv item

Use public search or bibliographic discovery to identify the paper. Once the
identifier is known, fetch one item directly:

```bash
uv run python tools/fetch_arxiv.py VERSIONED_ARXIV_ID
```

The helper accepts a modern or old-style identifier and official `abs`, `pdf`,
or `e-print` URLs. It does not search or query the metadata API. It sequentially
downloads the source and PDF, safely unpacks tar or gzip source material,
identifies likely main TeX files, records hashes and response metadata, refreshes
the local catalog, and audits the result.

Prefer a versioned identifier. An unversioned identifier is allowed, but the
metadata warns that only the downloaded hashes pin the local bytes. Existing
items are reused without network requests. Use `--source-only` or `--pdf-only`
for a focused need and `--force` only when deliberately replacing that exact
item.

Set an informative HTTP identity when appropriate:

```bash
export RESEARCH_HARNESS_USER_AGENT="my-research-project/0.1 (contact@example.org)"
```

This is a restrained single-item helper. Do not loop or parallelize it for bulk
collection. For bulk access, follow the service’s official
[bulk-data guidance](https://info.arxiv.org/help/bulk_data/index.html) and
[API terms](https://info.arxiv.org/help/api/index.html).

## 4. Prepare PDF or DjVu sources

For a local PDF or DjVu file, let the preparation tool choose native extraction
when a usable text layer exists and OCR otherwise:

```bash
uv run python tools/prepare_reference.py path/to/source.pdf \
  --slug stable-source-name \
  --pages 1-12
```

The original is never modified. Text and metadata go under
`references/derived/text/`; OCR PDFs go under `references/derived/ocr/`.
Metadata records the source hash, page map, selected mode, tool versions,
subprocess commands, and invocation.

Use `--mode extract` to require an existing text layer, `--mode ocr` to force a
new searchable derivative, and `--language` to select installed recognition
languages. Focused page ranges are preferable for large books. See
[`ENVIRONMENT.md`](ENVIRONMENT.md) for optional dependencies.

Render pages when layout, a diagram, or visual verification matters:

```bash
uv run python tools/render_pdf_pages.py \
  --pdf path/to/source.pdf \
  --pages 20-22
```

For a custom extraction, use the lower-level tool:

```bash
uv run python tools/extract_pdf_text.py \
  --pdf path/to/source.pdf \
  --pages 1-12 \
  --out references/derived/text/stable-source-name.txt \
  --metadata-out references/derived/text/stable-source-name.metadata.json \
  --repair-glyphs
```

Recognition and PDF text extraction are reading aids, not certified mathematical
transcriptions. Visually verify load-bearing formulas, symbols, hypotheses, and
diagrams against the source image.

## 5. Maintain the catalog

The arXiv helper updates the local catalog automatically. After manually filing
another item with an `item.json` based on
[`templates/REFERENCE-ITEM.json`](../templates/REFERENCE-ITEM.json), run:

```bash
uv run python tools/reference_catalog.py --hash path/to/source.pdf
uv run python tools/reference_catalog.py --refresh-catalog --audit
```

The audit checks stable identities, workspace-relative paths, catalog freshness,
and recorded resource hashes. A catalog entry establishes local identity and
provenance; it does not establish a mathematical claim.

## 6. Separate discovery from verification

A title, abstract, search snippet, secondary citation, or nearby theorem may
justify further reading but does not support `proved/literature`.

For a load-bearing source, verify:

- bibliographic identity and exact version;
- the precise statement being used;
- every relevant assumption and convention;
- whether the result has the required scope;
- dependencies needed to apply it; and
- a checkable locator such as a theorem number, section, page, or stable local
  text location.

If text extraction or character recognition may have altered a formula,
hypothesis, or symbol, inspect the source image. Verification effort should
follow the consequence and risk of the claim.

Use [`templates/SOURCE-CHECK.md`](../templates/SOURCE-CHECK.md) for a durable
verification record.

## 7. Record the result honestly

Use `proved/literature` only when the source matches the exact claim and its
conventions. Otherwise record the narrower sourced statement, a conditional
dependency, a useful pointer, or an unresolved mismatch.

A literature note should identify what was checked, what the source actually
proves, and how that changes the current research picture. Update the claim
catalog or ledger only when there is a genuine canonical consequence. A source
search with no durable consequence creates no synchronization debt.

Respect access conditions and copyright. Preserve bibliographic metadata and
verification notes in Git; keep source artifacts local unless the repository’s
owner deliberately chooses otherwise.
