# Session contract

This repository supports owner-directed mathematical research. Infer scope and
authorization from ordinary conversation. Do not ask the owner to operate the
harness as a configuration system. The sample thread and files explicitly
marked as tutorial or fictional examples demonstrate record shape only; they
are not canonical mathematical state.

## Boot

Read this file first and classify the task.

- Meta or repository work needs no mathematical thread state.
- For mathematical work, read `STEERING.md` and the relevant
  `threads/<thread>/LEDGER.md`. Read `docs/PROJECT-FOUNDATIONS.md` only when the
  ledger cites it, the task spans several threads, or one of its shared
  conventions is genuinely load-bearing; use it then without rederiving its
  contents or presenting them as new.
- If the thread has `RESEARCH-QUESTIONS.md`, it runs the question-driven
  variant in `docs/RESEARCH-MODES.md`: read that document and the question
  list whole before choosing work, and follow `docs/RECORDS.md`'s list rules.
  Ordinary `QUESTIONS.md` files are catalogs or general question lists;
  their presence does not select a research mode or trigger the hooks.
- Read `threads/INDEX.md` only when the thread is unclear or the task concerns
  the thread directory.
- Follow ledger citations only as the task needs them. Do not load every note or
  claim by default.
- For literature work, also read `docs/LITERATURE.md`.
- For a manuscript citation, attribution, or related-literature audit, also
  read `docs/CITATION-AUDIT.md`. “Do citation audit for <paper>” invokes its
  full scope, including missing precedents and proof-method credit.
- For backend-dependent work, a durable computation, or a counterexample, read
  `docs/COMPUTATIONS.md`.
- For collaboration with agents lacking repository access, read
  `docs/COLLABORATION.md`.
- Read `docs/CAMPAIGN-CONTRACT.md` before an exact full-resolution campaign.
- Read `docs/REPORTS.md` before producing a substantial owner-facing report.
- Before drafting or revising a live research-paper manuscript, use
  `write-research-paper` (or `polish-math-prose` when polishing prose and proof
  presentation or repairing post-polish math-audit findings) and read
  `docs/PAPER-WRITING.md` for this repository's local overlay.
- Before supervising a first-reader review, read
  `docs/FIRST-READER-REVIEW.md`; the isolated reader loads the portable
  protocol through `read-research-paper`.
- Before supervising a skeptical-editor review, read
  `docs/SKEPTICAL-EDITOR-REVIEW.md`; the isolated editor loads the portable
  protocol through `read-research-paper`.

The portable paper skills (`write-research-paper`, `read-research-paper`,
`polish-math-prose`, and `coordinate-research-paper`) are maintained in the
public `haruhisa-enomoto/math-paper-skills` repository and installed through
user-level skill links; see `docs/SKILLS.md`. This repository keeps only its
local overlays, vocabulary tooling, and any private evaluation cases. A skill
supplements this contract and never creates edit authority. `evals/` holds
frozen cases for scoring those skills; an isolated reader or editor must not
read it. Other repository record shapes are in `templates/`.

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

When recording an owner direction in a durable document, quote the owner's
words verbatim with date and context (paper, situation). Put any
generalization, procedure, or example the agent derives under a separate
"Interpretation (agent)" line. A remark about one paper stays scoped to that
paper unless the owner says it applies generally. Use the label "Owner
direction" only for the owner's words or wording the owner approved.

## Evidence and communication

Use ordinary mathematical language and plain, short English in owner-facing
communication. Define nonstandard notation before relying on it. Distinguish
proved, computed, refuted, equivalent-strength, conditional, and open
statements.

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
calculation has only its recorded scope. Preserve another agent’s provenance.
Audit load-bearing claims in proportion to their role, unless the owner's
current audit direction in `STEERING.md` says otherwise.

## Literature and computation routing

For literature, follow `docs/LITERATURE.md`: check the local catalog first,
prefer versioned arXiv source, preserve originals, and use the repository's
preparation tools for PDF/DjVu derivatives. Hexagon (hexagonmath.org) works are
written `hexagon:<id>` and filed with `tools/fetch_hexagon.py`; their IDs look
like arXiv IDs but are a separate namespace. Never invoke `pdftotext`,
`pdftoppm`, `djvutxt`, or OCR commands directly. Local availability is not
verified evidence or endorsement.

