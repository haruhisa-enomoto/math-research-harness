# Collaboration and briefings

The default unit of responsibility is one repository-aware lead agent. Optional
parallel work and external consultation support that lead; they do not replace
its responsibility or enlarge the owner-authorized scope.

## Internal subagents

Use internal subagents only when work decomposes into bounded, nonconflicting
tasks such as an independent proof attempt, counterexample search, computation,
literature check, or audit.

The lead:

- assigns exact tasks and avoids conflicting file ownership;
- preserves the provenance of returned claims;
- audits surprising or load-bearing conclusions in proportion to their role;
- synthesizes disagreements rather than selecting the most convenient answer;
- alone edits canonical state and creates the scoped checkpoint commit.

Parallelism is optional. A task with one compelling route may be better handled
by one agent.

## Collaborators without repository access

An outbound briefing is a self-contained research handoff assembled from
`docs/PROJECT-FOUNDATIONS.md`, the relevant ledger, and cited evidence—not from
memory. It states:

- the applicable common foundations and their evidence status;
- the exact delegated question;
- definitions and conventions required to understand it;
- the established and refuted boundary, with evidence status;
- important failed routes only when they prevent wasted repetition;
- the desired form of the response; and
- what the recipient is not authorized to change.

Store a reusable briefing under `briefings/outbound/`. A newer briefing may
explicitly supersede an older one for the same recipient or purpose.

Preserve an inbound response under `briefings/inbound/` with its source and date.
It is correspondence, not canonical proof evidence. When it yields a coherent
durable package, absorb that package through a research note recording what was
checked, what was already known, and the actual canonical implications. Audit
load-bearing claims before relying on them.

The templates in `briefings/templates/` demonstrate both directions without
including real transcripts.
