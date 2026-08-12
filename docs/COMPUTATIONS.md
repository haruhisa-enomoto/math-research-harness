# Computational research records

Projects may use GAP, SageMath, Mathematica, Macaulay2, Magma, Lean, Python,
Julia, Rust, or other systems suited to the research. These rules explain how
to preserve computational evidence so that it can be checked later.

## Choosing and recording backends

A project normally settles on one computational engine for its central
mathematical objects and a separate host language for search and orchestration.
Record that choice in [`ENVIRONMENT.md`](ENVIRONMENT.md) and keep it stable.
The engine is what carries mathematical authority; changing it silently
invalidates comparison between results.

Keep the boundary explicit:

- the search layer owns candidate generation, filtering, deduplication,
  batching, checkpointing, and machine-readable input and output;
- the engine owns the mathematical objects and the invariants computed from
  them;
- a search program may call the engine directly, but candidate generation and
  the mathematical tests remain separate modules with a small, typed boundary.

Do not reimplement the engine's objects in ad hoc host-language code as a
performance workaround. Host-language linear algebra or combinatorics is
appropriate when it does not replace a computation the engine owns, or when an
independently motivated verifier has been deliberately authorized. This applies
to disposable probes as well: scratch status relaxes record-keeping, not the
engine boundary.

The engine boundary is also an audit boundary. Two bindings onto the same engine
agree by construction, so their agreement is not verification evidence at all.
Two implementations of the same published algorithm agree for much the same
reason, so a differential check between them is compatibility evidence rather
than mathematical independence. Add a genuinely independent implementation only
when it supplies concrete verification value.

Before depending on a backend in a session, run whatever preflight the project
provides for it. Treat a passing preflight as the routine compatibility gate:
the exact revision of an engine matters only when a result depends on an
unreleased change. A durable record states the engine and its version, the
coefficient domain or arithmetic used, and the conventions the result depends
on. A computation over a particular field, characteristic, or precision has
only that scope unless a separate argument extends it.

## Working layers

- `.research-scratch/<thread>/<session>/` contains disposable probes.
- `experiments/<thread>/` contains one-off research programs that may be rerun
  but are not imported as maintained libraries.
- `lib/` contains reusable maintained code, organized in the form natural to
  the chosen backend.
- `data/<thread>/` contains machine-readable durable outputs and certificates.
  Git ignores it in full; see "Data is local" below.
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
`results/<thread>/` when practical.

## Data is local

`.gitignore` excludes all of `data/` except its README. This is deliberate.
Do not track a file under `data/`, do not stage one with `git add -f`, and do
not relax the `data/*` rule to get an output committed. An output that seems too
important to lose is not an exception; it is a reason to write a better
manifest.

Machine-readable outputs therefore exist on local disk only. The tracked record
of a computation is its `results/<thread>/` summary, which must carry the
manifest: exact computed scope, the generation command, backend and versions,
expected invariants or hashes, and the `data/` path where the output sits.
Write it as if the output were unavailable to the reader, because for anyone
cloning the repository it is.

Validation effort is proportional to mathematical and implementation risk. For
a deterministic closed computation, one successful complete run plus targeted
sanity checks is normally sufficient. Do not rerun a broad search solely to
demonstrate byte-for-byte reproducibility. A hash is optional for a small
deterministic artifact; it is most useful for large or externally stored
output, transfer integrity, or later comparison.

Run tests that exercise changed reusable code or a concrete failure risk. A
full repository test suite is appropriate after broad shared-library or
environment changes, not as a routine gate for every one-off experiment.
Formatting checks are maintenance checks, not computational verification
evidence. Reserve repeated runs, independent software, or a second
implementation for suspected nondeterminism, reusable engine or library
changes, candidate counterexamples, and unusually load-bearing results.

## Search discipline

Search campaigns work in strata. A stratum is a finite list of cases with a
clear boundary. Close it completely and state exact counts. Do not use
open-ended random sampling as a substitute for strata.

- Reduce the case list by symmetry before computing. Search the reduced list,
  not the raw one.
- Start each stratum at the edge of what is already proved or excluded. Do not
  recompute inside closed regions.
- Report exact scope: "all 900 pairs", not "about 26k candidates".
- Before a long batch job, time a small pilot and estimate the total. If the
  estimate is much over an hour, shrink or split the job.
- Never idle on a background job. If a job must run long, park it and close
  another stratum meanwhile. Harvest streamed output early.
- Stop a job when it only repeats known outcomes. Record the partial scope
  honestly.

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
2. a machine-readable certificate under `data/<thread>/`, which stays local and
   untracked, so the note must state its scope and regeneration command; and
3. a small verification program under `experiments/<thread>/` or `lib/`.

The verifier should check the certificate rather than repeat a broad search.
Record enough conventions that another researcher can interpret the witness
without reconstructing the discovery process.

## Independent verification

Prefer a small verifier with clear failure messages. Check inputs before use,
report the exact verified scope, and keep expensive discovery separate from
cheap re-verification. When independent software or a second implementation is
mathematically valuable, state what independence it provides; it is not a
routine requirement. Repeating the same deterministic discovery run is not
independent verification.

Use [`templates/COMPUTATION-SUMMARY.md`](../templates/COMPUTATION-SUMMARY.md)
for a durable human-readable record.
