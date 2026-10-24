# Literature workflow

Literature work is part of the research evidence chain. Discovery, possession,
verification, and canonical use are different stages.

For a manuscript citation audit, also follow
[`CITATION-AUDIT.md`](CITATION-AUDIT.md). That workflow checks missing prior
results, proof-method attribution, and related work as well as existing
citations; this document supplies its source-discovery and verification rules.

Read sections 1 and 6 for source selection and evidence. Then load only the
operation needed: section 2 for workspace or external-library lookup, 3 for
arXiv or Hexagon fetching, 4 for PDF/DjVu preparation, 5 for catalog lookup or
maintenance, and 7 for a durable literature record. Catalog lookup precedes
discovery; source extraction and catalog maintenance are not prerequisites for
reading already available TeX.

## 1. Start from the research question

State what the source needs to establish: the exact claim, assumptions,
conventions, and scope. Search is more reliable when driven by that statement
rather than by a broad topic label.

Check the existing local catalog first, with `tools/reference_lookup.py`
(section 5). It records author, title, year, identifiers, keywords, and
abstract for every local item, so a source can be found by what it is rather
than by a remembered identifier or slug. If an arXiv source exists, identify
its exact available version and fetch the source with the repository helper; do
not replace it with a copy from an external library. Use focused public
discovery to identify unknown sources and locate current versions, following
citations backward or forward when useful. Before treating a paper-stated
conjecture as apparently open, or accepting an agent argument as a new
full-scope resolution, run the forward-citation check in section 5 against the
source paper. Prefer primary sources for mathematical claims and control the
exact version when revisions or publication differences may matter. Use a
targeted external-library lookup for books, older or non-arXiv papers, difficult
scans, and other sources without usable arXiv source.

Prefer arXiv TeX when it is available: it usually preserves definitions,
formulas, and structure more reliably than PDF text extraction and provides
checkable line locators. A stable TeX line range is already a complete
checkable locator; do not consult, extract, or render a PDF solely to add a
generated theorem number or PDF page number. Use the PDF alongside TeX only
when the mathematical task needs a diagram, layout, comparison with a distinct
published or versioned artifact, or visual verification of load-bearing
content.

Literature discovery is normally authorized inside an owner-authorized research
task. It does not independently broaden the mathematical scope.

## 2. Use the local workspace

The gitignored `references/` directory is a working area for source material:

```text
references/
  inbox/                         newly acquired or not yet classified
  items/
    arxiv/<versioned-id>/        fetched source, PDF, and item metadata
    hexagon/<versioned-id>/      Hexagon record, BibTeX, source, PDF, metadata
    papers/<stable-slug>/        other selected papers
    books/<stable-slug>/         selected books
  derived/
    text/                        page-delimited extracted text and metadata
    pages/                       rendered page images
    ocr/                         searchable OCR derivatives
  external/<slug>.json          records for externally held sources known
                                 here only through a derivative
  CATALOG.json                  generated local inventory with bibliographic
                                 identity per item
  CATALOG.md                    generated author-sorted reading index
  README.md                     tracked workspace guide
```

Within an item, `original/` holds the downloaded artifact, `source/` holds the
unpacked or directly supplied source tree, and `item.json` holds both download
provenance and bibliographic identity.

An external library outside this workspace may hold the most suitable paper,
book, or scan. Read from it, never modify its originals, and put every
extraction, OCR result, or rendered page under `references/derived/` so that
the derivative is reusable and its provenance is recorded.

Do not modify source originals. Keep derivatives separate and record which
source and version produced them. Do not force-add source files merely because
they were useful in a session.

Local availability is not evidence that the owner knew, read, or endorsed a
source.

The entire working collection remains ignored by Git except for
`references/README.md`. Research notes preserve bibliographic identity and
checkable locators without committing source artifacts.

## 3. File a known arXiv or Hexagon item

Use public search or bibliographic discovery to identify the paper. Once the
identifiers are known, fetch one or several items directly:

```bash
uv run python tools/fetch_arxiv.py VERSIONED_ARXIV_ID
uv run python tools/fetch_arxiv.py VERSIONED_ID_1 VERSIONED_ID_2
```

The helper accepts modern or old-style identifiers and official `abs`, `pdf`,
or `e-print` URLs. It does not search or query the metadata API. It validates a
multi-item request before downloading, processes the items sequentially, safely
unpacks tar or gzip source material, identifies likely main TeX files, records
hashes and response metadata, then incrementally updates and validates the
selected catalog entries. It does not rescan or re-hash unrelated items. If the
catalog is missing or malformed, it falls back to a full rebuild.

Prefer a versioned identifier. An unversioned identifier is allowed, but the
metadata warns that only the downloaded hashes pin the local bytes. Existing
items are reused without network requests. Use `--source-only` or `--pdf-only`
for a focused need and `--force` only when deliberately replacing that exact
item.

Set an informative HTTP identity when appropriate:

```bash
export RESEARCH_HARNESS_USER_AGENT="my-research-project/0.1 (contact@example.org)"
```

