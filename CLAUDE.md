# CLAUDE.md

This repository's session contract lives in `AGENTS.md`—read it first, then
follow its task-sensitive boot sequence. Mathematical work reads `STEERING.md`
and the relevant thread ledger; `docs/PROJECT-FOUNDATIONS.md` and
`threads/INDEX.md` are conditional. There is one contract for all agents; this
file is only a Claude-specific entry point.

## Memory policy

Do not use the file-based memory system in this repository. Do not read from or
write to the auto-memory directory, and do not create, update, or rely on
`MEMORY.md` or any individual memory files. Treat memory as disabled.

All durable context lives in the repository itself: `AGENTS.md`, `STEERING.md`,
thread ledgers, conditional shared references such as
`docs/PROJECT-FOUNDATIONS.md`, and the `threads/`, `results/`, and `data/`
trees. If something is worth preserving, write it to the
appropriate repository record rather than to memory.

## Rules that are easy to forget

- Use plain, short English with the owner. Avoid long or ornate wording.
- Take every date and note timestamp from the operating system immediately
  before finalizing it.
- Before any search or batch computation, reread "Search discipline" in
  `docs/COMPUTATIONS.md`: close finite strata with exact counts, reduce by
  symmetry first, start at the edge of what is already settled, time a pilot
  before a long job, and do not substitute open-ended sampling for a stratum.
- Run long jobs so the harness tracks them (a normal or background tool call),
  never detached with `nohup ... &`, `disown`, or `setsid`; a detached job
  sends no completion notice.
