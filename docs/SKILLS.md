# Paper-writing skills

The portable paper-writing package is maintained separately, in
[`haruhisa-enomoto/math-paper-skills`](https://github.com/haruhisa-enomoto/math-paper-skills).
It contains the paired `write-research-paper` and `read-research-paper` skills:
the writer owns the portable exposition standard and the writer/supervisor
workflow, and the reader owns the continuous first-reader, skeptical-editor,
and delta-regression protocols. They must be installed together, because the
reader loads the writer's standard through a sibling-relative link.

Install them once, from a stable local checkout, by linking both skill
directories into the agent's user-level skill directory. That repository's
README gives the exact commands for the common agent-skills location and for
Claude Code, and both hosts follow symlinked skill directories, so one checkout
serves every workspace. Do not copy the skill bodies into this repository and
do not add project-level skill links: a second copy shadows the installed
package and drifts from it.

A skill supplements the session contract in `AGENTS.md`. It never creates edit
authority, and it does not replace this repository's own policies. What stays
here is the local overlay: authorship rules, manuscript state, the vocabulary
checker and its corpus under `tools/` and `paper/vocab/`, compilation gates,
and publication conventions. Those are host-specific and are not part of the
portable package.

If a task exposes a gap in the portable exposition standard, review protocol,
or workflow, report it rather than editing the checkout from inside a research
session.
