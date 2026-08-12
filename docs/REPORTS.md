# Owner-facing reports

A substantial report is a bounded presentation task unless the owner separately
authorizes new research. It does not change claim status or publication scope.

This is a presentation protocol, not a research mode. It changes neither the
authorized mathematical scope nor the return conditions in
`docs/RESEARCH-MODES.md`.

This guide does not govern revision of a live research-paper manuscript. For
that work, read [`PAPER-WRITING.md`](PAPER-WRITING.md); when a task involves
both a live paper and a separate owner-facing report, use both guides.

## Scope and audience

Declare the starting knowledge the report assumes. A reader with that knowledge
should not need the ledger, notes, or prior chats to understand it.

Link unobtrusively to supporting notes or certificates. Do not turn the report
itself into a proof archive unless the owner asks for complete proofs.

Use standard mathematical words and notation. Internal exploratory labels may
appear in source links or a historical appendix, but the main account must state
the objects and properties they denote rather than rely on the labels.

A genuinely new term may be used when it names a durable and useful
mathematical object. Define the object first, explain the distinction the term
captures, and do not use the name as a substitute for its defining property.

Introduce every report-specific symbol, set, function, and construction before
using it. State handedness, field assumptions, finiteness assumptions, and other
scope restrictions where they matter.

## Organization and mathematical status

Organize exposition by mathematical dependency rather than session chronology.
Operational history belongs only when the owner requests it or when it explains
why a method was abandoned.

A substantial report normally gives:

1. the exact present status and principal conclusion;
2. conventions and notation needed after the declared starting point;
3. developments in dependency order;
4. clear distinctions among proved, computed, refuted, equivalent-strength,
   conditional, and open statements;
5. concrete remaining questions; and
6. unobtrusive links to proof records and computational certificates.

State a theorem’s scope where it appears. Do not turn a finite computation into
informal evidence for an unrestricted claim. If a reformulation has the same
logical strength as the target, say so even when it exposes useful new
structure.

A report is not automatically a proof source, canonical checkpoint, or paper
edit. Those require their own evidence or owner authorization.

Unless the owner asks for a proof, the report may omit proof and experiment
details while linking to the records that support its statements.

## HTML

Use semantic HTML for prose and structure. Define notation before substantial
displayed formulas. Use TeX rendered by MathJax for mathematics and keep
evidence links available without interrupting the main explanation.

For hand-written HTML reports, use dollar delimiters consistently:

```html
<span class="math inline">$A$</span>

$$
\operatorname{Ext}^i_A(M,M)=0
$$
```

Configure MathJax explicitly with `inlineMath: [['$', '$']]` and
`displayMath: [['$$', '$$']]`. Do not use `\(...\)` or `\[...\]` delimiters in
repository HTML reports: backslashes are easily lost while patches or generated
source are transported through string-escaping layers. Before delivery, check
that intended inline mathematics still has literal dollar delimiters in the
saved HTML source.

When inexpensive, check syntax, local links, section anchors, and formula
delimiter balance. Load the report in a browser only when useful. Extensive
viewport, print, or page-by-page review is not the default unless the requested
artifact makes it necessary.

Automated accessibility, responsive-layout, or print checks are welcome when
already cheap, but they do not justify expanding a report task into exhaustive
browser testing. If visual inspection is justified, inspect one ordinary
section and one formula-heavy section rather than every page.

## TeX and PDF

Compile a requested TeX or PDF report and inspect enough of the result to catch
likely compilation or layout failures. Page-by-page visual review is not the
default. A standalone report remains distinct from editing a live paper.

## Final check

Before delivery, ask:

> Could a mathematician who knows the declared starting material understand
> this without reading the ledger, internal notes, or previous agent chats?

If not, define the missing objects, replace internal terminology, or move the
starting point earlier. Do not compensate by adding campaign chronology.
