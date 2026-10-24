"""Build and apply a small, owner-approved vocabulary corpus.

Unlike :mod:`tools.lexicon`, which measures wording against the repository's
broad literature collection, this tool uses an explicit manifest.  It treats
words from owner papers as established personal vocabulary and accepts a word
from comparison papers only when at least a configured number of distinct
papers use it.  A flag is an item for editorial discussion, never an automatic
instruction to rewrite mathematics.

Run from the repository root, for example::

    uv run python -m tools.strict_vocabulary \
      --manifest paper/example/strict-vocabulary/corpus-manifest.json \
      --target paper/example/main.tex paper/example/body.tex \
      --out paper/example/strict-vocabulary
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from tools.lexicon import derived_from, is_english, now, parts, read, strip_tex, tokens


REPO = Path(__file__).resolve().parent.parent
GROUPS = ("owner", "comparison")


def load_manifest(path: Path) -> dict:
    """Load and validate an explicit strict-corpus manifest."""
    manifest = json.loads(path.read_text(encoding="utf-8"))
    entries = manifest.get("papers")
    if not isinstance(entries, list) or not entries:
        raise ValueError("manifest must contain a nonempty 'papers' list")

    seen_keys: set[str] = set()
    comparison_authors: set[str] = set()
    for entry in entries:
        missing = {"group", "key", "title", "authors"}.difference(entry)
        if missing:
            raise ValueError(
                f"manifest entry lacks required fields: {sorted(missing)}"
            )
        if entry["group"] not in GROUPS:
            raise ValueError(f"unknown corpus group: {entry['group']}")
        if entry["key"] in seen_keys:
            raise ValueError(f"duplicate corpus key: {entry['key']}")
        seen_keys.add(entry["key"])
        if not isinstance(entry["authors"], list) or not entry["authors"]:
            raise ValueError(f"paper {entry['key']} has no approved authors")
        if entry["group"] == "comparison" and manifest.get(
            "require_distinct_comparison_authors", False
        ):
            repeated = comparison_authors.intersection(entry["authors"])
            if repeated:
                raise ValueError(
                    "comparison authors must be distinct across papers: "
                    + ", ".join(sorted(repeated))
                )
            comparison_authors.update(entry["authors"])
    return manifest


def load_decision_policy(path: Path | None) -> dict:
    """Return exact unigram families recorded in an owner decision file."""
    empty = {
        "source": None,
        "approved": set(),
        "conditional": set(),
        "not_approved": set(),
        "non_prose": {},
    }
    if path is None:
        return empty
    record = json.loads(path.read_text(encoding="utf-8"))

    approved: set[str] = set(record.get("approved_exact_forms", []))
    for family in record.get("approved", []):
        for term in family.get("terms", []):
            approved.update(word for word, _ in tokens(term))

    conditional = {
        word
        for item in record.get("conditional", [])
        for word, _ in tokens(item.get("term", ""))
    }
    not_approved = {
        word
        for item in record.get("not_approved", [])
        for word, _ in tokens(item.get("term", ""))
    }
    non_prose = {
        item["term"].casefold(): item["reason"]
        for item in record.get("non_prose_exact_forms", [])
    }
    return {
        "source": str(path),
        "approved": approved,
        "conditional": conditional,
        "not_approved": not_approved,
        "non_prose": non_prose,
    }


def extract_paper(root: Path, entry: dict) -> tuple[Counter, list[str], list[str]]:
    """Return prose counts, used files, and skipped duplicate files."""
    item = root / "references" / "items" / "arxiv" / entry["key"]
    if not item.is_dir():
        raise FileNotFoundError(f"missing approved source item: {item}")

    item_words: Counter = Counter()
    used_files: list[str] = []
    duplicates: list[str] = []
    seen_file_tokens: dict[tuple[str, ...], str] = {}
    for source in sorted(path for path in item.rglob("*.tex") if path.is_file()):
        prose = strip_tex(read(source))
        file_tokens = tuple(word for word, _ in tokens(prose))
        counts = Counter(file_tokens)
        if not is_english(counts):
            continue
        relpath = str(source.relative_to(root))
        if file_tokens in seen_file_tokens:
            duplicates.append(relpath)
            continue
        seen_file_tokens[file_tokens] = relpath
        item_words.update(counts)
        used_files.append(relpath)

    if not item_words:
        raise ValueError(f"approved source contains no usable English TeX: {item}")
    return item_words, used_files, duplicates


def write_vocabulary(
    path: Path,
    occurrences: Counter,
    paper_support: dict[str, set[str]],
) -> None:
    """Write one group's exact-form vocabulary in a stable TSV format."""
    with path.open("w", encoding="utf-8") as handle:
        handle.write("word\tpapers\toccurrences\tpaper_keys\n")
        for word in sorted(
            occurrences, key=lambda token: (-len(paper_support[token]), token)
        ):
            keys = sorted(paper_support[word])
            handle.write(
                f"{word}\t{len(keys)}\t{occurrences[word]}\t{','.join(keys)}\n"
            )


