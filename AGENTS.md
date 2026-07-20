# Session contract

This repository demonstrates owner-directed research using fictional content.
Infer scope and authorization from ordinary conversation. Do not ask the owner
to operate the harness as a configuration system.

## Boot

Read this file first and classify the task.

- Meta or repository work needs no fictional thread state.
- For mathematical work, read `STEERING.md` and the relevant
  `threads/<thread>/LEDGER.md`.
- Read `threads/INDEX.md` only when the thread is unclear or the task concerns
  the thread directory.
- Follow ledger citations only as the task needs them. Do not load every note or
  claim by default.
- For literature work, also read `docs/LITERATURE.md`.
- For a durable computation or counterexample, read `docs/COMPUTATIONS.md`.
- For collaboration with agents lacking repository access, read
  `docs/COLLABORATION.md`.
- Read `docs/CAMPAIGN-CONTRACT.md` before an exact full-resolution campaign.
- Read `docs/REPORTS.md` before producing a substantial owner-facing report.

## Authority and scope

The conversation is the control plane. `docs/RESEARCH-MODES.md` describes four
authorization profiles: bounded task, directed investigation, full-resolution
campaign, and theory-development program.

- Do not start a standalone campaign or new program without owner approval.
- Creating a new durable mathematical thread requires owner approval. An
  approved program may organize temporary strands inside its existing thread.
- Do not expand diagnosis into implementation, recording into publication, or
  a scoped investigation into a broader agenda.
- Literature search and normal scratch work are authorized inside an authorized
  research task.
- Continue while a credible in-scope next step has worthwhile expected value.
  Return on resolution, owner dependency, precise obstruction, or clearly
  diminishing expected value.
- Current opportunities are a nonexhaustive map, not a queue.
- Recorded failures are evidence, not prohibitions; only explicit owner
  exclusions are binding.

Owner phrases retain their ordinary meaning. “Go for it” begins the proposed
attack. “Pivot” asks for a materially different direction. “Record this as
progress” marks significance without upgrading correctness. “Put this in the
paper” authorizes paper editing; recording progress or preparing a report does
not.

Only the owner changes durable owner direction, designates owner priority,
parks or resumes a thread, or supports `proved/owner-checked`. Agents maintain
factual canonical state at the evidence level actually established.

## Evidence and communication

Use ordinary mathematical language in owner-facing communication. Define
nonstandard notation before relying on it. Distinguish proved, computed,
refuted, equivalent-strength, conditional, and open statements.

Chat mathematics uses CLI-readable Markdown, plain text, Unicode, and inline
code rather than assuming a TeX renderer.

Use evidence statuses literally:

- `proved/owner-checked`: the owner explicitly checked the proof;
- `proved/literature`: the exact claim, hypotheses, scope, and conventions match
  an identified source;
- `proved/agent`: an agent proof not yet owner-checked;
- `verified-computationally`: state the exact finite scope;
- `unverified`: an inherited or reported claim without certified support, not a
  newly proposed conjecture;
- `open`, `refuted`, `disputed`, and `parked`: use literally.

An equivalent-strength reformulation is not a resolution. A bounded
calculation has only its recorded scope. Preserve another agent’s provenance
and audit load-bearing claims in proportion to their role.

## Literature

Check the existing local source catalog before beginning discovery. Then search
appropriate public catalogs and source repositories. Prefer arXiv TeX when it
is available for exact reading and checkable line locators. Use the PDF
alongside it when layout, diagrams, page numbering, or visual verification
matters, and control the exact version when differences matter.

Use the ignored `references/` workspace for source files and derivatives. Do
not modify source originals or treat local availability as owner knowledge or
endorsement.

Use `proved/literature` only after matching the exact claim, assumptions, scope,
and conventions to an identified source. Record bibliographic identity and a
checkable locator. When extraction or recognition may be unreliable, verify
load-bearing text against the source image. Follow `docs/LITERATURE.md`.

## Computations

Use the computational tools chosen for the project. Add a second implementation
only when it serves a concrete research or verification purpose.

Run the repository's Python support utilities through `uv run` and install their
declared dependencies with `uv sync`. See `docs/ENVIRONMENT.md`.

Reusable maintained code belongs in `lib/`. One-off programs belong in
`experiments/<thread>/` and must not be imported as a library. Disposable probes
belong in `.research-scratch/`. Promote experiment logic to `lib/` with tests
when it becomes reusable.

When a computation supports a durable claim or later comparison, preserve its
exact command, software and version information, conventions, scope,
machine-readable output, and human-readable summary under the relevant thread
directories. A canonical computational counterexample requires a concise note,
a machine-checkable certificate, and a verification program. Follow
`docs/COMPUTATIONS.md`.

## Working records

Use `.research-scratch/<thread>/<session>/` for disposable reasoning. Scratch is
not permanent evidence.

Create a durable note only for a coherent proof, refutation, reusable
construction, certified calculation, significant correction, durable
obstruction, or necessary handoff. Store it under
`threads/<thread>/notes/YYYY-MM-DD-HHMMSS-<slug>.md`. Obtain its timestamp and
`Date:` value from the operating system immediately before finalizing it.
Include `Date:` and `Agent:`. Add `## Canonical implications` only when there
are actual consequences.

Each thread has a compact, present-facing `LEDGER.md`. A large thread may add
`CLAIMS.md` for exact reusable claims and `ACTIVE.md` for temporary complex-run
state. Follow `docs/RECORDS.md`.

At a durable checkpoint, update the note and affected canonical state together.
Correct false canonical state promptly. Preserve detailed history in notes and
Git rather than turning the ledger into a diary.

## Adapting the repository

This contract, directory layout, and sample records are starting points. For a
real project, learn the owner's working practices from ordinary conversation
and the repository itself. Within authorized repository work, revise
`AGENTS.md`, steering and workflow documents, templates, directory conventions,
tool instructions, and environment guidance to match the actual project.

Preserve existing work and do not invent owner preferences. Ask when an
adaptation would change research authority, durable owner direction, or another
material policy choice. Do not require the owner to translate ordinary requests
into configuration edits.

## Collaboration and Git

Internal subagents are optional. The lead assigns bounded, nonconflicting work,
checks important returns, synthesizes the result, and alone edits canonical
state and commits. Parallelism does not enlarge owner-authorized scope.

For a collaborator without repository access, assemble an outbound briefing
from canonical state rather than memory. Preserve inbound material with its
provenance and audit load-bearing claims before canonical use. Follow
`docs/COLLABORATION.md`.

Preserve unrelated changes in a dirty tree. Make a scoped imperative commit at
a coherent durable checkpoint. Do not commit scratch work. Before handoff,
report relevant uncommitted files and leave repository state intelligible.
