# Paper-writing skills

The portable paper-writing package is maintained separately, in
[`haruhisa-enomoto/math-paper-skills`](https://github.com/haruhisa-enomoto/math-paper-skills).
It contains four complementary skills:

- `write-research-paper`: drafts and revises a live LaTeX manuscript, or
  supervises independent exposition review relays; it owns the portable
  exposition standard and the reusable direction and launcher templates;
- `read-research-paper`: performs an isolated continuous first reading,
  skeptical editorial review, or bounded delta regression of a frozen
  manuscript;
- `polish-math-prose`: rewrites AI-like syntax, causative verb compression,
  telegraphic imperative chains, and compressed proof presentations into natural
  mathematical English with fresh eyes, logging substantive mathematical
  argument touches in `REVISION-NOTES.md`, and repairs defects flagged by a
  later mathematical diff audit; and
- `coordinate-research-paper`: runs the whole multi-model relay below on the
  owner's behalf.

Install them together, because the other skills load the writer's exposition
standard through sibling-relative links. Install once, from a stable local
checkout, by linking the skill directories into each agent's user-level skill
directory (for example `~/.agents/skills/` for Codex, `~/.claude/skills/` for
Claude Code, and `~/.gemini/config/skills/` for Gemini). That repository's
README gives the exact commands. User-level links use absolute paths, so no
machine-specific path enters this repository, and one checkout serves every
workspace. Do not copy the skill bodies into this repository and do not add
project-level skill links: a second copy shadows the installed package and
drifts from it.

A skill supplements the session contract in `AGENTS.md`. It never creates edit
authority, and it does not replace this repository's own policies. What stays
here is the local overlay: authorship rules, manuscript state, the vocabulary
checker and its corpus under `tools/` and `paper/vocab/`, compilation gates,
publication conventions, writer-side style material, and any evaluation cases
under `evals/`. Those are host-specific and are not part of the portable
package.

If a task exposes a gap in the portable exposition standard, review protocol,
or workflow, report it rather than editing the checkout from inside a research
session.

## Multi-model workflow

Paper production can divide labour across models in three phases. One model
can play several roles; what matters is that each review starts from a clean
context.

1. **Structure and exposition relay** (`write-research-paper` with
   `read-research-paper`). A drafting model writes the manuscript and revises
   it from review reports. A supervising model coordinates isolated
   first-reader (FR) and skeptical-editor (SE) subagents until organization,
   definitions, notation, citations, and missing steps converge. A writer turn
   does not spawn review subagents unless asked.
2. **Prose and proof-presentation rewrite** (`polish-math-prose`, rewrite
   mode). A prose-focused model reads the live `.tex` files with fresh eyes,
   ignoring earlier FR/SE reports and revision batches. It rewrites patch
   syntax and compressed proof steps into natural mathematical English and logs
   every substantive mathematical touch in `REVISION-NOTES.md`.
3. **Mathematical diff audit loop** (an auditing model with
   `polish-math-prose`, repair mode). The auditor reads `git diff` and
   `REVISION-NOTES.md` against the pre-polish baseline for mathematical
   regressions, quantifier shifts, or dropped hypotheses. The polisher repairs
   each flagged defect until the auditor finds none.

`polish-math-prose` also loads its own anti-pattern guide, which this
repository mirrors in
[`MATH-WRITING-ANTI-PATTERNS.md`](MATH-WRITING-ANTI-PATTERNS.md). Editorial
review accepts one frozen packet; continuous reading keeps its staged relay.

`docs/PAPER-WRITING.md` owns repository conventions and the vocabulary gate.
Paper-specific instructions live beside their manuscript, for example
`paper/<paper>/AGENTS.md`. Isolated readers receive audience and convention
information through their frozen direction, never through writer-side project
instructions.

## Isolated reviewer agents

Hosts that support named subagents can define the isolated reviewers once. For
Claude Code, [`.claude/agents/`](../.claude/agents/) holds `paper-first-reader`
and `paper-skeptical-editor`. Each takes its whole task from the frozen
direction file it is pointed at and must not load research state, drafting
history, earlier reviews, or evaluation cases.

## General style skills

General-purpose "humanizer" or anti-AI-writing skills tend to conflict with
the mathematical exposition standard. Keep them out of active skill discovery
while working on manuscripts. An already-running session may retain its
original skill catalog; use a new session to confirm discovery changes.
