# Citation, attribution, and related-literature audits

Principle: in human–AI mathematical collaboration, work proved by an agent
must receive the same careful scholarly attribution as any other work. Independent rediscovery, a self-contained argument, or a result's
absence from the current bibliography does not establish originality.

“Do citation audit for <paper>” invokes the full workflow below. It covers
missing citations and intellectual credit, not just bibliography correctness.
Use ordinary conversation to resolve material ambiguity; do not ask the owner
to specify a checklist or configure the harness.

## Scope and authority

Identify the live manuscript and its owning thread. Read `STEERING.md`, the
thread ledger, paper-local instructions, and relevant previous audit records.
Use [`LITERATURE.md`](LITERATURE.md) for discovery, source preparation, and
verification, and [`PAPER-WRITING.md`](PAPER-WRITING.md) for citation conventions.
Record the manuscript revision or content hash so findings remain attributable
if another session edits it.

The default audit covers the whole manuscript, including appendices, examples,
remarks, conjecture history, definitions with claimed historical attribution,
and abstract/introduction claims about the contribution. Respect a narrower
owner request. Inspect arguments to compare methods and attribution; a citation
audit is not an independent proof audit or a new mathematical campaign.

Default: an unqualified citation-audit request produces
findings and concrete proposed repairs, without editing the live manuscript.
Apply any more specific manuscript-edit authority already given in the
conversation. If implementation is authorized, use
`write-research-paper` and its required checks for the actual revision. Do not
ask again for authority already given. Correct materially false canonical
attribution through the normal records workflow without upgrading proof status.

## What to check

1. **Prior statements.** Search for theorems, lemmas, constructions, examples,
   counterexamples, and equivalent formulations already in the literature.
   Include results obtainable by a routine specialization, duality, change of
   conventions, or short combination of known results. Distinguish an exact
   precedent from a weaker case, stronger theorem, or additional deduction.
   Do not present an agent's rediscovery as a first proof of the statement.
2. **Proof ideas and constructions.** Compare substantial mechanisms, reductions,
   constructions, and organization of arguments, even when the final statements
   differ. Credit borrowed or adapted methods and identify close precedents
   found after the proof was written. Similarity alone does not establish that
   the author or agent actually read or borrowed from a source; distinguish
   documented dependence from retrospective mathematical comparison.
3. **Related work.** Look for nearby questions, earlier partial results,
   alternative approaches, analogous constructions, and independently developed
   theories that help a reader understand the contribution. A direct logical
   dependency is not required. Explain the substantive relationship and the
   difference in scope; avoid a list of unrelated references.
4. **Existing citations and historical claims.** Verify what each citation
   supports, the relevant hypotheses and conventions, its locator and version,
   and bibliographic identity. Trace credit through expository or later sources
   to earlier authors when warranted. Distinguish the original attribution from
   the convenient source used to read the result. Earlier usage establishes
   neither first coinage nor universal priority.
5. **Presentation of the contribution.** Reconcile the abstract, introduction,
   theorem headings, local proof credits, and related-work passages with the
   findings. Separate what is known from a new extension, proof, synthesis, or
   application. Check implied novelty as well as explicit words such as “new,”
   “first,” and “we prove.” A bibliography entry alone may not convey the credit
   owed at the result or argument where it matters.

## Procedure and evidence

Start with a compact inventory of the manuscript's substantive statements,
proof mechanisms, existing citations, and novelty claims. Labels and section
names are usually enough; do not duplicate all theorem statements in a second
catalog. Reuse previous verified comparisons, checking that they still apply
to the current manuscript and source versions.

Check the local reference catalog first. Then make focused public searches
using mathematical descriptions, alternate terminology, equivalent statements,
and candidate authors, rather than only the manuscript's names. Follow the
references of close precedents and their later citing work when useful. For a
paper-stated conjecture or claimed new resolution, perform the forward-citation
check required by `LITERATURE.md`. Search beyond the present bibliography.

Read primary source passages for consequential findings. For each comparison,
record bibliographic identity, the exact version read, checkable locators, and
the correspondence of hypotheses, conclusion, conventions, or proof mechanism.
For a consequence of several results, give the short deduction and its inputs;
do not say the source states the conclusion verbatim. For method credit, name
the shared mathematical step rather than relying on common terminology.

Use versioned arXiv TeX for reading when available. Follow the repository's
published-reference rule in the manuscript: verify published metadata and
locators rather than silently transferring arXiv theorem numbers. If the
original source is unavailable, record the limitation and identify the checked
secondary attribution honestly. Search snippets and citation graphs provide
leads, not verification.

