# Full-resolution campaign contract

A full-resolution campaign is sustained work on one exact target. This
document defines authorization and completion, not a required thinking method.

## Authorization

Before a standalone campaign begins, distill a short mandate from the
conversation and current ledger. Record:

- the exact target and conventions;
- permitted scope and owner exclusions;
- what counts as proof or certified refutation;
- important resource or authority limits; and
- conditions requiring a return to the owner.

Unless the owner explicitly broadens a particular campaign, a selectable
paper target must be formally labelled `Conjecture` by its authors. Statements
labelled `Question` or `Problem`, informal future-work prompts, and conjectural
remarks are not eligible merely because they can be read as yes-or-no claims.
They may still supply background, examples, or proof ingredients. This rule is
about target selection and does not reclassify historical resolutions.

Before allocating a target, read the owning thread's compact settled-conjecture
index when it has one, then search its ledger, claim catalog, and notes by
author, title, and distinctive statement text.  This internal resolution check
is separate from the literature audit: a target already settled in the
repository or listed in its selection-exclusion registry is ineligible even
when no external paper has solved it.

Target selection follows the current owner direction in `STEERING.md`. The
owner may restrict the pool there, for example to targets already recorded in
the repository; then identify the existing record before allocation and do not
search externally for new targets. Web research may still verify the current
status, progress, exact source, and supporting mathematics of an eligible
target, following `docs/LITERATURE.md`.

Without such a restriction, the local source catalog is a deduplication and
availability check, not the candidate pool. Target discovery is open to papers
the repository does not hold, and should use focused public search, current
listings, bibliographic catalogs, and backward or forward citation trails
whenever they have useful expected value. Run the forward-citation check in
`docs/LITERATURE.md` before treating a paper-stated conjecture as apparently
open. A paper's absence from the local catalog neither disfavors it nor makes
it ineligible. In either case, local availability is not evidence that a target
is open or otherwise eligible.

The owner approves the target and scope, not a predetermined route registry.

## Completion

A campaign resolves only its exact target by a proof produced in the campaign
at the stated scope or by a certified refutation produced in the campaign that
settles it.  An existing literature resolution is a target-selection
correction, not a campaign resolution.  In particular, a `proved/literature`
finding by itself is never a terminal campaign outcome.

If a later literature check shows that the allocated target was already
settled, record the exact source and scope when useful, add the target to the
relevant exclusion registry, and release it.  When the mandate authorizes
target selection or pivots, select another eligible target and continue.  When
it does not, return to the owner for a new target while stating explicitly that
the campaign has not succeeded.  Literature may remain load-bearing evidence
for ingredients of a new proof or refutation; what is excluded is treating the
discovery of an existing exact resolution as the campaign's achievement.

If the campaign independently completes a proof or certified refutation, a
later matching literature source does not erase that work: preserve the agent
argument and its provenance separately.  The following may be valuable
progress without being completion:

- a narrower positive result;
- verification through a finite boundary;
- an equivalent-strength reformulation;
- a candidate counterexample without a checkable certificate;
- an exact resolution found only in existing literature;
- an argument with an unresolved compatibility step; or
- confidence unsupported by completed evidence.

## Evidence

Use the evidence statuses in `AGENTS.md` and follow the owner's current audit
direction in `STEERING.md`. Unless the owner has deferred independent audits,
audit a final or load-bearing proof in proportion to its risk, including
conventions, hypotheses, known boundary examples, and dependency provenance.
When audits are deferred, preserve the constructing agent's argument and
state explicitly that it has not been independently audited; do not replace
the deferred audit with a lead-agent recheck of the same proof.

A canonical computational counterexample includes a concise mathematical note,
a machine-checkable certificate, and a verification program. A computation has
only its recorded finite scope unless a separate proof extends it.

## Working rhythm

For finite searches, organize cases into exact strata under
`docs/COMPUTATIONS.md`. Choose batch size from runtime and checkpoint needs;
an hour is a planning estimate, not a mathematical stopping rule. Theory and
construction detours may proceed when they have worthwhile in-scope value.

Close a stratum with its exact scope and outcome. Preserve a durable note when
warranted; update the ledger and commit when the result changes canonical state
or supplies a necessary handoff, not automatically after every batch. Admit a
negative stratum to the claim catalog only when it remains an independently
useful, non-subsumed result under `docs/RECORDS.md`.

## Checkpoints and handoff

Continue while a credible in-scope step has worthwhile expected value. On an
unresolved handoff, state the strongest reliable result, the exact remaining
gap, conditional dependencies, and the most plausible next decision. Do not
claim completion merely because the route registry is exhausted.

Use scratch space while ideas are fluid. Preserve coherent durable results,
corrections, reusable obstructions, and necessary handoffs. Update canonical
state and create a scoped checkpoint commit when the present research picture
changes.
