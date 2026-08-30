# Manuscript vocabulary check

A mechanical wording check for manuscripts in `paper/`. It builds a comparison
lexicon from the TeX sources filed under `references/items/`, reports
manuscript word forms the corpus never attests or attests narrowly, and
compares every hyphenated manuscript form with its exact open and solid
spellings. A flag is a prompt for inspection, not an error.

Tool: [`../../tools/lexicon.py`](../../tools/lexicon.py).

## Corpus

Only LaTeX sources are read. No OCR or PDF-derived text enters the lexicon, so
the corpus grows as TeX sources are filed under `references/items/`.

A file joins the corpus only if it has at least 200 prose words and at least
4% of them are common English function words. This drops macro-only files and
non-English sources. Duplicate items with identical prose word multisets, and
duplicate files with identical prose token sequences inside one item, are
counted once; both manifests are recorded in `corpus.json`. Versioned copies of
an item already held under its bare identifier are the usual case.

Authors are read from each item's `bibliographic_identity.authors` metadata.
Clear affiliation, address, and TeX-layout debris is discarded, and combined
author fields are split when their separators are unambiguous. Names are then
reduced to case- and accent-insensitive given-name initials plus surname. These
conservative author signatures merge abbreviated and expanded spellings of one
name; they may also merge different people sharing initials and surname, which
understates rather than inflates breadth. There is no distinguished owner tier
and no hardcoded author bibliography. A paper without usable author metadata
still contributes to occurrence and paper counts, and the report records that
its author contribution is unknown.

The size of the current build is recorded in `corpus.json`. Its `word_forms`
field counts surface forms; `lexicon_entries` also counts components of
hyphenated compounds, so that exact compounds and their parts can be compared
separately.

## What counts as prose

The extractor removes recognized comments, document preambles, math,
citations, labels, diagrams, tables, figures, verbatim text, converter-emitted
macro definitions, and bibliographies on both the corpus and manuscript sides.
It handles common LaTeX and plain/AMS-TeX forms, but it is a lexical extractor
rather than a full TeX parser. Each removal keeps its own newlines, so reported
line numbers are exact.

Unicode diacritics and TeX letter or accent commands inside prose words are
normalized before tokenization. Different source spellings of the same name are
therefore compared as one form rather than as accidental fragments.

A hyphenated compound is attested only if the corpus writes that compound.
Attestation of its parts does not count. The compound comparison additionally
counts the exact open and solid spellings in uninterrupted prose-word runs; it
does not join words across removed mathematics, citations, or punctuation.

Comparisons are deliberately surface-exact. `Hom-space` is compared with
`Hom space` and `Homspace`, not automatically with the plural `Hom spaces`,
because automatic inflection merging can conflate a noun phrase such as
`three elements` with the attributive alternative to `three-element`. Inspect
related inflections separately when the exact comparison is sparse.

## Files

- `unigrams.tsv` — lexicon entry, distinct papers, exact surface occurrences,
  distinct conservative author signatures, and supporting papers without author
  metadata. A component-only entry can have zero surface occurrences.
- `corpus.json` — the exact file list and bibliographic authors behind the
  build.

Both are build outputs and are not tracked. A check normally writes
`vocabulary-report.json` and `vocabulary-report.md` in the common parent
directory of its target TeX files. Reports are per-manuscript output, not part
of this directory. The JSON retains every manuscript location and, for compound
comparisons, the complete supporting paper and author sets. The Markdown table
displays the first three manuscript locations for each word.

## Use

```sh
uv run python tools/lexicon.py build
uv run python tools/lexicon.py check <manuscript>/*.tex
```

The check above writes both standard reports beside the TeX sources. Use
`--report-dir <directory>` to place both standard filenames elsewhere, or
`--json` and `--markdown` to override either individual path. If the target
files have different parent directories, the command refuses to guess unless
`--report-dir` or both explicit report paths are supplied. Output directories
are created as needed. The command summary reports
`"manuscript_result": "not_pass_fail"` and directs the writer to inspect and
adjudicate the report; its numerical counts are not a manuscript verdict.

Use `--stdout-only` for an exploratory check that prints only the short
summary. It cannot be combined with report-output options and does not satisfy
a workflow's required recorded vocabulary check.

Rebuild after adding sources to `references/`. A form is narrowly attested when
either its distinct-paper count is at most `--rare-max-papers` or its
author-signature count is at most `--rare-max-authors` (both default to 2;
`--rare-max` remains an alias for the paper threshold).

Every hyphenated manuscript form is compared with its open and solid spellings.
The default `broad support` label requires at least 3 papers, at least 5 author
signatures, and at least a 4:1 advantage under both counts. Configure these
gates with `--compound-min-papers`, `--compound-min-authors`, and
`--compound-dominance-ratio`. Raw occurrences are informational only.

## Adjudicating a flag

The checker has no manuscript-level pass or fail result. Its output locates
phrases for writer judgment; eliminating all rows is not the objective. Inspect
the complete sentence and paragraph before editing the flagged token.

Ask, in this order:

1. Does the phrase state an exact mathematical subject, predicate, and
   referent, or does ordinary English conceal the condition, equality, map, or
   implication actually used?
2. Is it a defined and useful term, or an internal or one-use label that adds
   terminology without reducing later work?
3. Does it sound like a conventional theorem, criterion, principle, method, or
   argument without an established or immediately introduced referent?
4. Does a citation or author's name replace the precise sourced result and
   hypotheses needed at this point?
5. Does the passage have a reader-facing mathematical role, or does it preserve
   drafting history, reassurance, or a private objection?

Repair a semantic or expository defect before considering the surface form. A
precise formula, the actual mathematical property, an exact numbered reference,
or a direct statement of the imported result is often better than another
English label. Compare hyphenated, open, and solid spellings only after the
phrase is mathematically precise, necessary, and properly introduced.

Never respell a token solely to make its row disappear. A correct specialized
term may remain flagged. The recorded check is complete when it covers the
exact manuscript revision and every flag has been inspected and adjudicated.
Rerun after any accepted wording change so that the report matches the revision
being frozen for regression.

## Reading the report

Sections, in order of usefulness.

1. *Hyphenated, open, and solid spellings.*
2. *Unattested, with no relative recognized by the heuristic.*
3. *Hyphenated compound unattested in the corpus.*
4. *Unattested, but formed from an attested word.*
5. *Narrowly attested by paper or author-signature breadth.*

None of these categories determines whether the wording is good. Definitions,
formulas, context, and mathematical usage decide that. In particular, a
vocabulary report does not replace the exposition standards in
[`../../docs/PAPER-WRITING.md`](../../docs/PAPER-WRITING.md): a word can be
perfectly well attested and still be an undefined internal label. A
`broad support` label describes only this finite corpus; it does not certify
correctness, usual mathematical language, or that the surrounding phrase earns
its place.

The general check is word-level only. The tool counts word sequences solely for
the targeted open alternatives to hyphenated manuscript forms; it does not flag
arbitrary unattested word pairs. The lexicon is the union of the whole corpus,
so a form attested by any source item passes the unattested check.
General-English hyphenation rules are not corpus evidence. Describe a spelling
as broadly supported only when both its distinct-paper and author-signature
counts pass the printed gates; otherwise report the evidence as mixed, sparse,
or absent and inspect the context.
