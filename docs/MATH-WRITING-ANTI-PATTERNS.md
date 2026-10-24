# Mathematical English Writing Guidelines and AI Anti-Patterns

This document catalogs recurring AI-generated and harness-induced prose anti-patterns found in mathematical manuscripts, together with concrete principles and before/after examples for writing natural, clear mathematical English.

---

## Core Principle

Good mathematical prose guides a human mathematician's mental model. Every sentence should make clear **what is being assumed or chosen**, **what operation or theorem is being applied**, and **what mathematical conclusion follows**. Brevity achieved by deleting logical connectives or turning nouns into actors makes proofs harder—not easier—to read.

---

## Anti-Pattern 1: Inanimate Agency ("X makes Y do Z", "X writes Y", "X puts Y in Z")

AI revisions that try to compress word count frequently make abstract properties, equations, or theorem numbers the active subject of physical or causative verbs (*make*, *put*, *write*, *force*, *send*, *kill*, *turn*). While standard mathematical English allows natural mathematical subjects (*"The functor $F$ preserves exactness"*, *"The sequence splits"*), a property or citation cannot physically manipulate objects.

### Bad vs. Good Examples

* **Bad:** *"Nilpotence then writes every element as a polynomial in $t$, giving $C\cong k[t]/(t^N)$."*
  **Good:** *"Since $\rad C$ is nilpotent, $t$ generates $C$ as a $k$-algebra, so $C \cong k[t]/(t^N)$ for some $N \ge 1$."*

* **Bad:** *"Linear independence therefore makes exactly one summand nonzero, equal to $b$."*
  **Good:** *"By linear independence, only one summand can be nonzero, so $b \in e_i B_0 e_j$ for a unique pair $(i,j)$."*

* **Bad:** *"Irreducibility makes either the surjection onto the image a split monomorphism or the inclusion of the image a split epimorphism."*
  **Good:** *"Since the map is irreducible, either the canonical surjection onto its image is a split monomorphism or the inclusion of its image is a split epimorphism; in either case, the map is injective or surjective."*

* **Bad:** *"The parenthesized terms have degree $n-1$, so induction puts them in the mesh ideal and hence puts $F$ there as well."*
  **Good:** *"Since each parenthesized term has degree $n-1$ and vanishes in $\mathcal{C}$, it belongs to the mesh ideal by the induction hypothesis; hence so does $F$."*

* **Bad:** *"Lemma 9.6 would then make every path of the prefix two-sided, a contradiction."*
  **Good:** *"By Lemma 9.6, every path representing this prefix would then consist of two-sided arrows, a contradiction."*

---

## Anti-Pattern 2: Telegraphic / Imperative "Pseudocode" Proofs

AI-generated proofs often degenerate into a string of short, disconnected imperative sentences (*"Eliminate... Give... Reverse... Assign... Apply..."*) or bare assertions without logical connectives (*since*, *because*, *moreover*, *consequently*, *it follows that*). This forces the reader to reconstruct the logical relation between adjacent sentences.

### Bad vs. Good Examples

* **Bad:**
  > *"Eliminate triangles along finite mate chains as in Lemma 4.2, leaving the periodic subcomplexes untouched. Give the remaining edges outside those subcomplexes weight zero. Reverse the eliminations. At each step the two retained edges of a triangle have weights, and its third edge was removed at that step. Assign that edge the unique weight making the boundary sum zero. This restores all triangles without changing any prescribed periodic weight."*
* **Good:**
  > *"As in the proof of Lemma 4.2, we may successively collapse the triangles along all finite mate chains without touching the periodic subcomplexes. We assign weight zero to all nonperiodic edges that remain after this collapse, and then restore the collapsed triangles in reverse order: since each restored triangle has a unique free edge, its weight is uniquely determined by requiring the boundary sum around the triangle to vanish. This extends the given weight to all of $K$."*

---

## Anti-Pattern 3: Conflating Mathematical Objects with Their "Labels" or Indices

