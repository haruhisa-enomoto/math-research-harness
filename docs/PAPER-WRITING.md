# Repository paper-writing conventions

The installed `write-research-paper` skill loads the portable exposition
standard and the writer/supervisor workflow in full; its canonical source is
recorded in [`SKILLS.md`](SKILLS.md). This document adds only the conventions
and tooling specific to this repository. For a standalone owner-facing report
rather than a manuscript, read [`REPORTS.md`](REPORTS.md).


## Authorship and identity

Authorship is owner-controlled. Unless the owner explicitly assigns their name
to a particular manuscript, do not use the owner's name, affiliation, address,
email address, or other identity metadata in its author block. Use the drafting
agent's name as the author instead.

Use the most specific agent or model designation reliably exposed by the
current environment, including its version or tier. Do not replace an
available versioned identity by a generic product label, and do not guess a
model identity that the environment does not establish.

Permission must be explicit for the manuscript at hand. Do not infer it from
the repository owner identity, author information in another paper, an existing
template, prior correspondence, or the owner's mathematical contribution. If
the owner specifies authorship or author metadata, reproduce only what was
authorized.

## Manuscript vocabulary check

Before freezing a prose revision for independent regression, run the repository
vocabulary checker on every active manuscript TeX source as specified in
[`../paper/vocab/README.md`](../paper/vocab/README.md). Rebuild the lexicon
first when eligible source TeX under `references/` has been added or changed.
The normal check writes `vocabulary-report.json` and `vocabulary-report.md`
beside manuscript TeX files that share a directory; choose the manuscript root
explicitly with `--report-dir` when active sources span directories.
`--stdout-only` is exploratory and does not satisfy the recorded check.

A vocabulary report locates passages for exposition review. It is not a list of
forbidden strings and does not pass or fail a manuscript. Inspect every flag at
its manuscript location. Before changing a spelling, decide whether the phrase
is an undefined or unnecessary label, an ambiguous English substitute for an
exact mathematical predicate, an apparent theorem name, a citation standing in
for the result used, or private-process language, and repair the mathematical
statement or its role when needed.

Consider spelling or hyphenation only after the phrase itself is precise,
necessary, and properly introduced. Never change a token merely to remove a
flag. For every justified hyphenated form, inspect the exact hyphenated, open,
and solid comparison. Raw occurrence counts and general-English hyphenation
rules do not establish mathematical usage; use the author-signature and
distinct-paper breadth together with the mathematical context. A correct
specialized term may remain flagged, and sparse or mixed evidence may support
retaining it.

The gate is complete when the checker has run on every active TeX source at the
exact revision and every flag has been inspected and adjudicated, not when the
report has no warnings. Cluster recurring semantic causes in the ordinary
revision batch rather than making one mechanical edit per token, and rerun
after any accepted wording repair. A later prose edit invalidates the recorded
check. Do not give vocabulary reports or their adjudication to an isolated
reader, or count this writer-side diagnostic as independent reading evidence.

## Project formatting conventions

Record here the manuscript conventions this project has actually settled — the
shape of the abstract, how introductory restatements alias later results, which
front-matter blocks are required, and any house numbering or citation style.
These are owner decisions, not portable exposition rules, so the skill defers
to whatever this section states.

The sample harness settles none of them. Do not invent a convention to fill the
gap, and do not retrofit an existing manuscript to a convention added after it
was written without owner direction.