For computation, follow `docs/COMPUTATIONS.md`. Record the project's engine in
`docs/ENVIRONMENT.md` and run its preflight before depending on it. Keep the
search and orchestration layer separate from the engine that owns the
mathematical objects, and do not reimplement that engine in scratch code or
gate compatibility on Git hashes. Search in closed strata with exact counts.
Follow the computation document for exactness, verification, versions,
conventions, and durable certificates.

Run repository Python utilities with `uv run`; install declared dependencies
with `uv sync`. Suitable maintained tools may be added for a concrete benefit;
use `uv add` for reusable dependencies. See `docs/ENVIRONMENT.md` when setting
up or changing the environment.

## Working records

Use `.research-scratch/<thread>/<session>/` for disposable reasoning and probes;
it is not permanent evidence. One-off programs belong in `experiments/<thread>/`
and must not be imported as libraries. Promote recurring logic to a small tested
`lib/` API when a shared boundary has concrete value; do not generalize or
refactor closed experiments merely for uniformity.

Before a durable checkpoint, read `docs/RECORDS.md`. Preserve coherent proofs,
refutations, reusable constructions, certified calculations, significant
corrections, durable obstructions, or necessary handoffs. Notes and their actual
canonical consequences belong in the same checkpoint; correct false canonical
state promptly. No canonical consequence means no synchronization debt. Take
note timestamps and dates from the operating system immediately before
finalizing.

Each thread has a compact present-facing `LEDGER.md` and a strongest-current-claim
catalog `CLAIMS.md`; unsuitable nonmathematical threads may explicitly omit the
catalog. Proofs, witnesses, implementation details, and route history belong in
linked evidence, not catalog entries or ledgers. `ACTIVE.md` is optional state
for complex interacting work. Follow the records document for note timestamps,
claim curation and renumbering, evidence fields, and structural validation.

`docs/PROJECT-FOUNDATIONS.md` holds stable shared conventions and exceptional
cross-thread facts, not a second claim catalog. Update affected entries with
canonical state; specialized mathematics stays in its owning thread.

## Evolving the repository

This contract, directory layout, and sample records are starting points. Learn
the owner's working practices from ordinary conversation and the repository
itself. Within authorized repository work, revise `AGENTS.md`, steering and
workflow documents, templates, directory conventions, tool instructions, and
environment guidance to match the project as it develops.

Preserve existing work and do not invent owner preferences. Ask when an
adaptation would change research authority, durable owner direction, or another
material policy choice. Do not require the owner to translate ordinary requests
into configuration edits.

## Collaboration and Git

Internal subagents are optional. The lead assigns bounded, nonconflicting work,
synthesizes the result, and alone edits canonical state and commits. Review of
mathematical returns follows the owner's audit direction in `STEERING.md`;
when the owner has deferred audits, do not independently recheck subagent
proofs. Parallelism does not enlarge owner-authorized scope.

Several owner-directed sessions may work concurrently in one working tree.
Treat every pre-existing tracked, staged, or untracked change as shared work
unless its provenance is known. Partition concurrent tasks by file whenever
possible and serialize overlapping edits. Stage only explicit owned paths,
inspect the index before committing, and serialize Git operations that take the
index lock. Do not switch branches, stash, reset, clean, rebase, run `git am`,
or otherwise rewrite shared worktree or index state while another session may
be active. Shared integration files such as ledgers, indexes, and dependency
manifests require particular care.

For a collaborator without repository access, assemble an outbound briefing
from canonical state rather than memory. Preserve inbound material with its
provenance and audit load-bearing claims before canonical use. Follow
`docs/COLLABORATION.md`.

Preserve unrelated changes in a dirty tree. Make a scoped imperative commit at
each coherent durable checkpoint without asking, unless the owner has said
otherwise. Do not commit scratch work. Before handoff, report relevant
uncommitted files and leave repository state intelligible.

When the project has a Git remote, push at durable checkpoints. `data/` is
ignored in full and never reaches a remote, so a push backs up code, records,
and ledgers only. Never widen a push to carry data: if an output looks too
valuable to leave untracked, strengthen its manifest in `results/<thread>/`
instead. Because `git status` does not show data outputs, name the `data/`
files a session produced when reporting work at handoff.
