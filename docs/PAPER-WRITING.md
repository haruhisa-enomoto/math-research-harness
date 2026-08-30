# Research-paper writing

Read this guide before drafting or revising a live research-paper manuscript.
It supplements any thread-specific style memo. It concerns mathematical
exposition, not merely TeX syntax or PDF layout. For a standalone owner-facing
report, also read [`REPORTS.md`](REPORTS.md).

## Authorship and identity

Authorship is owner-controlled. Unless the owner explicitly assigns their name
to a particular manuscript, do not use the owner's name, affiliation, address,
email address, or other identity metadata in its author block. Use the drafting
agent's name as the author instead.

Use the most specific agent or model designation reliably exposed by the
current environment, including its version or tier. Do not replace an
available versioned identity by a generic product label, and do not guess a
model identity that the environment does not establish.

Permission must be explicit for the manuscript at hand. Do not infer it from
the repository owner identity, author information in another paper, an existing
template, prior correspondence, or the owner's mathematical contribution. If
the owner specifies authorship or author metadata, reproduce only what was
authorized.

## The first-encounter standard

Write for a mathematician who has the background explicitly assumed by the
paper but who has not read the research ledger, internal proof notes, earlier
agent conversations, or the sources being cited. At each point in the paper,
the reader may use what has already been explained, but not definitions or
motivation that appear later.

A mathematically knowledgeable reader can often guess what an author means.
That is not enough. The text should make its intended meaning and the role of
each construction clear when it is first encountered. In particular, a
successful proof audit does not imply that the exposition passes this
first-encounter standard.

## Orient the reader before using the machinery

The beginning of a section or subsection should explain, in ordinary
mathematical language, what will be studied and why it is relevant to the
paper. Do not orient the reader by listing technical consequences whose
meaning has not yet been introduced.

For example, a section that passes to a quotient by a group action should first
say which group acts on which object, what the quotient is, and why the problem
under study transfers to it. Technical names for the machinery involved should
not be made to carry the opening explanation before the reader knows what they
mean.

There is no mandatory paragraph template. An order such as

```text
motivation -> definition -> statement -> proof -> interpretation
```

is one useful possibility, not a rule. The correct order depends on the
mathematics. The governing requirement is that every paragraph be
understandable at the point where it occurs and that the reader know why it is
there.

## Keep the authoring process out of the manuscript

A public mathematical document must state the mathematics directly. Do not
copy the wording of an instruction, prompt, review criterion, revision request,
or private discussion into the manuscript. Do not tell the reader what the
author or an agent was asked to do, which defects a referee reported, or which
internal constraint shaped a paragraph. Such information belongs in working
records or correspondence, not in the mathematical exposition.

Process-facing disclaimers are a common form of this error. Sentences such as
`We describe the proof without assuming the constructions used later`, `As
requested, we now explain ...`, or `The following was added to address a
reader's concern` do not explain the mathematics. Replace them by the
mathematical content: state the proof steps, define the construction before it
is used, or give the missing argument. Likewise, do not advertise that a
passage is self-contained, accessible, elementary, rigorous, or
publication-ready; make the passage satisfy that description.

This rule does not prohibit mathematical scope statements. A sentence such as
`The argument proves the case in which the extension splits, and does not
descend to the general case` conveys a mathematical boundary and should remain.
The test is whether the sentence changes what the reader knows about the
objects, hypotheses, result, proof, provenance of a mathematical input, or
scope. If it only reveals the authoring process, delete it.

### Hard boundary: private discussion is not manuscript content

**Conversational salience is never a criterion for inclusion in a public
manuscript.** The conversation controls the work; it does not supply the
paper's narrative. Every sentence, paragraph, remark, implementation detail,
qualification, and comparison must earn its place independently through the
mathematics presented to the reader: the problem, result, proof, necessary
context, or genuine reproducibility requirements.

Apply a counterfactual test during drafting and revision: if the same
mathematical result and evidence had been obtained without the private
conversation, would the passage still be needed in this paper at this point?
If not, delete it. This test applies regardless of the subject or form of the
private exchange and regardless of whether its wording has been disguised as
ordinary mathematical prose.

Audit violations at the level of purpose, not vocabulary. Removing an explicit
process phrase is insufficient when the passage's reason for existing still
comes from the private discussion. After removing such a passage, inspect the
surrounding transitions and section structure as well, since they may preserve
the same leaked agenda implicitly.

## Define before relying

Introduce every paper-specific symbol, construction, and term before relying
on it. Define nonstandard terminology explicitly. A less familiar standard
term should also be recalled when its precise meaning is load-bearing or when
the expected audience may not share one convention for it.

