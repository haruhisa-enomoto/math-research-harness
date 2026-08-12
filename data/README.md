# Machine-readable research artifacts

Store durable outputs and certificates under `data/<thread>/`. Pair each one
with a human-readable explanation in `results/<thread>/` and preserve the exact
generation or verification command.

Git ignores everything here except this file, and that is deliberate. Do not
track an output, do not stage one with `git add -f`, and do not relax the
`data/*` rule. Outputs live on local disk only.

The tracked record of a computation is therefore its `results/<thread>/`
summary, which must carry the manifest: exact computed scope, generation
command, backend and versions, expected invariants or hashes, and the `data/`
path where the output sits. Write it as if the reader could not open the
output, because a reader who clones the repository cannot.

See [`../docs/COMPUTATIONS.md`](../docs/COMPUTATIONS.md).
