# Evaluation suites

Optional frozen inputs for testing repository skills against owner judgment.
The sample harness ships no suite. A suite is a pair: `cases.yaml` holds the
raw material and the forwarding contract, `gold.yaml` holds the owner's labels
and repair boundaries.

A typical suite is `paper-writing/`: exposition and revision judgment for the
externally maintained paper skills recorded in
[`docs/SKILLS.md`](../docs/SKILLS.md). Draw cases from the project's own
manuscripts and their revision history, and give each case a `source` field
with the exact commit, path, and line.

## Running a case

Read the suite's `forwarding_contract` first. It fixes what may reach the agent
under test and what must never leave the suite file.

Forward one scalar built from the fields the contract names, into a clean
staging context. Never forward the case ID, its split, the skill name, the
source locator, the contract itself, or anything from `gold.yaml`. A case whose
`raw` is absent names a `frozen_source` blob instead; materialize only that
blob.

An isolated reader must not read `evals/` at all. Score the run against
`gold.yaml` afterwards, keeping required observations separate from repair
advice, and record an invented defect as a precision failure even when the rest
of the answer is right.

Split cases into `development` and `holdout`. Tune against development cases;
keep holdout cases unread until a scored run.