def build_corpus(root: Path, manifest: dict, out: Path) -> dict:
    """Extract grouped vocabularies from the approved source papers."""
    occurrences = {group: Counter() for group in GROUPS}
    support: dict[str, dict[str, set[str]]] = {
        group: defaultdict(set) for group in GROUPS
    }
    papers = []

    for entry in manifest["papers"]:
        counts, files, duplicates = extract_paper(root, entry)
        group = entry["group"]
        occurrences[group].update(counts)
        for word in counts:
            support[group][word].add(entry["key"])
            for component in parts(word):
                support[group][component].add(entry["key"])
        papers.append({
            **entry,
            "files": files,
            "duplicate_files_skipped": duplicates,
            "prose_words": sum(counts.values()),
            "word_forms": len(counts),
        })

    out.mkdir(parents=True, exist_ok=True)
    for group in GROUPS:
        write_vocabulary(
            out / f"{group}-unigrams.tsv", occurrences[group], support[group]
        )

    summary = {
        "generated_at": now(),
        "manifest_name": manifest.get("name", "strict vocabulary corpus"),
        "comparison_min_papers": manifest.get("comparison_min_papers", 2),
        "groups": {
            group: {
                "papers": sum(1 for paper in papers if paper["group"] == group),
                "prose_words": sum(
                    paper["prose_words"] for paper in papers
                    if paper["group"] == group
                ),
                "word_forms": len(occurrences[group]),
            }
            for group in GROUPS
        },
        "papers": papers,
    }
    (out / "corpus.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {
        "summary": summary,
        "occurrences": occurrences,
        "support": support,
    }


def location_key(location: str) -> tuple[str, int]:
    path, line = location.rsplit(":", 1)
    return path, int(line)