AI text often over-distinguishes or clumsily conflates an object with its notation, calling modules or vertices *"labels"* (*"At a nonprojective label $X$"*, *"Restrict these functors to the projective labels $P_x$"*, *"evaluated injective labels"*).

* **Rule:** Call mathematical objects what they are: *objects* of $\mathcal{C}$, *vertices* of $\Gamma_A$, or *indecomposable projective modules* $P_x$. Reserve the word *label* for actual combinatorial labels on edges or tables when distinct from the objects themselves.
* **Bad:** *"At a projective label $P$, the initial forms of the components of $\rad P \to P$ give a monomorphism in $\operatorname{add}\mathcal{C}$."*
* **Good:** *"For an indecomposable projective module $P$, the initial forms of the components of the inclusion $\rad P \hookrightarrow P$ define a monomorphism in $\operatorname{add}\mathcal{C}$."*

---

## Anti-Pattern 4: Compressed Private Shorthand Instead of Standard Mathematical Phrasing

When summarizing a case analysis or formula, AI prose frequently invents compressed noun phrases that are not standard mathematical English and require the reader to reverse-engineer the underlying formula:

* **Bad:** *"An unshiftable output permits no surviving substitution, so its equation is $0=0$."*
  **Good:** *"When $t = rs$ is unshiftable, both $r^+ s$ and $r s^+$ vanish, so $\epsilon_L = \epsilon_R = 0$ and the equation reduces to $0=0$."*
* **Bad:** *"The Hom of a generating ray $f: x \to y$ is cyclic at $x$ if $A_0(x,y) = R_x f$."*
  **Good:** *"For a generating ray $f \in A_0(x,y)$, we say that the corner bimodule $A_0(x,y)$ is cyclic at $x$ if $A_0(x,y) = R_x f$."*
* **Bad:** *"Different blocks multiply to zero by orthogonality. They give a unital section $S \hookrightarrow B$."*
  **Good:** *"Since the idempotents of distinct blocks are orthogonal, these matrix units multiply to zero across different blocks and therefore define a unital algebra embedding $S \hookrightarrow B$."*

---

## Anti-Pattern 5: Citation and Cross-Reference Clutter in Narrative Overview Sections

In an Introduction or Part overview, inserting parenthetical internal references (`Proposition 2.5`, `Corollary 3.12`, `Lemma 6.3`, `Theorem 7.7`) into nearly every sentence turns a conceptual narrative into a compilation log. At the start of a paper, the reader does not yet know what the numbered lemmas say.

* **Rule:** In narrative overview subsections, explain the mathematical ideas and logical flow in self-contained prose, anchoring only the main theorems or section numbers. Place detailed section-by-section and theorem-by-theorem maps in the dedicated **Reading routes** or **Organization** subsection.

---

## Anti-Pattern 6: Prematurely Introducing Global Induction Machinery Inside a Local Section

Placing global inductive definitions and theorem statements at the beginning of a section whose actual content is local and independent of the induction splits the reader's attention and obscures dependencies.

* **Rule:** Keep local structural sections self-contained, or clearly explain upfront why a global inductive statement is being recorded before the local subsections begin.

---

## Anti-Pattern 7: Wall-of-Text Convention Blocks and Mid-Argument Convention Interruptions

Dropping a global convention remark (*"Here and throughout, in a product of maps the map on the left is applied first"*) in the middle of motivating a theorem interrupts the mathematical narrative. Conversely, packing twenty different conventions into a single unbroken paragraph at the end of the introduction makes them hard to look up.

* **Rule:** State a brief, natural reminder where first needed in the introduction, and organize the **Conventions and notation** subsection into clearly separated, thematic paragraphs (e.g., *Algebras and modules*, *Composition and opposite algebras*, *Category algebras and radicals*).

---

## Anti-Pattern 8: Omitting the Crucial Algebraic Trigger in Poset or Case Proofs

