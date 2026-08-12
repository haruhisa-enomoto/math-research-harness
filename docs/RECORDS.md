# Research records

Records are separated by function so that exploratory work stays cheap and
canonical state stays readable.

`PROJECT-FOUNDATIONS.md` is the compact mathematical boot layer shared by all
threads. It summarizes stable cross-thread facts while citing the primary
thread claim that owns each exact statement and its evidence. It does not
replace a thread ledger or claim catalog, and thread ledgers should not copy its
contents unless a local convention or scope distinction requires repetition.

## Scratch

Use `.research-scratch/<thread>/<session>/` while ideas are fluid. Scratch files
may be rough, contradictory, or temporary. They are ignored by Git and are not
evidence.

## Durable notes

A note preserves one coherent package: a proof, refutation, reusable
construction, certified computation, significant correction, durable
obstruction, or necessary handoff. Several exploratory attempts may mature into
one note.

A note does not automatically cause a ledger change. Add canonical implications
only when the package changes the standing answer, supplies a reusable
mechanism, corrects canonical state, or materially changes the current map.

A note may be revised, consolidated, renamed, or discarded until another
permanent record cites it or canonical state incorporates it. After that point,
preserve its filename and mathematical meaning; use an explicit correction note
for substantive changes.

## Ledger

`LEDGER.md` is present-facing. It normally contains owner direction,
conventions, the current theory map, durable claims or a catalog pointer,
current opportunities, and only those corrections whose omission would invite
substantial repeated error.

It is not a proof archive, chronological diary, or inventory of everything ever
tried. It should be readable comfortably in one sitting.

Use [`templates/LEDGER.md`](../templates/LEDGER.md) as a starting shape, adapting
its headings when the mathematics is clearer another way. General evidence
rules belong in `AGENTS.md`; route-specific cautions belong with the route;
owner prohibitions belong under `Owner direction`. There is no required
adversarial checklist or pitfalls section.

Move exact claim statements, proofs, route chronology, superseded mandates, and
detailed computations elsewhere. Do not compress by hiding a proof inside an
enormous table cell or paragraph.

`Current opportunities` is a nonexhaustive map rather than a task queue. Agents
with exploratory authority may pursue better in-scope questions not listed
there. A completed theorem no longer belongs in the opportunity list.

## Claim catalog

Use `CLAIMS.md` as the compact prerequisite layer for a thread: it contains the
strongest durable results that a newcomer should know before attempting new
work. It is not a registry of everything once promoted to a claim, and its
identifiers are current catalog coordinates rather than permanent archival
keys. Store the exact statement, status, evidence, and dependencies; keep full
arguments in notes.

Treat `CLAIMS.md` as a compact citation catalog, not as a self-contained proof
surface. “Exact statement” means that the hypotheses, conclusion, scope, and
indispensable conventions identify the assertion without ambiguity. It does
not mean that the entry should explain why the assertion is true. Put proof
sketches, intermediate lemmas, census counts or partitions, explicit witnesses,
certificate contents, implementation and verification details, runtimes, and
route history in the linked note or result. A reader should follow the evidence
links for the argument.

The normal entry consists only of its identifier and short title, evidence
status, exact statement, evidence links, and dependencies. Do not copy the
style of an older oversized entry merely because it is nearby. Existing large
entries need not be rewritten just for uniformity, but compact one when a
substantive edit already requires touching it and the exact meaning can be
preserved safely.

Admit a claim only when it is currently useful in its own right and is not
strictly subsumed by another catalog claim. A narrower statement may remain
when it is genuinely stronger in another direction, supplies an independently
reusable mechanism, or describes the current unresolved frontier. A closed
finite computation remains only when its exact scope is itself a live reusable
boundary, not merely because it was once a campaign milestone.

Progressive bound or dimension milestones, proof-internal lemmas, closed
subcases of a later theorem, route checkpoints, temporary conjectures, and raw
experiments belong in notes or results rather than the catalog. Dependencies
name only other independently useful catalog claims; the evidence note owns the
internal proof dependency graph.

Each exact claim has one primary thread. Other threads cite
`<thread>:<claim-id>` rather than maintaining competing formulations. At every
canonical checkpoint, reconcile the affected claim lineage. If a stronger claim
makes an older entry unnecessary, delete the older entry regardless of past
citations, update present-facing canonical references and dependencies, and
renumber the surviving catalog consecutively. Do not retain alias or
supersession entries. Historical notes and Git preserve the old numbering and
need not be rewritten merely for citation compatibility.

Keep claim headings consecutively numbered from one in reading order. After
structurally editing a catalog, run

```text
uv run python tools/audit_claim_catalog.py --strict <path-to-CLAIMS.md>
```

The audit checks consecutive numbering, required fields, legacy metadata,
explicit proof/detail sections, forbidden supersession entries, and an
entry-size review guard. It is a structural backstop, not a substitute for
semantic curation: an agent must still check that no entry is strictly
subsumed, that each survivor is useful to a new reader, that its statement
remains mathematically exact, and that its evidence supports its full scope.

Use the evidence statuses in `AGENTS.md`, splitting a package when its parts
require different statuses. The catalog contains statements and provenance,
not full proofs. If proof or computational explanation has entered a claim,
move it to a note or result and retain only the exact claim plus its evidence
links; do not wait until the entry has become an essay.

## Active state

Use `ACTIVE.md` only when interacting live routes genuinely need a shared map.
Record the current target, route leverage, exact obstructions, discriminating
tests, and provisional dependencies. Rewrite it as the run changes. Active
state is not proof evidence.

When several routes are genuinely competitive, active state can prevent
conflicting work and preserve the current discriminators. A single active route
normally needs only ordinary scratch work. Do not create `ACTIVE.md` merely
because a numerical threshold was crossed.

Put mathematical arguments in notes rather than active state. Rewrite route
rows as the position changes instead of appending session chronology.

Remove or archive active state through ordinary Git history when the complex run
ends, after absorbing its durable consequences into the ledger or claim catalog.

## Checkpoints

Update canonical state at coherent durable checkpoints, including when a
correction makes it false, a result changes the present picture, owner direction
changes, or a complex run ends or hands off. The note and resulting canonical
changes belong in the same scoped commit.

Synchronize canonical state when:

- a correction makes the current ledger false or misleading;
- a coherent durable package changes the established boundary or organizing
  mechanism;
- an active campaign or program ends, pauses, or hands off;
- owner direction, thread status, or the central opportunity changes.

There is no note-count trigger. Work with no canonical consequence creates no
synchronization debt. Git records history; the ledger records the present.

When editing canonical state, reconcile the relevant claim lineage and record
only its current scope and evidence. Retain a correction or failed route in the
ledger only when omitting it would misrepresent the present or invite
substantial repeated work. Detailed supersession history remains in notes and
Git.

Update `threads/INDEX.md` only when thread status, scope, or central focus
materially changes. Only the owner creates, parks, resumes, or closes a durable
research thread.
