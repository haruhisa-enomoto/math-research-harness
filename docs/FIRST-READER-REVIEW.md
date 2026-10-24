# Repository setup for continuous first-reader review

The installed `read-research-paper` skill contains the portable continuous
first-reader protocol. Its paired `write-research-paper` skill contains the
reusable direction and launcher templates. Their canonical source is recorded
in [`SKILLS.md`](SKILLS.md).

Read the portable protocol completely before supervising a run. The isolated
reader loads it through `read-research-paper` and must not load repository
research state or this writer-side setup overlay unless its frozen direction
explicitly permits that file.

Ordinary review artifacts belong in
`.research-scratch/<paper>/first-reader/`. Preserve a completed report in a
durable thread only when the owner authorizes that record. The repository's
`evals/` cases and gold files are always withheld from the reader.

## Report delivery

Select the portable protocol's `reader-persisted` or `supervisor-persisted`
mode before manuscript exposure, and put the selected mode and permitted
writing tool or response/handback channel in the frozen direction. Align any
host agent wrapper with that contract. Claude runs have repeatedly refused
subagent report-file writes; when those writes are unavailable or uncertain,
choose a permitted supervisor-persisted channel from the outset. The supervisor
saves each reader-authored section without substantive alteration before issuing
the next segment and makes the saved report available to the same reader.

The `Reading journal` remains a paragraph-anchored editorial report, preserving
purpose, pacing, cumulative burden, substantive questions, harmless delays,
and effective exposition. It is not an internal reasoning transcript. Keep
annotations distinct from diagnoses and proposed repairs. Existing historical
reports need not be rewritten to the new contract.

If delivery fails or a safety safeguard stops a response, record an incomplete
run, preserve delivered partial output, and stop. Do not bypass restrictions,
recover withheld content, or turn the failure into a request for an undelivered
journal. Resolve execution conditions before starting a fresh run from the
beginning. Protocol revisions do not establish that a provider will accept a
run; completion and report quality both need validation in an authorized review.

## Audience

When filling the direction's background slot, do not list the background the paper itself owes its reader, such as the classical
conjectures or results that motivate its problem, as already known. List only
general tools. Otherwise a missing motivation section is invisible to the
reader. Ask the reader to judge whether the opening motivates the problem for
a reader who does not know that history.
