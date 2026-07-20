# Optional research playbook

These are tactics, not a required procedure. Use only what has worthwhile
expected value for the current question.

## Select an approach

Choose the organization with the best expected mathematical value. A problem
may call for one compelling structural route, several independent routes, a
proof/refutation split, computation before theory, literature before
experimentation, or another order entirely. Do not manufacture route diversity
for appearance’s sake.

When several routes are genuinely competitive, record their present leverage
and exact obstructions in `ACTIVE.md`. When only one route is active, ordinary
scratch notes are usually enough.

## Test ideas early

Before investing heavily in a proposed invariant or construction, test it on
examples chosen to expose its likely weakness. Preserve a failed example only
when it reveals a durable missing condition or prevents substantial repeated
work.

Choose controls from the mathematics of the route; there is no universal fixed
test battery. Failed examples are most useful when they identify the missing
hypothesis or mechanism rather than merely adding another negative case.

## Separate proof from refutation search

For a plausible positive statement, isolate its load-bearing step and check
whether local constructions assemble globally. For counterexample search, begin
where the proposed mechanism has the least protection.

Useful proof moves may include translating to a better setting, checking
functoriality or boundary compatibility, and determining whether local
constructions compose. Use computation in counterexample search to distinguish
structural possibilities rather than merely accumulating positive cases.

A route blocked by a target-strength statement has not resolved the target.
Keep the reformulation active only when it exposes genuinely new structure or
tools; otherwise record the exact obstruction and redirect effort.

## Audit by consequence and risk

Check exact statements, assumptions, conventions, dependencies, and the jump
from local claims to announced scope. Give independent attention to surprising
or campaign-closing claims.

An independent audit is particularly valuable for a delicate sign or duality
argument, a result that closes a campaign, or a claim supporting many later
conclusions. Exploratory lemmas do not require formal checklist completion.

## Use literature and computation deliberately

Literature can clarify definitions, locate neighboring theorems, prevent false
novelty claims, or supply a mechanism. Follow `docs/LITERATURE.md` when a source
will carry mathematical weight.

Use small scratch computations to test intuition. Promote code and artifacts
only when a result becomes durable, needs independent verification, or will be
reused. A larger census should have a structural discriminator or a clearly
stated closed evidence scope.

Follow `docs/LITERATURE.md` when a source will carry mathematical weight and
`docs/COMPUTATIONS.md` when a calculation becomes durable evidence.

## Coordinate optional subagents

When work decomposes cleanly, a lead may delegate independent proof attempts,
counterexample searches, computations, source checks, or audits. Avoid
conflicting file ownership, compare returns critically, and preserve provenance.
Parallelism is useful only when the tasks are genuinely separable.

The lead remains responsible for synthesis and canonical state. Parallelism
does not enlarge owner-authorized scope.

## Decide whether to continue

Ask what the next concrete step could distinguish and whether that distinction
would materially improve the research picture. Continue while the expected
value is credible; otherwise return a precise obstruction or propose a pivot.

A serious investigation should not stop at the first superficial failure, but
it need not manufacture additional activity after credible in-scope routes have
lost worthwhile expected value.