State the conventions the argument depends on — sidedness, base field or base
ring assumptions, finiteness hypotheses, and the class of objects considered —
wherever they are used. The conventions in
[`PROJECT-FOUNDATIONS.md`](PROJECT-FOUNDATIONS.md) are internal boot state, not
something the reader of the paper knows.

Prefer the mathematical property itself to an unexplained label. For example:

- do not coin a label such as `projective boundary` when the argument means
  that an indecomposable object is projective; say the latter;
- do not call an object `small` or `bounded` before stating the finiteness
  property actually used, such as finite projective dimension, finite length,
  or a uniform bound on the ranks in a resolution;
- before using a term such as `reflexive` or `torsionless`, state the concrete
  embedding, quotient, or duality property needed in the argument; and
- do not import internal research labels such as `route`, `stratum`, `wall`,
  `core`, or `profile` unless they name a genuinely useful object that has
  first been defined mathematically.

Typography does not define a term. Emphasizing an unexplained word with
italics can make the interruption worse by suggesting that the reader should
already recognize a formal concept.

A vocabulary report is an audit prompt, not a list of forbidden strings.
Replacing an opaque noun by the corresponding verb does not explain the
mathematics: for example, changing "forwardness of the arrow" to "the arrow
points forward" leaves the same ambiguity. State the relation actually used,
such as \(\operatorname{pd} U<\operatorname{pd} V\), the inclusion
\(X\in\mathcal C\), or the specific map and its source and target. To run the
check, see [`../paper/vocab/README.md`](../paper/vocab/README.md).

## Prefer exact mathematical predicates to prose paraphrases

When a sentence merely paraphrases a short mathematical condition, state the
condition in notation. In particular, prefer

```text
Assume that \(\operatorname{Hom}_A(M,K)\ne 0\).
Choose an indecomposable direct summand \(Z\) of \(K\) such that
\(\operatorname{Hom}_A(M,Z)\ne 0\).
```

with the Hom conditions written as formulas, to idioms such as `K receives a
nonzero map from M`. The same rule applies to vanishing, containment,
factorization, injectivity, surjectivity, and equality when the exact predicate
is shorter and easier to parse than its prose description.

This is not a rule to replace mathematical prose by strings of symbols.
Natural language should explain the logical movement and the purpose of a
construction. The formula should state the mathematical fact on which that
explanation depends. For example, after writing an invariant equality such as
\(\operatorname{grade} M=n\), say precisely which evaluation map remains to be
proved injective or surjective; do not replace this by an abstract sentence
about the object being controlled in that degree.

Avoid English-dependent spatial or directional paraphrases when they conceal a
standard predicate. Expressions such as `the extension dies`, `the syzygy
stabilizes`, `the object survives the shift`, or `the map passes through the
projectives` are useful only when they have already been given a precise
meaning and genuinely shorten a repeated argument. Otherwise write the
cohomology group, membership relation, factorization, or equality that is
actually used.

## Make every reference recoverable locally

Write so that the reader can understand each sentence while reading forward. A
technically available antecedent is not enough if recovering it requires
backtracking, remembering several objects, or noticing that the ambient
category or ring has changed. Repeat the notation when that is clearer than a
pronoun or descriptive placeholder.

In particular, avoid phrases such as `the two restricted classes`, `the former
map`, `the remaining term`, or `this group` unless the referents are both
immediate and unique. State an equality such as

```text
\(\operatorname{Ext}^i_A(\Omega M,A)\cong\operatorname{Ext}^{i+1}_A(M,A)\)
for every \(i\ge 1\)
```

before summarizing its consequence. A display which appears only after an
opaque sentence does not make that sentence forward-readable.

Do not introduce an informal English name for a condition already expressed
more clearly by notation. For example, if the argument uses
\(\operatorname{pd}_A M<\infty\), do not call \(M\) `resolvable` unless that
term has been explicitly defined, is used consistently, and genuinely reduces
the reader's work.

Use one established term for one notion. Do not add a near-synonym merely to
emphasize a property that the notation already makes explicit. A paper that has
fixed one name for a class of objects does not also need a second, equivalent
name for the same class.

## Control the symbol budget and diagram the maps

Every long-lived symbol adds to the reader's working memory. Before naming an
object, ask whether the name gives it a genuine conceptual role or merely
aliases a short standard construction. Prefer \(\Omega M\) to a new symbol
\(N:=\Omega M\), and \(\operatorname{Ext}^n_A(M,A)\) to a new symbol for that
group, unless the alias is used often enough to make the proof materially
easier to read. Confine dummy variables for individual morphisms or test
objects to the paragraph in which they are used.

