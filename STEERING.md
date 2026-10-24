# Cross-thread steering

Use this file only for current owner directions that genuinely apply across
multiple research threads or for rare standing assignments.

Every mathematical session reads this file after `AGENTS.md` and before the
relevant thread ledger. This file holds current owner direction;
`docs/PROJECT-FOUNDATIONS.md` holds the optional shared mathematical
conventions, read only when something actually calls for them.

There are no cross-thread directions in the fictional starter state.

## Audit direction

None recorded. Agents audit final and load-bearing claims in proportion to
their role. The owner may defer independent audits here; then agents preserve
the constructing agent's argument, state that it has not been independently
audited, and do not substitute a lead-agent recheck.

## Shape of an entry

Typical cross-thread entries are a source exclusion, a research-area
preference, a restriction of the campaign target pool, or an audit direction.
Each quotes the owner verbatim with date and context, and keeps any
generalization on a separate "Interpretation (agent)" line, as `AGENTS.md`
requires. For example:

```text
## Source exclusion

Owner direction (2026-01-10), verbatim: "Do not take targets from the survey
by X; its statements are unreliable."

Interpretation (agent): do not select conjectures or questions from that
survey as research targets and do not use it as load-bearing evidence.
Existing records concerning it remain as history.
```

Thread-specific targets, priorities, exclusions, and park/resume decisions
belong in the relevant `threads/<thread>/LEDGER.md`.
