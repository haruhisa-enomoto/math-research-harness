# Math Research Harness

This repository is a starting point for owner-directed mathematical research
with AI agents. It organizes conversation, evidence, literature, computation,
scratch work, durable notes, canonical state, and Git checkpoints. Its sample
inquiry is fictional and uses placeholders such as `Property P`, `Condition A`,
and `setting S`.

## Start here

- Agents follow [`AGENTS.md`](AGENTS.md); Claude discovers the same contract
  through [`CLAUDE.md`](CLAUDE.md).
- Shared mathematical boot state lives in
  [`docs/PROJECT-FOUNDATIONS.md`](docs/PROJECT-FOUNDATIONS.md).
- Owners can begin with [`docs/OWNER-GUIDE.md`](docs/OWNER-GUIDE.md).
- The worked interaction is in
  [`examples/WORKED-SESSION.md`](examples/WORKED-SESSION.md).
- The generic literature workflow is in
  [`docs/LITERATURE.md`](docs/LITERATURE.md).
- Computational reproducibility is described in
  [`docs/COMPUTATIONS.md`](docs/COMPUTATIONS.md).
- Manuscript exposition standards are in
  [`docs/PAPER-WRITING.md`](docs/PAPER-WRITING.md), and the forward-blind
  reading protocol is in
  [`docs/FIRST-READER-REVIEW.md`](docs/FIRST-READER-REVIEW.md).
- The fictional canonical state begins at
  [`threads/INDEX.md`](threads/INDEX.md).

## Prerequisites

Git records durable checkpoints. The included Python and PDF utilities run
through `uv`, which installs their locked Python packages.

| Feature | Owner-installed command-line tools |
|---|---|
| Repository workflow | `git` |
| Python and PDF utilities | `uv` |
| arXiv downloads | `curl` |
| OCR | `ocrmypdf`, `tesseract`, and any needed Tesseract language data |
| DjVu preparation | `djvused`, `djvutxt`, and `ddjvu` (usually provided by DjVuLibre) |

`uv sync` installs PyMuPDF and FontTools from `uv.lock`. OCR and DjVu tools are
optional. Run the preflight below to see which features are available on the
current machine.

To prepare the environment and run the tests:

```bash
uv sync
uv run python tools/literature_preflight.py
uv run python -m unittest discover -s tests
```

Run the included Python utilities through `uv`.

## Repository map

| Path | Purpose |
|---|---|
| `AGENTS.md` | Authoritative session contract: boot, authority, evidence, records, and safety |
| `CLAUDE.md` | Claude entry point forwarding to the authoritative session contract |
| `docs/PROJECT-FOUNDATIONS.md` | Compact shared mathematical boot state with primary claim pointers |
| `STEERING.md` | Current directions that genuinely apply across research threads |
| `docs/` | Owner guide and focused workflow policies |
| `templates/` | Optional starting shapes for new records |
| `threads/` | One fictional thread showing present-facing canonical state |
| `examples/` | A worked conversation-to-checkpoint walkthrough |
| `lib/` | Maintained reusable research code in any language or system |
| `experiments/` | One-off programs organized by research thread |
| `data/` | Ignored local machine-readable outputs and certificates, with a tracked usage guide |
| `results/` | Human-readable summaries paired with durable outputs |
| `paper/` | Optional live paper material, edited only on explicit owner request, with the manuscript vocabulary check in `paper/vocab/` |
| `briefings/` | Optional interface for collaborators without repository access |
| `references/` | Ignored local source workspace with a tracked usage guide |
| `.research-scratch/` | Ignored disposable workspace created only when needed |
| `tools/` | Literature acquisition, preparation and catalog utilities, the claim-catalog audit, and the manuscript vocabulary check |
| `tests/` | Offline unit tests for the reusable harness tools |

## Design principles

1. Conversation controls the work; the owner does not operate the harness.
2. Load only the context the current task needs.
3. Scope, evidence strength, significance, and publication authority are
   separate decisions.
4. Continue while a credible next step has worthwhile expected value.
5. Keep fluid work in scratch; preserve only coherent durable packages.
6. Let canonical state describe the present and Git preserve history.
7. Treat opportunities as a map, not an assignment queue.

Computational work can use GAP, SageMath, Mathematica, Macaulay2, Magma, Lean,
Python, Julia, Rust, or other systems appropriate to the project. Record the
chosen backends in [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md), and record the
software and version when a result depends on them. Machine-readable outputs
under `data/` stay on local disk; the tracked record of a computation is its
manifest in `results/`.

This is a working template, not a fixed configuration. When starting a real
project, agents should replace the fictional thread and adapt the session
contract, terminology, records, tools, and environment guidance to the owner's
working practices and the actual repository. The owner can describe preferences
in ordinary conversation; the agent should turn them into scoped repository
changes rather than requiring the owner to configure the harness manually.

The template is available under the [`MIT License`](LICENSE).