When the argument depends on the relation among several objects and maps,
display that relation before using it. A commutative diagram is normally
helpful when three or more objects participate in a factorization, pullback,
pushout, exact sequence, comparison of two resolutions, or comparison of
induced maps. Label the maps and state the exact kernel, image, or universal
property used. The diagram should reduce the number of relations the reader
must reconstruct from prose; it does not replace the argument.

## State cited inputs mathematically

A theorem name, an author's name, or a citation is not an explanation of what
the paper uses. Before applying a cited result, state its relevant input and
output, including hypotheses and conventions. The citation then supports that
precise statement.

The reader should not have to know in advance what a named correspondence or
classification says, nor should the reader have to consult the source merely
to discover why it is relevant. If only a numerical consequence or a
restricted case is needed, state that consequence rather than invoking a
larger theory rhetorically.

Do not turn an ordinary descriptive phrase into an apparent theorem name by
attaching an author's name to it. A label of the form `<Author>'s vanishing
criterion` suggests an established name which the reader should already know.
Introduce the result instead:

```text
To decide when the invariant vanishes in all large degrees, we use the
following criterion, proved in [citation].
```

Then state the criterion. Similarly, prefer `<Author> and <Author> prove that
...` to `the vanishing theorem of <Author>--<Author>` unless the latter is a
genuinely established theorem name. The expressions `the following criterion`,
`the following numerical equality`, and `the following bijection` are ordinary
descriptions of results being introduced at that point; they do not claim a
standard name.

This distinction remains important when the precise statement immediately
follows. A homemade possessive label still makes the reader stop to decide
whether it denotes familiar terminology. Use a named theorem or correspondence
only when that name is conventional in the intended field. In all other cases,
say what problem the cited result addresses, attribute it in ordinary prose,
and give the exact assertion used.

## Make proof movement explicit

When proving an equivalence, identify both directions by their actual
assumptions and conclusions. Avoid phrases such as `the nontrivial direction`
when the reader must stop to determine which implication is meant. It is fine
for one direction to be immediate, but say explicitly why it is immediate.

This matters particularly for implications between named conjectures or
properties. Say whether an implication holds between the statements for one
fixed object or between the universal statements quantified over a whole class,
and say where the argument replaces one object by another. Do not let the
manuscript blur the two levels the way an abbreviation can.

Likewise, a transition such as `this proves the assertion` should have an
unambiguous nearby assertion. Pronouns and directional shorthand are useful
only when their referents are immediate.

Do not compress a proof merely because an expert can reconstruct it. Include
the intermediate implication when it explains why a hypothesis is present,
why a construction is well defined, or why a collective closure property is
stronger than the corresponding objectwise check.

## Give long proofs visible mathematical structure

A proof which contains several logically distinct reductions or auxiliary
assertions should not remain one uninterrupted sequence of paragraphs when
internal claims would make the dependencies easier to follow. State each
load-bearing intermediate assertion as a claim, prove it at the point where it
is introduced, and use the claim explicitly afterward. In particular, when a
long technical argument proves two conditions which together imply the
theorem, first state and prove that reduction; the reader should know why each
condition is being proved before entering its proof.

An internal claim should state an exact mathematical assertion, not an
editorial description of the proof. Its surrounding transition should also
state its mathematical role. Avoid sentences such as `we now state what
remains to be proved`; write instead, for example, `By Claim 2, it remains to
prove the two vanishing statements in (4.3).` Once a reduction claim has been
proved, do not repeat its construction after proving its hypotheses: invoke the
claim or arrange the proof so that the last required assertion closes the
argument.

Length alone does not require numbered claims. Use descriptive case headings
when the proof is principally a case division, and use short transition
sentences when the argument is linear. Do not fragment a proof into claims
which are used only in the next sentence and do not reduce the reader's working
memory. The purpose of the structure is to expose the dependency graph of the
proof, not to add typography.

## Report computational evidence honestly

When the paper rests on a finite computation, state its exact scope, the
conventions under which it was run, and what it does and does not establish. A
computed range is not a theorem about every object in the class. If the paper
presents a counterexample found by search, give the object explicitly enough
that the reader can verify it independently, and cite the certificate.

## Keep optional interpretation optional

Related theories, alternative terminology, historical associations, and
possible future uses can enrich a paper, but they should not obstruct the main
argument. Put them after the relevant mathematics has been made clear, often
in a short remark. Define the associated terminology and say concretely what
connection is being observed.

For instance, if a condition under study is to be related to a known class of
objects or to a derived invariant, first develop the argument in the paper's
own terms. A later remark may then define that terminology and explain what
additional structure it suggests. A bare sentence equating several
unintroduced names adds no usable information.

## Blind-reader review

A blind review is a first-encounter test, not merely an expert correctness
audit. When assigning one:

1. give the reviewer no conversational or internal proof context;
2. ask the reviewer to read in manuscript order and not use later definitions
   to excuse an unclear first occurrence;
3. require page- or line-specific annotations for every unexplained term,
   symbol, metaphor, citation, proof direction, and transition;
4. ask the reviewer to paraphrase the purpose of each section and substantial
   paragraph, marking places where that purpose is not recoverable locally;
5. tell the reviewer not to silently repair the prose from subject expertise;
   and
6. distinguish mathematical gaps from exposition that is technically
   reconstructible but needlessly difficult to read.

The lead agent must then reread the manuscript under the same conditions.
Calling a reviewer `blind` does not certify the paper. A list of reported
defects is not a sufficient checklist: repeated local defects may reveal that
the exposition needs a broader rewrite.

For the full relay protocol, see
[`FIRST-READER-REVIEW.md`](FIRST-READER-REVIEW.md).

## Manuscript vocabulary check

Before freezing a prose revision for independent regression, run the repository
vocabulary checker on every active manuscript TeX source as specified in
[`../paper/vocab/README.md`](../paper/vocab/README.md). Rebuild the lexicon
first when eligible source TeX under `references/` has been added or changed.
The normal check writes `vocabulary-report.json` and `vocabulary-report.md`
beside manuscript TeX files that share a directory; choose the manuscript root
explicitly with `--report-dir` when active sources span directories.
`--stdout-only` is exploratory and does not satisfy the recorded check.

A vocabulary report locates passages for exposition review. It is not a list of
forbidden strings and does not pass or fail a manuscript. Inspect every flag at
its manuscript location. Before changing a spelling, decide whether the phrase
is an undefined or unnecessary label, an ambiguous English substitute for an
exact mathematical predicate, an apparent theorem name, a citation standing in
for the result used, or private-process language, and repair the mathematical
statement or its role when needed.

Consider spelling or hyphenation only after the phrase itself is precise,
necessary, and properly introduced. Never change a token merely to remove a
flag. For every justified hyphenated form, inspect the exact hyphenated, open,
and solid comparison. Raw occurrence counts and general-English hyphenation
rules do not establish mathematical usage; use the author-signature and
distinct-paper breadth together with the mathematical context. A correct
specialized term may remain flagged, and sparse or mixed evidence may support
retaining it.

The gate is complete when the checker has run on every active TeX source at the
exact revision and every flag has been inspected and adjudicated, not when the
report has no warnings. Cluster recurring semantic causes in the ordinary
revision batch rather than making one mechanical edit per token, and rerun
after any accepted wording repair. A later prose edit invalidates the recorded
check. Do not give vocabulary reports or their adjudication to an isolated
reader, or count this writer-side diagnostic as independent reading evidence.

## Revision check

Before declaring a manuscript revision complete, check at least the following.

- Can the intended audience explain the purpose of every section from its
  opening paragraphs?
- Is each term and symbol meaningful at its first occurrence?
- Are the load-bearing conventions — sidedness, base field or ring assumptions,
  finiteness hypotheses, and the class of objects — stated wherever the
  argument depends on them?
- Does every cited result appear with the precise mathematical content used?
- Have author possessives and phrases such as `the theorem of`, `the
  correspondence of`, or `X's criterion` been checked to ensure that they are
  established names rather than labels coined by the manuscript?
- Are both directions of equivalences and reductions identifiable without
  backtracking, and is the fixed-object or universal level of each implication
  explicit?
- Does every long proof expose its main reductions and auxiliary assertions
  through internal claims when that clarifies their dependencies, while using
  descriptive headings rather than artificial claims for pure case divisions?
- Have internal metaphors and proof-development jargon been removed or
  replaced by mathematical statements?
- When prose describes a precise vanishing, containment, factorization,
  injectivity, surjectivity, or equality condition, would the corresponding
  formula be shorter and clearer?
- Can every pronoun or descriptive placeholder be resolved from the current
  sentence or the immediately preceding display, without backtracking or
  changing an ambient object silently?
- Does every named object need its own symbol, and has every load-bearing
  configuration of several maps been considered for a commutative diagram?
- Does every computational claim state its exact scope?
- Are optional interpretations placed after, rather than in place of, the
  main explanation?
- Did the revision address recurring causes, rather than only the individual
  sentences flagged by a reviewer?
- Has every reference to prompts, instructions, review history, internal
  records, agent behavior, or the revision process been removed from the
  public mathematical text?

Compilation, reference checking, and visual inspection remain necessary, but
they test the artifact rather than the reader's understanding.
