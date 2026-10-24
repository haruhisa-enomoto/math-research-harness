# Repository paper-writing conventions

Use the installed paper skills (`write-research-paper`, `read-research-paper`,
and `polish-math-prose`), their shared exposition standard, and the relevant
workflow; extended examples are optional references. Their source and the
three-phase multi-model workflow are recorded in [`SKILLS.md`](SKILLS.md). This
overlay owns repository conventions and the mandatory vocabulary gate. Read
paper-local instructions for the target only. For a standalone owner-facing
report rather than a manuscript, read [`REPORTS.md`](REPORTS.md).

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

## Published references

Credit prior results and substantial proof ideas even when an agent arrived at
them independently or the manuscript gives a self-contained proof. A new proof
does not make a known statement new. Acknowledge closely related work when it
helps locate the contribution, including work with no direct proof dependency.
For a requested citation audit, follow
[`CITATION-AUDIT.md`](CITATION-AUDIT.md); checking only the existing bibliography
does not satisfy that request.

Cite a work where its authors are first named, as in "Foo and Bar \cite{FB}
show that ...", "In \cite{FB}, Foo and Bar prove ...", or
"By \cite[Theorem~2.1]{FB}, ...", not by naming authors and citing only at the
end of a later sentence. Put the locator of an imported definition or theorem
in its optional heading.

When a paper has been published, cite the published version, not its arXiv
preprint. Verify the journal details and ensure that result locators match the
published version. The literature workflow may still use versioned arXiv TeX
for source reading and internal evidence; this does not change the version
cited in the manuscript.

## Exposition defaults

Use the owner's previous papers as the primary style exemplars when revising
an owner-directed manuscript. For a style calibration, consult
[`PAPER-STYLE-EXAMPLES.md`](PAPER-STYLE-EXAMPLES.md) and
[`MATH-WRITING-ANTI-PATTERNS.md`](MATH-WRITING-ANTI-PATTERNS.md), then read the
relevant complete source passage. They are writer-side material, not a packet
for an isolated reader.

Keep the introduction at the level of the problem, principal results, new
contribution, and main ideas. It should not teach each proof technique or
replay the sequence of technical reductions. When an introductory passage is
unclear to a reader, prefer stating it at a coarser level, pointing to the
body, or deleting it over adding detail; do not enter a loop of adding
explanation each time a reviewer asks for more. An introductory figure follows
the same level of detail. Define the techniques and explain their dependencies
where the argument begins.

Conciseness limits proof detail in the introduction, not background. Give the
background of the problem before posing it: state the classical results or
conjectures the problem belongs to, with their status and attribution, so that
the question arises naturally. Do not open with a bare question or a technical
statement without motivation, and do not assume the reader already knows that
history.

Do not repair a review finding by appending a sentence that only answers the
reviewer. Merge the point into the sentence where it belongs, restructure the
passage, or delete the trigger. A reviewer's "why X?" is evidence about the
text, not a question every reader asks. Check the body for the same pattern.

In the proof of a statement with numbered parts, open each part with its bare
label as a paragraph heading, such as `(1)` or `(1) $\Rightarrow$ (2):`, in
the order of the statement, rather than writing `For (1), ...` or
`... this proves (1)`.

Prefer recognizable cardinalities and established notation to variables that
only count already named sets. Retain abbreviations when expansion obscures the
argument or names a repeatedly studied combination.

Give lasting definitions and constructions numbered, findable homes and cite
those homes when recalling notation. Use an upright `Setting` environment when
a substantial collection of assumptions and notation governs a section or
several results; state its scope explicitly. Distinguish assignments from their
properties and proofs. Keep ordinary prose for motivation and transitions, and
keep temporary proof notation local. Do not turn every observation into a
lemma or every one-line convention into a numbered environment.

State imported results directly in the manuscript's conventions (for example,
left or right modules, composition order, sign conventions). Do not explain a
routine convention change merely because the source chose the other side;
preserve the distinction only when both versions are substantive. Specialize
general results to the setting needed after checking that their hypotheses and
constructions support the specialization. Keep the source check in the
research record; do not turn routine convention changes into warnings in the
paper.

## Recording owner style directions

Owner style directions accumulate here or in paper-local instructions. Follow
the rule in `AGENTS.md`: quote the owner's words verbatim with date and paper,
and put the agent's generalization on a separate line. A remark about one paper
stays scoped to that paper unless the owner says it applies generally. For
example:

```text
Owner direction (2026-01-15, sample paper), verbatim: "The proofs are hard to
follow without the diagrams. Show the exact sequences you use."

Interpretation (agent): in proofs of this paper, display the exact sequences
and commutative diagrams being used and argue by diagram chasing rather than
by long prose descriptions of maps.
```

## Manuscript vocabulary check

Before freezing a prose revision for independent regression, run the repository
vocabulary checker on every active manuscript TeX source as specified in
[`../paper/vocab/README.md`](../paper/vocab/README.md). Rebuild the lexicon
first when eligible source TeX under `references/` has been added or changed.
The normal check writes `vocabulary-report.json` and `vocabulary-report.md`
beside manuscript TeX files that share a directory; keep the current pair with
the manuscript. If active sources span directories, choose the manuscript root
explicitly with `--report-dir`. Use explicit scratch paths only for frozen or
temporary audits. `--stdout-only` is exploratory and does not satisfy the
recorded check.

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
rules do not establish mathematical usage; use conservative author-signature
breadth, distinct-paper breadth, and the mathematical context. A correct
specialized term may remain flagged, and sparse or mixed evidence may support
retaining it.

The gate is complete when the checker has run on every active TeX source at the
exact revision and every flag has been inspected and adjudicated, not when the
report has no warnings. Cluster recurring semantic causes in the ordinary
revision batch rather than making one mechanical edit per token, and rerun
after any accepted wording repair.

For a paper whose wording should stay close to the owner's own usage,
`tools/strict_vocabulary.py` applies a smaller explicit corpus: words from the
owner's papers count as established, and a word from comparison papers counts
only when enough distinct papers use it. Its manifest lists the papers in each
group. Like the broad check, it flags passages for discussion and never
dictates a rewrite.

Record the checked manuscript revision and report paths in writing state. A
later prose edit invalidates the recorded check. Do not give vocabulary reports
or their adjudication to an isolated reader, or count this writer-side
diagnostic as independent reading evidence.

## Project formatting conventions

Record here the manuscript conventions this project has actually settled.
These are owner decisions, not portable exposition rules, so the skill defers
to whatever this section states.

The sample harness settles none of them. Typical decisions a project records
include:

- whether the rendered abstract may contain mathematical symbols;
- how introductory restatements alias later results (for example a
  `[= Theorem 3.2]` heading) and where exact citations of imported results go;
- which front-matter paragraphs are required, such as `Organization` and
  `Conventions and notation`;
- whether enumeration labels stay upright inside italic theorem bodies;
- the document class, page layout, and preferred notation, taken from the
  owner's own papers rather than invented.

One technical lesson applies widely: do not load `\usepackage[T1]{fontenc}` or
another font package unless the project chose it. Without the matching vector
fonts installed, T1 encoding silently produces bitmap Type 3 fonts that look
poor in the PDF.

Do not invent a convention to fill a gap, and do not retrofit an existing
manuscript to a convention added after it was written without owner direction.