def scan_manuscript(
    root: Path,
    targets: list[Path],
    corpus: dict,
    comparison_min_papers: int,
    decisions: dict | None = None,
) -> dict:
    """Classify exact manuscript word forms under the strict policy."""
    manuscript: dict[str, list[str]] = defaultdict(list)
    total = 0
    for target in targets:
        relpath = str(target.relative_to(root))
        for word, line in tokens(strip_tex(read(target))):
            manuscript[word].append(f"{relpath}:{line}")
            total += 1

    owner_support = corpus["support"]["owner"]
    comparison_support = corpus["support"]["comparison"]
    strict_words = set(owner_support).union(
        word for word, papers in comparison_support.items()
        if len(papers) >= comparison_min_papers
    )
    decisions = decisions or load_decision_policy(None)
    approved_decisions = decisions["approved"]
    conditional_decisions = decisions["conditional"]
    not_approved_decisions = decisions["not_approved"]
    non_prose_decisions = decisions["non_prose"]

    def in_family(word: str, family: set[str]) -> bool:
        return word in family or derived_from(word, family) is not None

    categories: dict[str, list[dict]] = {
        "owner": [],
        "comparison_repeated": [],
        "decision_approved": [],
        "non_prose": [],
        "conditional": [],
        "comparison_single": [],
        "unattested": [],
    }
    for word, locations in manuscript.items():
        owner_papers = sorted(owner_support.get(word, set()))
        comparison_papers = sorted(comparison_support.get(word, set()))
        if word in non_prose_decisions:
            category = "non_prose"
        elif in_family(word, not_approved_decisions):
            category = "unattested" if not comparison_papers else "comparison_single"
        elif in_family(word, conditional_decisions):
            category = "conditional"
        elif in_family(word, approved_decisions):
            category = "decision_approved"
        elif owner_papers:
            category = "owner"
        elif len(comparison_papers) >= comparison_min_papers:
            category = "comparison_repeated"
        elif comparison_papers:
            category = "comparison_single"
        else:
            category = "unattested"

        relative = derived_from(word, strict_words)
        row = {
            "text": word,
            "count": len(locations),
            "where": sorted(set(locations), key=location_key),
            "kind": "compound" if "-" in word else "derived" if relative else "plain",
            "recognized_relative": relative,
            "owner_papers": owner_papers,
            "comparison_papers": comparison_papers,
            "non_prose_reason": non_prose_decisions.get(word),
        }
        categories[category].append(row)

    for rows in categories.values():
        rows.sort(key=lambda row: (-row["count"], row["text"]))

    violations = (
        categories["conditional"]
        + categories["comparison_single"]
        + categories["unattested"]
    )
    violation_compounds = sorted(
        (row for row in violations if row["kind"] == "compound"),
        key=lambda row: (-row["count"], row["text"]),
    )
    return {
        "generated_at": now(),
        "targets": [str(target.relative_to(root)) for target in targets],
        "prose_words": total,
        "distinct_word_forms": len(manuscript),
        "comparison_min_papers": comparison_min_papers,
        "policy": {
            "owner_word": "accepted when attested in any approved owner paper",
            "comparison_word": (
                "accepted only when attested in at least "
                f"{comparison_min_papers} approved comparison papers"
            ),
            "flag_meaning": "editorial discussion item, not an automatic rewrite",
            "decision_source": decisions["source"],
            "non_prose": (
                "exact proper names, acronyms, and literal machine identifiers "
                "recorded separately from prose vocabulary"
            ),
        },
        "counts": {category: len(rows) for category, rows in categories.items()},
        "occurrences": {
            category: sum(row["count"] for row in rows)
            for category, rows in categories.items()
        },
        "categories": categories,
        "violation_compounds": violation_compounds,
    }


def _locations(row: dict, limit: int = 6) -> str:
    locations = row["where"]
    shown = ", ".join(f"`{location}`" for location in locations[:limit])
    if len(locations) > limit:
        shown += f"; +{len(locations) - limit} more"
    return shown


def _word_table(rows: list[dict], single_support: bool = False) -> list[str]:
    if single_support:
        lines = ["| Word | Uses | Comparison paper | Kind | Locations |",
                 "|---|---:|---|---|---|"]
    else:
        lines = ["| Word | Uses | Kind | Recognized relative | Locations |",
                 "|---|---:|---|---|---|"]
    for row in rows:
        word = row["text"].replace("|", "\\|")
        if single_support:
            support = ", ".join(row["comparison_papers"])
            lines.append(
                f"| `{word}` | {row['count']} | `{support}` | {row['kind']} | "
                f"{_locations(row)} |"
            )
        else:
            relative = row["recognized_relative"] or "—"
            lines.append(
                f"| `{word}` | {row['count']} | {row['kind']} | `{relative}` | "
                f"{_locations(row)} |"
            )
    return lines


def _non_prose_table(rows: list[dict]) -> list[str]:
    lines = [
        "| Exact form | Uses | Reason | Locations |",
        "|---|---:|---|---|",
    ]
    for row in rows:
        word = row["text"].replace("|", "\\|")
        lines.append(
            f"| `{word}` | {row['count']} | {row['non_prose_reason']} | "
            f"{_locations(row)} |"
        )
    return lines