Prioritize central contribution claims and distinctive proof mechanisms, then
cover the remaining substantive material. Do not stop after repairing a few
existing citations. Priority determines the order of work, not permission to
leave identified relevant papers unchecked. A zero-result search, successful
citation-graph pagination, or completed audit is never a certificate of
novelty or exhaustive priority.

## Completing identified comparisons

Once a paper has been identified as potentially relevant to a manuscript statement, method, or related-work
account, complete the source comparison. Read the full source, including the
relevant proofs, qualifications and dependencies, rather than treating an
abstract, introduction, snippet, or citation-list entry as a completed check.
Determine and record what the paper already establishes, how its methods
relate, and what attribution or contextual citation is warranted. A checked
comparison may conclude that the paper is not relevant, with the reason.
The requirement does not demand independent proof verification of every
unrelated result in a source.

Do not defer such a comparison because it is lower priority, time-consuming,
or one of several remaining items. General diminishing-return guidance does
not override this requirement. “Audit and propose corrections only” limits
manuscript-edit authority; it does not reduce source-checking obligations or
restrict authorized harness maintenance.

Distinguish unfinished reading from a new mathematical question. After reading
and comparing the sources, a stronger connection may require substantial new
mathematics, potentially across several sessions. It may then remain open:
state the precise question, the verified relationship already established,
why a routine specialization or comparison does not settle the stronger
connection, and the citation wording justified without solving it. Do not
label unperformed source reading or an unattempted routine comparison as
new research. A citation audit does not automatically authorize a separate
research campaign to resolve that question.

If a needed source cannot be obtained, pursue the available legitimate local,
publisher, author and repository routes and record the specific access
obstruction. Such an item is blocked, not completed; clearly identify the
affected part of the audit. Do not claim whole-audit completion while known
material comparisons remain unread, unperformed, or access-blocked. An
explicit owner decision to exclude an item can narrow the scope.

Completion means that the manuscript coverage and identified relevant-source
comparisons have been performed, with proposed treatments supported at their
stated strength. Precisely formulated new mathematical questions may remain
open after that work. This requirement does not promise discovery of every
unknown paper or an exhaustive proof of historical priority.

## Findings and proposed treatment

Give each substantive finding a manuscript location, a checked source and
locator, the precise relationship, its consequence for attribution, and a
concrete treatment. Separate verified findings from leads still needing source
checks. Useful treatments include:

- Cite a known result and propose omitting a redundant proof, with the exact
  specialization or remaining argument stated.
- Keep a useful self-contained or genuinely different proof, while attributing
  the known statement explicitly.
- Credit the method before the relevant argument; state which part is adapted
  or extended and which part is the manuscript's contribution.
- Add a short related-work sentence or remark comparing hypotheses, methods,
  or conclusions even where there is no direct dependency.
- Narrow an unsupported novelty claim, correct a source's stated scope, or
  repair bibliographic data and locators.

Supply proposed wording for significant repairs, including where it belongs.
Use “follows from,” “adapts,” “uses the same idea as,” and “related to” only at
the strength the evidence supports. Do not invent a borrowing history or soften
an exact prior theorem into vague related work. Preserve concise introductions;
put detailed method comparisons beside the corresponding proof. Keep a proof
when it serves the paper, and respect explicit independence requirements before
proposing to replace it with a citation.

## Deliverable and handoff

Follow [`RECORDS.md`](RECORDS.md) for a durable note in the existing thread and
[`REPORTS.md`](REPORTS.md) for a substantial owner-facing report. Use the paper's
established audit record when appropriate, linking the evidence rather than
maintaining competing reports. The record should contain:

- the audited revision, coverage, and whether the audit is complete, partial,
  or blocked;
- attribution repairs, separated from contextual additions and bibliographic
  corrections;
- source comparisons and proposed wording sufficient to review each repair;
- the resulting description of the contribution, with search limits stated;
- any unfinished or access-blocked comparisons, clearly distinguished from
  open mathematical questions arising from completed comparisons; and
- implementation status: proposed, applied, retained, or deferred, as applicable.

Update ledgers or claim catalogs only for actual canonical consequences. Keep
proof correctness, literature support, and originality assessment separate;
finding a precedent does not owner-check an agent proof. If authorized edits
follow, check citations and cross-references, compile, and complete the writing
workflow's applicable vocabulary and exposition checks. Commit the coherent
checkpoint and report remaining limitations and relevant uncommitted work.