This is a restrained direct-item helper, not a bulk harvester. Do not
parallelize requests or feed it bulk collections. For bulk access, follow the
service’s official
[bulk-data guidance](https://info.arxiv.org/help/bulk_data/index.html) and
[API terms](https://info.arxiv.org/help/api/index.html).

### Hexagon works

[Hexagon](https://hexagonmath.org) is a preprint server whose identifiers have
the same shape as modern arXiv identifiers (`2610.00392v2`). They are distinct
namespaces: always write a Hexagon work as `hexagon:<id>` and never pass a
Hexagon identifier to the arXiv helper. File a known work with:

```bash
uv run python tools/fetch_hexagon.py hexagon:2610.00392v2
uv run python tools/fetch_hexagon.py https://hexagonmath.org/2610.00392v2
```

The helper uses Hexagon's public read-only API. It stores the work record
(`original/work.json`), the BibTeX, the source zip, and the PDF under
`references/items/hexagon/<versioned-id>/`, and checks the PDF and source files
against the SHA-256 digests the record publishes. An unversioned identifier is
resolved to the current version and filed under it. The same `--source-only`,
`--pdf-only`, and `--force` options apply.

The record supplies the catalog's title, authors, abstract, MSC codes, and
tags, and is authoritative for the arXiv identifier and DOI. A Hexagon arXiv
identifier is a submitter declaration that Hexagon does not verify. The item
also keeps Hexagon's declarations in its `hexagon` field: authorship mode
(for example `mixed` human/AI), human-understanding level, the free-text
provenance statement, and withdrawal status. `reference_lookup.py` shows them;
`--kind hexagon` restricts a search to Hexagon items.

## 4. Prepare PDF or DjVu sources

First check `references/derived/text/` and the local catalog for an existing
reusable derivative. Agents must never invoke `pdftotext`, `pdftoppm`,
`djvutxt`, or OCR executables directly. Direct commands produce ephemeral
output and bypass the project's page mapping, metadata, hashes, and reuse
conventions. Use the repository tools below; those tools may call the same
system utilities internally while recording their invocation and outputs.

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

Use `--mode extract` to require an existing text layer, `--mode ocr` to replace
the text on the selected pages by OCR (including a garbled existing layer),
and `--language` to select installed recognition languages. For PDFs readable
with an empty password, the helper records and uses a temporary unencrypted
copy for OCR. Focused page ranges are preferable for large books. See
[`ENVIRONMENT.md`](ENVIRONMENT.md) for optional dependencies.

Render pages only when layout, a diagram, or visual verification of
load-bearing content matters. Do not render them merely to recover generated
theorem or page numbers:

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

The lower-level extractor always writes metadata. If `--metadata-out` is
omitted, it creates `<output-stem>.metadata.json` beside the text derivative.

Recognition and PDF text extraction are reading aids, not certified mathematical
transcriptions. Visually verify load-bearing formulas, symbols, hypotheses, and
diagrams against the source image.

## 5. Search and maintain the catalog

### Local search

`CATALOG.json` carries title, authors, year, identifiers, keywords, and
abstract for every local item, plus records for externally held sources present
only as derivatives. Query it by what the source is:

```bash
uv run python tools/reference_lookup.py noether invariants
uv run python tools/reference_lookup.py --author noether --year 1920-1930
uv run python tools/reference_lookup.py --title "rings of invariants" -v
uv run python tools/reference_lookup.py --keyword cohomology --json
uv run python tools/reference_lookup.py --grep "finitely generated"
```

Matching ignores case, accents, and dash style, so `riemann-roch` matches a
title typeset `Riemann--Roch` and `erdos` matches `Erdős`. `--grep` searches the
extracted text and unpacked TeX themselves and prints file and line, which is
the cheap way to check whether a statement is already available locally.
`--kind external` covers sources held outside the workspace that have a local
derivative. `references/CATALOG.md` is the same information as an
author-sorted reading list.

This is a catalog or targeted-path lookup, not a recursive scan of the
reference workspace or of an external library. It says what is available here;
it does not discover later papers that cite a source.

Catalog identity is extracted from local material, not from a metadata service.
It is an availability index and a search aid: confirm bibliographic identity in
the source itself before a `proved/literature` claim, and check the recorded
provenance (`tools/reference_lookup.py -v`) when a field looks doubtful.

### Forward-citation discovery

A local catalog cannot tell you who has cited a source since it was filed.
Before allocating a paper-stated conjecture as a research target, or accepting
an agent argument as a new full-scope resolution, query the source paper's
forward citations:

```bash
uv run python tools/reference_citations.py arxiv:2099.01234v2
uv run python tools/reference_citations.py doi:10.1000/example.2099.001
uv run python tools/reference_citations.py "Finiteness properties of rings of invariants"
```

The helper accepts an arXiv identifier or official URL, a DOI or DOI URL,
`hexagon:<id>` or a hexagonmath.org URL, or an exact title. A bare identifier
is always read as arXiv. It first enriches the query from `CATALOG.json`, then queries
Semantic Scholar and OpenAlex sequentially, exhausts their pagination,
normalizes the returned metadata, and deduplicates citing works by arXiv ID,
DOI, and bibliographic identity. Semantic Scholar runs first because it accepts
arXiv identifiers directly; metadata it resolves can then make the OpenAlex
lookup more reliable.

Use `--json` for machine-readable output. `--provider semantic-scholar` or
`--provider openalex` deliberately restricts the audit. `--max-results N` is an
explicitly bounded diagnostic: it labels the affected provider truncated and
exits nonzero. A provider lookup, resolution, or pagination failure also
preserves any results obtained from the other provider but exits nonzero, so
partial coverage cannot silently pass as a completed check.

The helper reads `SEMANTIC_SCHOLAR_API_KEY` and `OPENALEX_API_KEY` from a
git-ignored `.env` at the repository root through `python-dotenv`; variables
already set in the environment take precedence. Any agent running the helper
from the checkout then uses the keys without further setup; a separate clone or
worktree needs its own `.env`. Anonymous access to both services shares a
public quota and often fails with HTTP 429 or 503, so provide at least the free
OpenAlex key. Never commit `.env` or put keys in command arguments or tracked
files. The ordinary `RESEARCH_HARNESS_USER_AGENT` setting also applies.

Semantic Scholar requests are spaced at least 1.1 s apart, its per-key limit.
Rate limits and temporary provider failures are retried with exponential
backoff, or longer when the provider asks, noted on stderr, so a lookup can
take a minute or more before it reports a provider error.

For a Hexagon target, the helper takes the title and any declared arXiv
identifier or DOI from the local catalog or the Hexagon record and queries the
providers with those. Semantic Scholar and OpenAlex may not index Hexagon at
all, and Hexagon has no reverse-citation search, so Hexagon works citing any
source (Hexagon or arXiv) are invisible to the helper. When Hexagon activity
matters, also search Hexagon directly by topic, for example
`https://hexagonmath.org/api/v1/works?q=<term>` (terms are limited to 50
bytes).

Citation-graph coverage is uneven. A provider reporting zero citations is not
evidence that there are none, and the helper's `complete` field means only that
every enabled provider resolved and paginated successfully. It does not mean
that their combined scholarly graph is universally complete. Treat an
independent "cited by" inspection, such as Google Scholar where available, as a useful
additional safety check rather than as something the helper has reproduced.

The returned records are discovery leads, not checked citations. For each
plausible settlement or follow-up, identify the exact version, fetch its arXiv
source when available, and compare the theorem, hypotheses, conventions, and
scope as required in section 6. If a research run is long enough that the
citation graph may have changed materially, repeat the check before claiming a
new resolution.

Provider documentation:

- [Semantic Scholar Academic Graph API](https://www.semanticscholar.org/product/api)
- [OpenAlex Works API](https://developers.openalex.org/api-reference/works)

### Maintain

The arXiv helper describes, refreshes, and audits automatically. After manually
filing another item with an `item.json` based on
[`templates/REFERENCE-ITEM.json`](../templates/REFERENCE-ITEM.json), or after
producing a new derivative from an externally held source, run:

```bash
uv run python tools/reference_catalog.py --hash path/to/source.pdf
uv run python tools/reference_metadata.py
uv run python tools/reference_catalog.py --audit
```

`tools/reference_metadata.py` rewrites every `item.json`, the `external/`
records, `CATALOG.json`, and `CATALOG.md`. It reads only local material — TeX
sources, PDF document metadata, extracted text, item slugs — and makes no
network request. Useful options:

```bash
uv run python tools/reference_metadata.py --item arxiv:1503.01234v2  # one item
uv run python tools/reference_metadata.py --unpack-originals  # expand archives filed unexpanded
uv run python tools/reference_metadata.py --force             # also overwrite manual fields
```

The audit checks stable identities, workspace-relative paths, catalog freshness,
and recorded resource hashes. A catalog entry establishes local identity and
provenance; it does not establish a mathematical claim.

### Correcting a catalog entry

Extraction is a heuristic, and `metadata_provenance` records which source
supplied each field. When a field is wrong, edit `bibliographic_identity` in
that item's `item.json` (or `references/external/<slug>.json`) and set the
matching `metadata_provenance` entry to a string starting with `manual`, for
example `"title": "manual: checked against the published version"`. Later
refreshes preserve every field marked that way; only `--force` overwrites them.

## 6. Separate discovery from verification

A title, abstract, search snippet, secondary citation, or nearby theorem may
justify further reading but does not support `proved/literature`.

For a load-bearing source, verify:

- bibliographic identity and exact version;
- the precise statement being used;
- every relevant assumption and convention;
- whether the result has the required scope;
- dependencies needed to apply it; and
- a checkable locator. Prefer a stable TeX line range when TeX is available;
  otherwise use a section, page, or theorem number already present in a
  reusable derivative, or a stable local text location. Do not open a PDF
  merely to make the locator more ornate.

For a Hexagon source, read its authorship and human-understanding declarations
before relying on it. They are the submitter's statements, not checks, and a
work declared as AI-generated or only partly understood by a human needs the
same scrutiny as an unchecked agent proof before it supports
`proved/literature`.

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
