# Research records

Records are separated by function so that exploratory work stays cheap and
canonical state stays readable.

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

Use `CLAIMS.md` when exact reusable statements would make the ledger cumbersome.
Give a claim a stable identifier only when it becomes durable. Once cited,
never renumber or reuse that identifier. Store the exact statement, status,
evidence, and dependencies; keep full arguments in notes.

Admit a claim when it can reasonably be cited or reused independently, settles
a natural subquestion, supplies a reusable construction, records a meaningful
closed computational scope, or certifies a refutation or correction. Temporary
conjectures, proof-internal lemmas, immediately superseded statements, and raw
experiments normally remain outside the catalog.

Each exact claim has one primary thread. Other threads cite
`<thread>:<claim-id>` rather than maintaining competing formulations. If cited
claims later merge or are superseded, retain a small alias or supersession entry
so old references continue to resolve.

Use the evidence statuses in `AGENTS.md`, splitting a package when its parts
require different statuses. The catalog contains statements and provenance,
not full proofs. If an entry becomes an essay, move the argument to a note and
retain the exact claim plus its evidence links.

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
