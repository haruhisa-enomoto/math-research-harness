# Computational research records

Projects may use GAP, SageMath, Mathematica, Macaulay2, Magma, Lean, Python,
Julia, Rust, or other systems suited to the research. These rules explain how
to preserve computational evidence so that it can be checked later.

## Working layers

- `.research-scratch/<thread>/<session>/` contains disposable probes.
- `experiments/<thread>/` contains one-off research programs that may be rerun
  but are not imported as maintained libraries.
- `lib/` contains reusable maintained code, organized in the form natural to
  the chosen backend.
- `data/<thread>/` contains machine-readable durable outputs and certificates.
- `results/<thread>/` contains human-readable explanations of those outputs.

When experiment logic becomes reusable, promote it to `lib/`, give it a stable
interface, and add tests. Do not maintain copied implementations in both layers.

## Durable computation package

A computation supporting a durable claim records:

- the research question and exact computed scope;
- mathematical conventions and encodings;
- the program or configuration used;
- the exact invocation from repository root;
- backend, package, and relevant system versions;
- deterministic inputs, seeds, or an explanation of nondeterminism;
- machine-readable output or a compact certificate;
- a human-readable summary; and
- the date of the run and the agent responsible.

Use matching descriptive basenames in `data/<thread>/` and
`results/<thread>/` when practical. Large reproducible outputs may remain
ignored if their manifest records the generation command, expected hashes or
invariants, and storage location.

## Evidence scope

A finite computation proves only its stated finite scope. Do not present a
pattern, sample, or successful test battery as an unrestricted proof.

When a computation is exploratory, leave it in scratch. Promote it only when a
result becomes durable, needs independent verification, or will support later
comparison.

## Counterexamples and refutations

A canonical computational counterexample has three parts:

1. a concise mathematical note stating the witness and why it refutes the
   claim;
2. a machine-readable certificate under `data/<thread>/`; and
3. a small verification program under `experiments/<thread>/` or `lib/`.

The verifier should check the certificate rather than repeat a broad search.
Record enough conventions that another researcher can interpret the witness
without reconstructing the discovery process.

## Independent verification

Prefer a small verifier with clear failure messages. Check inputs before use,
report the exact verified scope, and keep expensive discovery separate from
cheap re-verification. When independent software or a second implementation is
mathematically valuable, state what independence it provides; it is not a
routine requirement.

Use [`templates/COMPUTATION-SUMMARY.md`](../templates/COMPUTATION-SUMMARY.md)
for a durable human-readable record.
