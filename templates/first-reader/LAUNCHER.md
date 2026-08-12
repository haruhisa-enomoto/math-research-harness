# Launcher notes: first-reader review

<!--
TEMPLATE.  See docs/FIRST-READER-REVIEW.md.
This file is for the supervisor.  Readers are forbidden to open it by
DIRECTION.md.  Never merge it into DIRECTION.md: an agent pointed at a file
reads the whole file, so a "do not read past this line" marker is not a
boundary.
-->

**Readers must not open this file.**  It holds the segment table, which
tells you the shape of the rest of the paper.

## Segment table

Size each segment when you issue it, from the block count of what remains —
do not fix the whole table in advance.  Target 6 to 10 blocks; only forward;
never split a proof.  Record what you issued:

| Key | Scope | Lines | Blocks |
|-----|-------|-------|--------|
|     |       |       |        |

Block count for a candidate range:

```bash
awk 'NR>=A && NR<=B && /^[[:space:]]*$/ {c++} END{print c+1 " blocks"}' <paper>
```

Segment file to hand over (cumulative — everything read so far, nothing
after):

```bash
sed -n "1,${END}p" <paper> > segments/through-<KEY>.tex
```

## Launch message

Send to a fresh reader with no prior context:

    You are a first reader.  Follow <path>/DIRECTION.md exactly.
    Your agent label: <LABEL>.
    Your first segment: <KEY>, lines <a>--<b>, in <segment file>.

Add nothing else.  Any extra word of guidance is forward information from a
contaminated launcher.

## Checking a segment: process only

The launcher has usually read the manuscript, or wrote it.  Both are
contaminated.  The check is therefore restricted to process.

- Did the reader cover the whole range, block by block?
- Are entries reading experience, or content summary?
- Did it append rather than rewrite?
- Did it use the flag categories, and keep `[gap]` separate?
- Did it stop at the end of its range?

Verify coverage mechanically:

```bash
awk 'NR>=A && NR<=B && /^[[:space:]]*$/ {printf "%s ", NR}' <paper>; echo
grep -n '^\*\*<KEY>\.' report-*.md
```

Never say or hint that the reader missed a passage, term, or difficulty.
Never confirm or deny that a flag is correct.

Approvals must be uniform in tone and length, so the reader cannot infer
approval or disappointment from how the next message reads:

    Recorded. Next segment: <KEY>, lines <a>--<b>.

If a process rule was broken, state the rule and the remedy in one sentence,
then give the same fixed form.

## Closing

    Recorded. The manuscript is finished. Append the Findings and Verdict
    sections as specified in the direction.

## Totals

Recompute from the report file; never accumulate across turns.

```bash
for f in meaning order cite idiom purpose gap; do
  printf "%-8s %s\n" "$f" "$(sed -n '1,/^## Findings/p' report-*.md | grep -o "\[$f\]" | wc -l)"
done
```

## Run log

Record aborted runs and the setup defect that caused them.  These are the
part of the protocol that cannot be reconstructed from first principles.
