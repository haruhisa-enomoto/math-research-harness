# Manuscript vocabulary check

A mechanical wording check for manuscripts in `paper/`. It builds a comparison
lexicon from the TeX sources filed under `references/items/`, then reports
manuscript word forms that the corpus never attests or attests rarely. A flag
is a prompt for inspection, not an error.

Tool: [`../../tools/lexicon.py`](../../tools/lexicon.py).

## Corpus

Only LaTeX sources are read. No OCR or PDF-derived text enters the lexicon, so
the corpus grows as TeX sources are filed under `references/items/`.

A file joins the corpus only if it has at least 200 prose words and at least
4% of them are common English function words. This drops macro-only files and
non-English sources. Versioned copies of an item already held under its bare
identifier are counted once and recorded in the `duplicates` field of
`corpus.json`.

The size of the current build is recorded in `corpus.json`. Its `word_forms`
field counts surface forms; `lexicon_entries` also counts components of
hyphenated compounds, so that exact compounds and their parts can be compared
separately.

## The author tier

An item counts as the author's when `references/CATALOG.json` records the
configured surname among its authors. Set that surname in `tools/lexicon.py`
(`OWNER_SURNAME`) or through the `RESEARCH_HARNESS_AUTHOR_SURNAME` environment
variable. There is no hardcoded item list: filing another of the author's
papers reclassifies it on the next build.

Leaving the surname unset disables this tier, and the report section
*Corpus-attested, but absent from the author's sources* is then empty. That
section also carries little signal while the tier holds only a few items, since
it will flag ordinary words of the field. The other sections do not depend on
the author tier.

## What counts as prose

The extractor removes recognized comments, document preambles, math,
citations, labels, diagrams, tables, figures, verbatim text, and bibliographies
on both the corpus and manuscript sides. It handles common LaTeX and
plain/AMS-TeX forms, but it is a lexical extractor rather than a full TeX
parser. Each removal keeps its own newlines, so reported line numbers are
exact.

Unicode diacritics and TeX letter or accent commands inside prose words are
normalized before tokenization. Different source spellings of the same name are
therefore compared as one form rather than as accidental fragments.

A hyphenated compound is attested only if the corpus writes that compound.
Attestation of its parts does not count.

## Files

- `unigrams.tsv` — lexicon entry, source items containing the exact form or
  that component of a compound, exact surface occurrences, and author's source
  items containing it. A component-only entry can have zero surface
  occurrences.
- `corpus.json` — the exact file list behind the build.

Both are build outputs and are not tracked. A check writes its report wherever
`--json` and `--markdown` point. Reports are per-manuscript output, not part of
this directory.

## Use

```sh
uv run python tools/lexicon.py build
uv run python tools/lexicon.py check <manuscript>/*.tex \
    --json <report>.json --markdown <report>.md
```

Rebuild after adding sources to `references/`. A build reads the whole corpus.
`--rare-max` sets how many source items still count as rare (default 2).

## Reading the report

Sections, in order of usefulness.

1. *Unattested, with no relative recognized by the heuristic.*
2. *Hyphenated compound unattested in the corpus.*
3. *Unattested, but formed from an attested word.*
4. *Attested in at most the requested number of source items.*

None of these categories determines whether the wording is good. Definitions,
formulas, context, and mathematical usage decide that. In particular, a
vocabulary report does not replace the exposition standards in
[`../../docs/PAPER-WRITING.md`](../../docs/PAPER-WRITING.md): a word can be
perfectly well attested and still be an undefined internal label.

The check is word-level only. The lexicon is the union of the whole corpus, so
a form attested by any source item passes the unattested check.