def render_markdown(report: dict, corpus: dict) -> str:
    """Render the complete discussion list and its approved provenance."""
    lines = [
        "# Strict vocabulary discussion report",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "This is an editorial discussion instrument, not a pass/fail test. A",
        "flag does not show that a word is wrong, and it does not authorize an",
        "automatic replacement. Mathematical terminology must be adjudicated in",
        "context.",
        "",
        "## Policy",
        "",
        "- A word is accepted when it occurs in any approved owner paper.",
        f"- Otherwise, it is accepted only when at least {report['comparison_min_papers']} "
        "approved comparison papers use the exact form.",
        "- A word used by only one comparison paper remains a discussion item.",
        "- Recorded proper names, acronyms, and literal machine identifiers are",
        "  reported separately and do not enlarge the prose vocabulary.",
        "- Hyphenated forms are checked as exact forms and are also collected",
        "  separately below.",
        "",
        "## Approved corpus",
        "",
        "| Role | Exact source | Authors |",
        "|---|---|---|",
    ]
    for paper in corpus["papers"]:
        authors = "; ".join(paper["authors"])
        lines.append(
            f"| {paper['group']} | *{paper['title']}* (`{paper['key']}`) | "
            f"{authors} |"
        )

    counts = report["counts"]
    occurrences = report["occurrences"]
    lines.extend([
        "",
        "## Summary",
        "",
        f"The manuscript contains {report['prose_words']:,} prose-word uses and "
        f"{report['distinct_word_forms']:,} distinct exact forms.",
        "",
        "| Class | Distinct forms | Uses |",
        "|---|---:|---:|",
        f"| Established owner vocabulary | {counts['owner']} | {occurrences['owner']} |",
        f"| At least {report['comparison_min_papers']} comparison papers | "
        f"{counts['comparison_repeated']} | {occurrences['comparison_repeated']} |",
        f"| Explicitly approved by owner | {counts['decision_approved']} | "
        f"{occurrences['decision_approved']} |",
        f"| Recorded non-prose exact forms | {counts['non_prose']} | "
        f"{occurrences['non_prose']} |",
        f"| Conditionally allowed; contextual review remains | "
        f"{counts['conditional']} | {occurrences['conditional']} |",
        f"| Only one comparison paper | {counts['comparison_single']} | "
        f"{occurrences['comparison_single']} |",
        f"| Absent from the approved corpus | {counts['unattested']} | "
        f"{occurrences['unattested']} |",
        "",
        "## A. Absent from the approved corpus",
        "",
    ])
    lines.extend(_word_table(report["categories"]["unattested"]))
    lines.extend([
        "",
        "## B. Conditionally allowed; contextual review remains",
        "",
    ])
    lines.extend(_word_table(report["categories"]["conditional"]))
    lines.extend([
        "",
        "## C. Used in only one comparison paper",
        "",
    ])
    lines.extend(_word_table(
        report["categories"]["comparison_single"], single_support=True
    ))
    lines.extend([
        "",
        "## D. Hyphenated forms among the discussion items",
        "",
    ])
    lines.extend(_word_table(report["violation_compounds"]))
    lines.extend([
        "",
        "## E. Recorded non-prose exact forms",
        "",
    ])
    lines.extend(_non_prose_table(report["categories"]["non_prose"]))
    lines.extend([
        "",
        "The JSON report preserves the full accepted categories as well as every",
        "location and paper-support set.",
        "",
    ])
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--target", type=Path, nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--decisions", type=Path)
    parser.add_argument("--root", type=Path, default=REPO)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.root.resolve()
    manifest_path = (root / args.manifest).resolve() if not args.manifest.is_absolute() else args.manifest
    out = (root / args.out).resolve() if not args.out.is_absolute() else args.out
    targets = [
        (root / target).resolve() if not target.is_absolute() else target.resolve()
        for target in args.target
    ]
    manifest = load_manifest(manifest_path)
    decisions_path = None
    if args.decisions is not None:
        decisions_path = (
            (root / args.decisions).resolve()
            if not args.decisions.is_absolute()
            else args.decisions.resolve()
        )
    decisions = load_decision_policy(decisions_path)
    corpus = build_corpus(root, manifest, out)
    report = scan_manuscript(
        root,
        targets,
        corpus,
        comparison_min_papers=manifest.get("comparison_min_papers", 2),
        decisions=decisions,
    )
    (out / "strict-vocabulary-report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (out / "strict-vocabulary-report.md").write_text(
        render_markdown(report, corpus["summary"]), encoding="utf-8"
    )
    print(json.dumps({
        "corpus": corpus["summary"]["groups"],
        "report_counts": report["counts"],
        "report_occurrences": report["occurrences"],
        "out": str(out.relative_to(root)),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
