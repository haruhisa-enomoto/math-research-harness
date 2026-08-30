# Session contract

This repository demonstrates owner-directed research using fictional content.
Infer scope and authorization from ordinary conversation. Do not ask the owner
to operate the harness as a configuration system.

## Boot

Read this file first and classify the task.

- Meta or repository work needs no fictional thread state.
- For mathematical work, read `STEERING.md` and the relevant
  `threads/<thread>/LEDGER.md`. Read `docs/PROJECT-FOUNDATIONS.md` only when the
  ledger cites it, the task genuinely spans several threads, or one of its
  shared conventions is load-bearing; use it then without rederiving its
  contents or presenting them as new.
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
- Before drafting or revising a live research-paper manuscript, use
  `write-research-paper` and read `docs/PAPER-WRITING.md` for this repository's
  local overlay.
- Before supervising a first-reader review, read
  `docs/FIRST-READER-REVIEW.md`; the isolated reader loads the portable
  protocol through `read-research-paper`.
- Before supervising a skeptical-editor review, read
  `docs/SKEPTICAL-EDITOR-REVIEW.md`; the isolated editor loads the portable
  protocol through `read-research-paper`.

The portable `write-research-paper` and `read-research-paper` skills are
maintained outside this repository and installed through user-level skill
links; see `docs/SKILLS.md`. This repository keeps only its local overlays and
vocabulary tooling. A skill supplements this contract and never creates edit
authority. Other repository record shapes are in `templates/`.

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

Check the existing local source catalog before beginning discovery, with
`uv run python tools/reference_lookup.py` (by author, title, year, keyword, free
text, or `--grep` inside local text). The catalog records bibliographic identity
for every local item and for externally held sources with a local derivative, so
a source is found by what it is. It is an availability index, not a checked
citation. Then search appropriate public catalogs and source repositories.
Prefer arXiv TeX when it is available for exact reading and checkable line
locators. A stable TeX line range is a sufficient locator: do not read, extract,
or render a PDF merely to recover generated theorem or page numbers. Use the PDF
only when layout, diagrams, version comparison, or visual verification of
load-bearing content actually matters, and control the exact version when
differences matter.

Never invoke `pdftotext`, `pdftoppm`, `djvutxt`, or an OCR command directly.
Check for an existing derivative first; when PDF or DjVu text is genuinely
needed, use the repository preparation and extraction tools so that
page-delimited output and provenance are preserved under `references/derived/`
for reuse.

Use the ignored `references/` workspace for source files and derivatives. Do
not modify source originals, including originals in an external library, or
treat local availability as owner knowledge or endorsement. After filing an item
by hand or producing a new derivative, run `tools/reference_metadata.py` so that
the catalog describes it.

Use `proved/literature` only after matching the exact claim, assumptions, scope,
and conventions to an identified source. Record bibliographic identity and a
checkable locator. When extraction or recognition may be unreliable, verify
load-bearing text against the source image. Follow `docs/LITERATURE.md`.

## Computations

Use the computational tools chosen for the project and record that choice in
`docs/ENVIRONMENT.md`. Keep the search and orchestration layer separate from the
engine that owns the mathematical objects, and do not reimplement that engine in
temporary host-language code. Add a second implementation only when it serves a
concrete research or verification purpose; two bindings onto one engine are not
independent verification. Before depending on a backend in a session, run the
preflight the project provides for it. Record engine, version, arithmetic
domain, and the conventions a durable result depends on. See
`docs/COMPUTATIONS.md`.

Run the repository's Python support utilities through `uv run` and install their
declared dependencies with `uv sync`. Agents may add suitable maintained Python
packages or computational tools themselves when a concrete task benefits from
them; prefer a dependable existing library to reimplementing commodity
algorithms. Declare reusable Python dependencies with `uv add`, and keep a new
dependency only when the measured or maintenance benefit justifies it. See
`docs/ENVIRONMENT.md`.

Reusable maintained code belongs in `lib/`. One-off programs belong in
`experiments/<thread>/` and must not be imported as a library. Disposable probes
belong in `.research-scratch/`.

Scratch and experiment code are appropriate while an interface is still being
discovered. When logic starts recurring, or a stable shared boundary would
materially reduce future duplication, promote that part to a small tested
`lib/` API and use it in new work. Generalize only as far as an actual workflow
requires, and do not refactor closed experiments merely for uniformity.

Search campaigns work in closed strata with exact counts, not open-ended
sampling. Human-facing exact hunts default to no coverage caps. A finite
optimization budget must preserve exactness by falling through to complete
work; an explicitly bounded diagnostic must label its incomplete scope.
Operational failures checkpoint their evidence, stop loudly, and retry
automatically when the same command is repeated.

For a deterministic closed computation, one successful complete run plus
targeted sanity checks is normally sufficient. Do not repeat a broad search
solely to obtain byte-identical output. Run tests relevant to the code and
risk actually changed; a full repository test suite and formatting checks are
not routine mathematical-evidence gates. Reserve repeated or independent
verification for suspected nondeterminism, reusable engine or library changes,
candidate counterexamples, and unusually load-bearing results.

Keep verification proportional. Do not calculate hashes or add extra audits
unless they address a concrete risk, such as a large ignored or partitioned
artifact, an external transfer, suspected nondeterminism, or a candidate
counterexample.

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
`CLAIMS.md` as a compact prerequisite catalog containing only the strongest
current non-subsumed reusable claims, and `ACTIVE.md` for temporary complex-run
state. Claim identifiers are present catalog coordinates, not archival IDs:
delete entries made unnecessary by stronger claims, renumber consecutively,
and update present-facing citations rather than retaining compatibility stubs.
A claim entry contains only its identifier and title, evidence status, exact
statement, evidence links, and dependencies. The statement must make the
assertion unambiguous, but the entry must not reproduce its proof or
computation: proof sketches, census details, witnesses, verification
narratives, implementation details, and route history belong in the linked
notes or results. Follow `docs/RECORDS.md`.

`docs/PROJECT-FOUNDATIONS.md` is an optional compact cross-thread reference,
not universal boot state and not a second claim catalog. It holds only stable
conventions, scope and transport guards, and exceptionally high-value reusable
facts, each citing the primary thread claim that owns its exact statement and
evidence. A relevant ledger cites it when those items matter. Maintain an
affected entry during the same canonical checkpoint, but leave specialized
mathematics and fresh results in their owning threads.

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

When the project has a Git remote, push at durable checkpoints. `data/` is
ignored in full and never reaches a remote, so a push backs up code, records,
and ledgers only. Never widen a push to carry data: if an output looks too
valuable to leave untracked, strengthen its manifest in `results/<thread>/`
instead. Because `git status` does not show data outputs, name the `data/`
files a session produced when reporting work at handoff.