In AI-compressed combinatorial or poset arguments, the text often asserts that a configuration is a crown or that a product is nonzero without writing the single associative identity that makes the assertion true. This forces the reader to stop and do scratch work to see how the hypothesis is used.

* **Bad:** *"If both $a_1,a_2$ were two-sided, the four support points $a_1,a_2,f,\widehat q_xf$ would be a crown."*
  **Good:** *"If both $a_1$ and $a_2$ were two-sided, then $\widehat q_xa_i=a_i\widehat q_{y_i}$, so $\widehat q_xf=a_i(\widehat q_{y_i}w_i)$ would be right-divisible by both $a_1$ and $a_2$, as is $f=a_iw_i$; thus $\{a_1,a_2,f,\widehat q_xf\}$ would form a four-point crown in the faithful projective support at $x$."*
* **Bad:** *"Write $fh=q_x^b\ne0$ with $b$ minimal. Then $hf\ne0$, so $hf=q_y^d$."*
  **Good:** *"Write $fh=q_x^b\ne0$ with $b\geq1$ minimal. Since $f(hf)=(fh)f=q_x^bf\ne0$ (by hypothesis), we have $hf\ne0$, so $hf=q_y^d$ for some $d\geq1$."*

---

## Anti-Pattern 9: Unstructured Multi-Branch Case Analyses

When a proof branches into several cases (e.g., Dynkin types $A,D,E$, or five combinations of endpoint types, or a four-step covering argument), AI prose often runs the cases together as unlabelled paragraphs with telegraphic transitions (*"For the odd quotient..."*, *"Now set $M=2N+1$..."*).

* **Rule:** Use explicit structural signposts—either `\medskip\noindent\textbf{Step 1: ...}` for sequential multi-step proofs or `\begin{itemize} \item \emph{Case 1: ...}` for parallel case analyses—and state at the outset why the listed cases exhaust all possibilities.

---

## Anti-Pattern 10: Heavy Noun-Cluster Compounding ("Stacked Modifiers")

To pack qualifications into a single noun phrase, AI prose often stacks three or four nouns or participles before a head noun instead of using normal prepositional phrases (`of`, `for`, `in`) or relative clauses.

* **Bad:** *"the rightmost surviving return arrow factor"*
  **Good:** *"the last factor in the path that returns to $x$ without vanishing"*
* **Bad:** *"the non-source simple module Ext-vanishing condition"*
  **Good:** *"the condition that $\operatorname{Ext}^1_A(S_i, S_j) = 0$ for all non-source vertices $i$"*

---

## Quick Diagnostic Checklist for a Prose Polish Pass

When reading a draft `.tex` file, scan specifically for these surface signals:

1. **Verb check:** Search for `makes`, `puts`, `writes`, `forces`, `sends`, `kills`, `turns`, `permits`, `forbids`. Ask whether the subject is an abstract property or citation acting as a physical agent; if so, rewrite with `Since ...`, `By ...`, or `Consequently, ...`.
2. **Imperative-chain check:** Look for paragraphs with three or more consecutive imperative sentences (`Choose...`, `Apply...`, `Set...`, `Eliminate...`, `Give...`, `Reverse...`). Rewrite using first-person plural (`We first choose...`, `Applying Lemma X, we obtain...`) and explicit logical connectives.
3. **Patch-accretion check:** Look for sentences with multiple semicolons, parenthetical cross-references wedged into the middle of a clause, or trailing clauses tacked onto the end of a long sentence. Split them into two clean sentences in logical order.
4. **Notation-vs-object check:** Search for `label`, `slot`, `spot`, `entry`, `output`, `target`, `intended` used where a mathematical object (module, vertex, morphism, basis element, subcategory) is meant.
5. **Trigger-identity check:** In any proof by contradiction or poset/case verification, check whether the key implication is stated as a bare assertion (*"then $X$ is a crown"*, *"then $hf \neq 0$"*) and, if a one-line identity makes it immediate, write that identity explicitly.
