"""Search the local reference workspace by bibliographic identity.

`references/CATALOG.json` carries title, authors, year, identifiers, keywords,
and abstract for every local item, plus records for externally held sources
that are only present as derivatives. This tool queries that catalog so an
agent can find a source by what it is rather than by remembering an arXiv
identifier or a directory slug.

    tools/reference_lookup.py resolution             # any field
    tools/reference_lookup.py --author noether
    tools/reference_lookup.py --title "exact structures" --year 2015-2022
    tools/reference_lookup.py --keyword cohomology --json
    tools/reference_lookup.py --grep "finitely generated"   # inside local text

Matching ignores case, accents, and dash style, so "riemann-roch" matches a
title typeset as "Riemann--Roch" and "erdos" matches "Erdős".
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

GREP_LIMIT = 200
SNIPPET = 100


def fold(value: str) -> str:
    """Normalize for matching: casefold, strip accents, unify dashes."""
    decomposed = unicodedata.normalize("NFKD", value)
    stripped = "".join(character for character in decomposed if not unicodedata.combining(character))
    stripped = re.sub(r"[‐-―]", "-", stripped)
    stripped = re.sub(r"-{2,}", "-", stripped)
    return re.sub(r"\s+", " ", stripped).casefold()


def load_catalog(root: Path) -> list[dict[str, object]]:
    catalog_path = root / "CATALOG.json"
    if not catalog_path.is_file():
        raise SystemExit(f"no catalog at {catalog_path}; run tools/reference_metadata.py first")
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    records = list(catalog.get("items", []))
    records.extend(catalog.get("external_sources", []))
    return [record for record in records if isinstance(record, dict)]


def identity(record: dict[str, object]) -> dict[str, object]:
    value = record.get("bibliographic_identity")
    return value if isinstance(value, dict) else {}


def parse_years(value: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d{4})(?:\s*-\s*(\d{4}))?", value.strip())
    if not match:
        raise SystemExit(f"invalid year filter: {value!r} (use 2019 or 2015-2022)")
    start = int(match.group(1))
    return start, int(match.group(2) or start)


def matches(record: dict[str, object], args: argparse.Namespace) -> bool:
    bibliography = identity(record)
    if args.kind and record.get("kind") not in args.kind:
        return False

    if args.author:
        names = bibliography.get("authors") or []
        # Items with no recorded by-line usually still carry surnames in the key.
        authors = fold(" ".join(str(name) for name in names)) if names else fold(str(record.get("key") or ""))
        if not all(fold(term) in authors for term in args.author):
            return False
    if args.title:
        title = fold(str(bibliography.get("title") or ""))
        if not all(fold(term) in title for term in args.title):
            return False
    if args.keyword:
        pool = fold(
            " ".join(str(item) for item in (bibliography.get("keywords") or []))
            + " "
            + " ".join(str(item) for item in (bibliography.get("msc") or []))
        )
        if not all(fold(term) in pool for term in args.keyword):
            return False
    if args.doi:
        if fold(args.doi) not in fold(str(bibliography.get("doi") or "")):
            return False
    if args.year:
        low, high = args.year
        year = bibliography.get("year")
        if not isinstance(year, int) or not low <= year <= high:
            return False
    if args.cited and not record.get("citation_count"):
        return False
    if args.has_derivative and not record.get("derivatives"):
        return False
    if args.has_source and not record.get("source_file_count"):
        return False

    if args.terms:
        blob = fold(str(record.get("search_text") or "")) or fold(json.dumps(bibliography, ensure_ascii=False))
        blob = f"{blob} {fold(str(record.get('id') or ''))}"
        if not all(fold(term) in blob for term in args.terms):
            return False
    return True


def sort_key(record: dict[str, object]) -> tuple[object, ...]:
    bibliography = identity(record)
    authors = bibliography.get("authors") or []
    first = fold(str(authors[0])) if authors else "~"
    surname = first.split(" ")[-1] if first else "~"
    return (surname, -(bibliography.get("year") or 0), str(record.get("id")))


def format_record(record: dict[str, object], *, verbose: bool) -> str:
    bibliography = identity(record)
    authors = [str(name) for name in bibliography.get("authors") or []]
    shown = ", ".join(authors[:4]) + (" et al." if len(authors) > 4 else "")
    year = bibliography.get("year")
    title = bibliography.get("title") or "(untitled)"
    lines = [f"{shown or '(unattributed)'}{f' ({year})' if year else ''}. {title}"]

    tags = []
    if bibliography.get("arxiv_id"):
        tags.append(f"arXiv:{bibliography['arxiv_id']}")
    if bibliography.get("doi"):
        tags.append(f"doi:{bibliography['doi']}")
    if bibliography.get("venue"):
        tags.append(str(bibliography["venue"]))
    if record.get("citation_count"):
        tags.append(f"cited in {record['citation_count']} repo file(s)")
    if tags:
        lines.append("    " + " | ".join(tags))

    location = record.get("path") or record.get("original_path") or record.get("record_path") or ""
    lines.append(f"    {record.get('id')}  {location}")

    if verbose:
        if record.get("derivatives"):
            lines.append(f"    derivatives: {', '.join(str(item) for item in record['derivatives'][:4])}")
        if record.get("citations"):
            lines.append(f"    cited by: {', '.join(str(item) for item in record['citations'][:4])}")
        keywords = bibliography.get("keywords") or []
        if keywords:
            lines.append(f"    keywords: {', '.join(str(item) for item in keywords[:8])}")
        abstract = str(bibliography.get("abstract") or "")
        if abstract:
            lines.append(f"    {abstract[:300]}{'...' if len(abstract) > 300 else ''}")
        provenance = record.get("metadata_provenance")
        if isinstance(provenance, dict):
            lines.append(f"    provenance: title={provenance.get('title', '-')} authors={provenance.get('authors', '-')}")
    return "\n".join(lines)


def grep_workspace(root: Path, pattern: str, *, limit: int) -> list[dict[str, object]]:
    """Search extracted text and unpacked TeX for a phrase, with file locators."""
    expression = re.compile(pattern, re.IGNORECASE)
    hits: list[dict[str, object]] = []
    searchable: list[Path] = sorted((root / "derived" / "text").glob("*.txt"))
    for plural in ("arxiv", "papers", "books"):
        base = root / "items" / plural
        if base.is_dir():
            searchable.extend(sorted(base.glob("*/source/**/*.tex")))

    for path in searchable:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if not expression.search(text):
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            if expression.search(line):
                hits.append(
                    {
                        "path": path.as_posix(),
                        "line": number,
                        "text": line.strip()[:SNIPPET],
                    }
                )
                if len(hits) >= limit:
                    return hits
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Search local reference items by author, title, year, keyword, or free text.",
    )
    parser.add_argument("terms", nargs="*", help="free-text terms matched against all recorded metadata")
    parser.add_argument("--root", type=Path, default=Path("references"))
    parser.add_argument("--author", action="append", help="substring of an author name (repeatable)")
    parser.add_argument("--title", action="append", help="substring of the title (repeatable)")
    parser.add_argument("--keyword", action="append", help="keyword or MSC code (repeatable)")
    parser.add_argument("--doi", help="substring of the DOI")
    parser.add_argument("--year", type=parse_years, help="year or inclusive range, e.g. 2015-2022")
    parser.add_argument(
        "--kind",
        action="append",
        choices=["arxiv", "paper", "book", "external"],
        help="restrict to a kind (repeatable)",
    )
    parser.add_argument("--cited", action="store_true", help="only sources cited somewhere in the repository")
    parser.add_argument("--has-derivative", action="store_true", help="only sources with extracted text or OCR")
    parser.add_argument("--has-source", action="store_true", help="only items with an unpacked source tree")
    parser.add_argument("--grep", metavar="PATTERN", help="search extracted text and TeX instead of metadata")
    parser.add_argument("--limit", type=int, default=25, help="maximum results (0 for all)")
    parser.add_argument("--verbose", "-v", action="store_true", help="show abstract, keywords, and provenance")
    parser.add_argument("--paths", action="store_true", help="print item paths only")
    parser.add_argument("--json", action="store_true", help="print full matching records as JSON")
    args = parser.parse_args()

    if args.grep:
        hits = grep_workspace(args.root, args.grep, limit=args.limit or GREP_LIMIT)
        if args.json:
            print(json.dumps(hits, indent=2, ensure_ascii=False))
        else:
            for hit in hits:
                print(f"{hit['path']}:{hit['line']}: {hit['text']}")
            print(f"\n{len(hits)} line(s)", file=sys.stderr)
        return 0

    records = [record for record in load_catalog(args.root) if matches(record, args)]
    records.sort(key=sort_key)
    if args.limit:
        shown = records[: args.limit]
    else:
        shown = records

    if args.json:
        print(json.dumps(shown, indent=2, ensure_ascii=False))
        return 0
    if args.paths:
        for record in shown:
            print(record.get("path") or record.get("original_path") or record.get("record_path") or record.get("id"))
        return 0

    for record in shown:
        print(format_record(record, verbose=args.verbose))
        print()
    suffix = f" (showing {len(shown)})" if len(shown) != len(records) else ""
    print(f"{len(records)} match(es){suffix}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
