# Computational research records

Projects may use GAP, SageMath, Mathematica, Macaulay2, Magma, Lean, Python,
Julia, Rust, or other systems suited to the research. These rules explain how
to preserve computational evidence so that it can be checked later.

Read Choosing and recording backends before depending on an engine, and Search
discipline before any search. For durable results read Working layers, Durable
computation package, Data is local, Evidence scope, and Independent
verification; counterexamples additionally require Counterexamples and
refutations. Disposable probes keep the backend and exactness rules but need no
durable package.

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
engine boundary. A construction taken from the literature is no exemption: computing
an invariant of a complex, resolution, or presentation copied from a paper is
an engine computation.

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

Read the engine version at runtime (for a Python package, for example with
`importlib.metadata.version`) rather than hard-coding it in a record, and do not
gate preflight, execution, or certificate reuse on a commit allowlist. A new
release of a pinned engine does not by itself require regenerating results that
passed under an earlier one.

### Completeness certificates

Prefer an enumeration method whose termination certifies completeness, such as
closing a finite seed set under a generation process that a theorem shows must
reach every object, over a census bounded by size, degree, or length. Run such
a method without a cap when finiteness is known or expected; use a finite cap
only as an explicit resource guard for a diagnostic, and treat a cap hit as
incomplete evidence even when neighbouring cases finish. A bounded census is
exhaustive only through its stated bound. Two convenient cutoffs that happen to
agree do not make it complete. Supply an independently known count, when one
exists, as an additional cross-check.

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

`.gitignore` excludes all of `data/` except its README. This is deliberate and
permanent. Do not track a file under `data/`, do not stage one with `git add
-f`, and do not relax the `data/*` rule to get an output committed. An output
that seems too important to lose is not an exception; it is a reason to write a
better manifest.

Machine-readable outputs therefore exist on local disk only. The tracked record
of a computation is its `results/<thread>/` summary, which must carry the
manifest: exact computed scope, the generation command, backend and versions,
expected invariants or hashes, and the `data/` path where the output sits.
Write it as if the output were unavailable to the reader, because for anyone
cloning the repository it is.

Validation effort is proportional to mathematical and implementation risk.
For a deterministic closed computation, one successful complete run plus
targeted sanity checks is normally sufficient. Do not rerun a broad search
solely to demonstrate byte-for-byte reproducibility. A hash is optional for a
small checked-in deterministic artifact; it is most useful for large or
externally stored output, transfer integrity, or later comparison.

Run tests that exercise changed reusable code or a concrete failure risk. A
full repository test suite is appropriate after broad shared-library or
environment changes, not as a routine gate for every one-off experiment.
Formatting checks are maintenance checks, not computational verification
evidence. Reserve repeated runs, independent software, or a second
implementation for suspected nondeterminism, reusable engine or library
changes, candidate counterexamples, and unusually load-bearing results.

## Search discipline

For exact finite searches, use strata with explicit case boundaries and close
each claimed stratum completely. Reduce cases by justified symmetries, avoid
recomputing certified closed regions, and report exact scope and counts.
Human-facing exact hunts default to no coverage caps. An optimization budget
must fall through to complete work; a bounded diagnostic labels its incomplete
scope. Sampling does not certify an exact stratum.

Time a small pilot before a long job. Split or checkpoint expensive work without
shrinking an authorized exact target. Repeated known outcomes justify stopping
an exploratory probe, but do not excuse missing exact-search coverage unless
a valid mathematical pruning argument removes those cases. Report an interrupted
search's partial scope honestly. Operational failures checkpoint evidence and
stop loudly; repeating the same command retries automatically.

While a long job runs, pursue useful independent in-scope work when available;
do not create another stratum merely to stay busy. Harvest streamed evidence
and monitor the run as needed.

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
