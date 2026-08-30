# Repository setup for continuous first-reader review

The installed `read-research-paper` skill contains the portable continuous
first-reader protocol, and its paired `write-research-paper` skill contains the
reusable direction and launcher templates. Their canonical source is recorded
in [`SKILLS.md`](SKILLS.md).

Read the portable protocol completely before supervising a run. The isolated
reader loads it through `read-research-paper` and must not load repository
research state, or this writer-side setup overlay, unless its frozen direction
explicitly permits that file.

Ordinary review artifacts belong in `.research-scratch/<paper>/first-reader/`.
Preserve a completed report in a durable thread only when the owner authorizes
that record.
