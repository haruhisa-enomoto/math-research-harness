# Research modes

These modes describe scope authorized through ordinary conversation. They are
not forms for the owner and do not prescribe a research strategy.

## 1. Bounded task

Use for a requested artifact or delimited service: explain a claim, audit an
argument, run a specified check, repair a tool, or prepare an authorized report.
Complete the task and return. Do not turn it into an autonomous agenda.

Read-only diagnosis does not authorize implementation. Recording progress does
not authorize paper editing. Update canonical mathematical state only when the
bounded task itself proves, refutes, or corrects a durable claim.

## 2. Directed investigation

Use when the owner asks for serious exploration of a particular question or
mechanism without requiring its exact final resolution. A proposal followed by
“go for it” authorizes the proposed investigation.

Try proofs, counterexamples, examples, source checks, computations, or useful
reformulations within scope. Return with a meaningful result, precise
obstruction, valuable pivot requiring owner judgment, or an honest
diminishing-return conclusion.

Do not return merely because the first idea failed. Expanding the investigation
to a standalone full-resolution campaign or broader theory program requires
owner approval.

## 3. Full-resolution campaign

Use for sustained work on one exact target. A standalone campaign begins only
after owner approval of a short mandate under `docs/CAMPAIGN-CONTRACT.md`.
An approved theory-development program may launch an in-scope subcampaign
without separate approval while recording the same local contract.

A narrower theorem, bounded verification, or equivalent-strength reduction is
progress rather than completion. Resolve the exact target or return under the
campaign’s stated handoff conditions.  Finding that the literature already
settles the target is nonterminal: follow the correction-and-pivot rule in
`docs/CAMPAIGN-CONTRACT.md` rather than reporting campaign success.

An in-program subcampaign returns its conclusion to the surrounding program,
which may absorb the result and continue within its approved territory.

## 4. Theory-development program

Use when the owner authorizes autonomous development of a broad territory. The
approved territory, exclusions, and initial points of contact remain standing
until the owner changes or parks them.

Within scope, the agent may introduce useful objects, test conjectures, prove
results, run focused investigations, and launch exact subcampaigns. Current
opportunities are entrances rather than a task list.

Return with a coherent account when a central question is resolved, the
owner’s mathematical taste or new authority is needed, credible directions face
precise barriers, or further work has clearly diminishing expected value.
Complete exhaustion of an open territory is not required.

### Question-driven variant (pilot)

Use only when the owner asks for a program to be question-driven: the agent,
not the owner, chooses what to study next, from questions that its own results
raised. Authority, territory, and exclusions are those of the surrounding
program. The thread then carries `RESEARCH-QUESTIONS.md`; see
`docs/RECORDS.md`. Ordinary `QUESTIONS.md` catalogs do not select this mode.
Threads without `RESEARCH-QUESTIONS.md` are unaffected.

- Before work, read `RESEARCH-QUESTIONS.md` whole. Choose one question and state, in
  scratch or the commit message, what success and what failure would each
  teach. A better question raised by the work may replace a live one through
  retirement.
- Before investing in a question, run a short literature check for whether it
  is already settled or close to a known result in any field, including
  neighbouring general theories that the question may specialize. Record the
  outcome in the note.
- Questions come from concrete events in the work: an unused hypothesis, two
  routes failing at the same step, an unexplained coincidence, a
  counterexample that works for an unexpected reason. Do not invent questions
  to fill the list.
- Stay with a chosen question until its next action is done or new evidence
  changes the picture. Novelty of another question is not a reason to switch.
- After work, rewrite the entry worked on. A next action is a step, not the
  question: when it settles only a special case or test class, rewrite the
  entry to the remaining question instead of retiring it.
- Retire an entry with one of these kinds, stated honestly:
  - `answered` or `refuted`: the question as written is settled;
  - `superseded by <id>`: a live question contains it;
  - `parked`: real attempts failed; name the obstruction and when to reopen;
  - `dropped`: not worth its slot, whether or not it was attempted.
- A question may be a conjecture, naive or deep; a conjecture raised by the
  work is an ordinary entry. Work on special cases is a normal next action,
  and a special-case result counts as a new observation, so a conjecture
  that keeps yielding special cases stays live.
- Hard questions are parked, not attacked forever or skipped forever. Park a
  question after two attempts that produce no new observation. A question
  skipped for three runs is worked on next, parked if it still deserves a
  return, or dropped. A parked question is reopened by copying it back into
  the list when a new observation reaches its obstruction.
- An owner-assigned target stays in the ledger as owner direction or
  territory, not only in the list, so parking an angle on it never removes it.
- Commit once per question worked on, so each commit carries one
  `Question:` line and the history shows which work came from which question.
- On resolving one question, continue with the next instead of returning.
  Return when the owner's taste or authority is needed, the agreed budget is
  spent, no live question has a worthwhile discriminating action, or the
  territory appears exhausted. Say which of these applies.
- At the end of each run, compare the live questions with the territory and
  owner direction in the ledger. Report which parts have no live question, and
  open one there only when a concrete observation supports it. Read the
  `parked` lines of `RESEARCH-QUESTIONS-RETIRED.md` (for example with
  `grep '; parked:'`) and reopen any whose condition this run has met. Also
  report questions skipped for two or more runs, anything parked, dropped,
  or reopened.
- Evidence statuses are unchanged. Interest in a question never raises the
  status of a claim.

#### Known failure modes

Avoid these patterns when choosing questions and when ending a run:

- **Narrowing to the easiest class.** Drifting to the most computable
  examples and writing that class into the question. A special class is a
  test case; the question stays general.
- **Losing the general question.** Retiring a question once only its test
  case is settled.
- **Picking what closes fast.** Preferring questions answerable in one
  session. Resistance is not a reason to switch.
- **Reporting gaps instead of acting.** Listing uncovered territory without
  opening anything. Earlier records, such as previous opportunity maps and
  parked questions, count as concrete observations for this purpose.

Depth on one question is not a failure. When the territory has more than one
area, at least one live question serves an area different from the rest,
filled from new observations or existing records, never invented.

Every entry carries a `Serves:` line naming the general question or territory
area it serves, and for a special class, why that class. The note for a chosen
question states the same before work.

## Transitions

The owner redirects work through ordinary language. A durable target,
exclusion, or park/resume decision belongs in the thread ledger. Modes govern
authority and return conditions, not the number of notes, routes, experiments,
or agents.
