"""Corpus lexicon for manuscript wording checks.

Builds a comparison lexicon from mathematical TeX source items, then
flags words in a manuscript that the corpus never attests.  The point is
mechanical: an unattested word is a candidate for odd wording, not a verdict.
Mathematics is never inspected; only prose outside math mode is read.

    uv run python tools/lexicon.py build
    uv run python tools/lexicon.py check <manuscript>/*.tex --markdown <report>.md

See `paper/vocab/README.md` for the corpus definition and output formats.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Prose is what survives after these are deleted.  A deleted span is replaced by
# its own newlines, so line numbers stay exact, plus a break marker.
BREAK = "\x00"

DROP_ENVS = [
    "equation", "align", "alignat", "gather", "multline", "eqnarray",
    "displaymath", "math", "array", "cases", "split", "aligned", "gathered",
    "matrix", "pmatrix", "bmatrix", "vmatrix", "Vmatrix", "smallmatrix",
    "tikzpicture", "tikzcd", "xy", "xymatrix", "picture", "diagram", "CD",
    "verbatim", "lstlisting", "comment", "thebibliography", "tabular",
    "tabularx", "longtable", "figure", "wrapfigure", "pspicture",
]

# Commands whose single brace group carries no prose.
DROP_ARG = [
    "label", "ref", "eqref", "cref", "Cref", "autoref", "pageref", "vref",
    "cite", "citep", "citet", "citeauthor", "citeyear", "nocite", "fullcite",
    "input", "include", "includegraphics", "url", "href", "bibliography",
    "bibliographystyle", "documentclass", "usepackage", "RequirePackage",
    "newcommand", "renewcommand", "providecommand", "DeclareMathOperator",
    "newtheorem", "theoremstyle", "setlength", "addtolength", "setcounter",
    "vspace", "hspace", "index", "textcolor", "color", "definecolor",
    "subjclass", "keywords", "address", "email", "thanks", "date", "def",
    "hyphenation", "pagestyle", "numberwithin", "bibitem", "verb",
]

WORD = re.compile(r"[^\W\d_]+(?:[-'\u2019][^\W\d_]+)*", re.UNICODE)

# TeX spells some letters and accents as commands inside otherwise ordinary
# words, especially personal names such as Y{\i}ld{\i}r{\i}m and Smal\o.
# Normalize these before removing markup; otherwise the checker reports
# meaningless fragments such as ld and smal as prose words.
TEX_LETTERS = {
    "i": "i", "j": "j", "o": "o", "O": "O", "l": "l", "L": "L",
    "aa": "a", "AA": "A", "ae": "ae", "AE": "AE", "oe": "oe",
    "OE": "OE", "ss": "ss",
}
TEX_PUNCT_ACCENTS = r"[\x60'\"^~=.]"
TEX_LETTER_ACCENTS = r"[uvHckbdtr]"

# A file must look like English prose to enter the corpus (guards against
# French sources and macro-only files).
ENGLISH_MARKERS = {"the", "of", "and", "is", "we", "that", "for", "this", "in"}
ENGLISH_MIN_SHARE = 0.04
MIN_FILE_WORDS = 200

# Attestation in this many papers counts as ordinary mathematical English.
COMMON_DF = 25


def _blank(match: re.Match) -> str:
    """Replace a span with its own newlines, preserving line numbers."""
    return BREAK + "\n" * match.group(0).count("\n") + BREAK


def strip_tex(text: str) -> str:
    """Return prose with math, markup, and bibliography removed."""
    text = re.sub(r"(?<!\\)%.*", lambda m: BREAK, text)

    if "\\begin{document}" in text:
        head, _, text = text.partition("\\begin{document}")
        text = "\n" * head.count("\n") + text
    else:
        # Two corpus sources use plain/AMS-TeX rather than a document
        # environment.  Their first title/topmatter command separates a long
        # macro preamble from the article text.
        marker = re.search(
            r"(?m)^\s*\\(?:topmatter\b|centerline\s*\{\\bf\b|title\b)", text,
        )
        if marker:
            text = "\n" * text[:marker.start()].count("\n") + text[marker.start():]
    text = text.split("\\end{document}")[0]
    text = re.sub(r"\\Refs\b.*?\\endRefs\b", _blank, text, flags=re.DOTALL)

    for env in DROP_ENVS:
        pattern = re.escape(env) + r"\*?"
        text = re.sub(
            r"\\begin\s*\{" + pattern + r"\}.*?\\end\s*\{" + pattern + r"\}",
            _blank, text, flags=re.DOTALL,
        )

    text = re.sub(r"\$\$.*?\$\$", _blank, text, flags=re.DOTALL)
    text = re.sub(r"\\\[.*?\\\]", _blank, text, flags=re.DOTALL)
    text = re.sub(r"\\\(.*?\\\)", _blank, text, flags=re.DOTALL)
    text = re.sub(r"(?<!\\)\$[^$]*?(?<!\\)\$", _blank, text, flags=re.DOTALL)

    drop_arg = "|".join(sorted(DROP_ARG, key=len, reverse=True))
    text = re.sub(
        r"\\(?:" + drop_arg + r")\b\*?(?:\[[^\]]*\])?(?:\{[^{}]*\})?",
        _blank, text,
    )
    letter_names = "|".join(sorted(TEX_LETTERS, key=len, reverse=True))
    text = re.sub(
        r"\{\\(" + letter_names + r")\b(?:\{\})?\}",
        lambda m: TEX_LETTERS[m.group(1)], text,
    )
    text = re.sub(
        r"\\(" + letter_names + r")\b(?:\{\})?",
        lambda m: TEX_LETTERS[m.group(1)], text,
    )
    # Braced and unbraced TeX accents contribute their underlying letter to
    # the vocabulary; the diacritic itself is irrelevant to word attestation.
    text = re.sub(
        r"\{?\\(?:" + TEX_PUNCT_ACCENTS + "|" + TEX_LETTER_ACCENTS
        + r")\s*\{([A-Za-z])\}\}?", r"\1", text,
    )
    text = re.sub(
        r"\{?\\" + TEX_PUNCT_ACCENTS + r"\s*([A-Za-z])\}?", r"\1", text,
    )
    # Alphabetic accent commands need either a braced argument (handled
    # above) or intervening whitespace.  Without this restriction, \text and
    # other ordinary commands would be mistaken for accents.
    text = re.sub(
        r"\{?\\" + TEX_LETTER_ACCENTS + r"\s+([A-Za-z])\}?", r"\1", text,
    )
    # \begin{theorem}[Riemann-Roch] — environment and its optional title.
    text = re.sub(
        r"\\(?:begin|end)\s*\{[^{}]*\}(?:\[[^\]]*\])?", _blank, text,
    )
    text = re.sub(r"\\[A-Za-z@]+\*?", " ", text)
    text = re.sub(r"\\.", " ", text, flags=re.DOTALL)
    text = re.sub(
        r"(?<![A-Za-z])(?:\d+(?:\.\d*)?|\.\d+)\s*(?:true)?"
        r"(?:pt|pc|in|bp|cm|mm|dd|cc|sp|ex|em)\b",
        " ", text,
    )
    text = re.sub(r"[{}\[\]&~^_]", " ", text)
    return text


UNICODE_LETTERS = str.maketrans({
    "ı": "i", "İ": "I", "ø": "o", "Ø": "O", "ł": "l", "Ł": "L",
    "đ": "d", "Đ": "D", "ð": "d", "Ð": "D", "þ": "th", "Þ": "Th",
    "æ": "ae", "Æ": "AE", "œ": "oe", "Œ": "OE", "ß": "ss",
})


def fold_unicode(text: str) -> str:
    """Put Unicode and TeX spellings of Latin prose words in one form."""
    text = text.translate(UNICODE_LETTERS)
    return "".join(
        char for char in unicodedata.normalize("NFKD", text)
        if unicodedata.category(char) != "Mn"
    )


def tokens(text: str) -> list[tuple[str, int]]:
    """Return (lowercased word, line number) for each prose word."""
    text = fold_unicode(text)
    out = []
    line = 1
    pos = 0
    for match in WORD.finditer(text):
        line += text.count("\n", pos, match.start())
        pos = match.start()
        out.append((match.group(0).lower().replace("\u2019", "'"), line))
    return out


def parts(word: str) -> list[str]:
    """Split a hyphenated compound into its components."""
    return [p for p in word.split("-") if p]


PREFIXES = [
    "non", "co", "un", "re", "semi", "quasi", "pre", "post", "sub", "super",
    "anti", "bi", "equi", "multi", "over", "under", "counter", "inter", "self",
]
SUFFIXES = [
    "s", "es", "ed", "d", "ing", "ly", "ness", "ity", "ties", "ation", "ions",
    "ion", "al", "ally", "ic", "ical", "ist", "ive", "able", "ible", "er",
    "ers", "est", "less", "ful", "ism", "ize", "izes", "ized",
]


def derived_from(word: str, known: set[str]) -> str | None:
    """Return an attested word this one is plainly built from, if any."""
    for prefix in PREFIXES:
        if word.startswith(prefix) and len(word) > len(prefix) + 2:
            stem = word[len(prefix):].lstrip("-")
            if stem in known:
                return stem
            for suffix in SUFFIXES:
                if stem.endswith(suffix) and stem[: -len(suffix)] in known:
                    return stem[: -len(suffix)]
    for suffix in SUFFIXES:
        if word.endswith(suffix) and len(word) > len(suffix) + 2:
            stem = word[: -len(suffix)]
            for candidate in (stem, stem + "e", stem[:-1] if stem[-1:] == "i" else "",
                              stem + "y" if stem[-1:] == "i" else ""):
                if candidate and candidate in known:
                    return candidate
    return None


def is_english(counts: Counter) -> bool:
    total = sum(counts.values())
    if total < MIN_FILE_WORDS:
        return False
    marked = sum(counts[w] for w in ENGLISH_MARKERS)
    return marked / total >= ENGLISH_MIN_SHARE


# --- corpus ------------------------------------------------------------------

# The author tier is read from the reference catalog rather than a hardcoded
# item list, so filing another of the author's papers reclassifies it on the
# next build.  Match on surname: the catalog records full author names, and
# spelling of given names varies between sources.  Set the surname for this
# project below or through RESEARCH_HARNESS_AUTHOR_SURNAME.  Leaving it empty
# disables the author tier and the report section that depends on it.
OWNER_SURNAME = os.environ.get("RESEARCH_HARNESS_AUTHOR_SURNAME", "")


def owner_items(root: Path) -> set[str]:
    """Item directory names whose catalog authors include the author."""
    if not OWNER_SURNAME:
        return set()
    catalog = root / "references" / "CATALOG.json"
    if not catalog.is_file():
        return set()
    try:
        data = json.loads(catalog.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return set()
    owned = set()
    for item in data.get("items", []):
        identity = item.get("bibliographic_identity") or {}
        authors = identity.get("authors") or []
        if any(OWNER_SURNAME in str(a) for a in authors):
            path = item.get("path") or item.get("item_path") or ""
            name = Path(path).name
            if name:
                owned.add(name)
    return owned


def corpus_items(root: Path) -> list[tuple[str, str, list[Path]]]:
    """Return (item_key, tier, tex_files) for each corpus paper."""
    items = []
    owned = owner_items(root)

    for kind in ("arxiv", "papers"):
        base = root / "references" / "items" / kind
        for item in sorted(base.iterdir()) if base.is_dir() else []:
            if not item.is_dir():
                continue
            tex = sorted(p for p in item.rglob("*.tex") if p.is_file())
            if not tex:
                continue
            tier = "owner" if item.name in owned else "field"
            items.append((item.name, tier, tex))
    return items


def read(path: Path) -> str:
    for encoding in ("utf-8", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return ""


def build(root: Path, out: Path) -> dict:
    unigram_df: Counter = Counter()
    unigram_n: Counter = Counter()
    owner_df: Counter = Counter()
    manifest = []
    duplicate_items = []
    duplicate_files = []
    seen_documents: dict[tuple[tuple[str, int], ...], str] = {}

    for key, tier, tex_files in corpus_items(root):
        item_words: Counter = Counter()
        used = []
        seen_file_tokens: dict[tuple[str, ...], str] = {}
        for path in tex_files:
            prose = strip_tex(read(path))
            file_tokens = tuple(w for w, _ in tokens(prose))
            counts = Counter(file_tokens)
            if not is_english(counts):
                continue
            relpath = str(path.relative_to(root))
            if file_tokens in seen_file_tokens:
                duplicate_files.append({
                    "item": key,
                    "file": relpath,
                    "duplicate_of": seen_file_tokens[file_tokens],
                })
                continue
            seen_file_tokens[file_tokens] = relpath
            item_words.update(counts)
            used.append(relpath)
        if not item_words:
            continue

        # The reference workspace may contain both an arXiv extraction and a
        # named-paper extraction of the same TeX source.  Document frequency
        # must count the mathematical paper, not its local copies.
        signature = tuple(sorted(item_words.items()))
        if signature in seen_documents:
            duplicate_items.append({
                "item": key,
                "duplicate_of": seen_documents[signature],
                "files": used,
            })
            continue
        seen_documents[signature] = key

        seen = set()
        for word, count in item_words.items():
            unigram_n[word] += count
            for token in {word, *parts(word)}:
                seen.add(token)
        for token in seen:
            unigram_df[token] += 1
            if tier == "owner":
                owner_df[token] += 1
        manifest.append({
            "item": key, "tier": tier, "files": used,
            "words": sum(item_words.values()), "types": len(item_words),
        })

    out.mkdir(parents=True, exist_ok=True)
    with (out / "unigrams.tsv").open("w", encoding="utf-8") as handle:
        handle.write("word\tpapers\toccurrences\towner_papers\n")
        for word, df in sorted(unigram_df.items(), key=lambda kv: (-kv[1], kv[0])):
            handle.write(f"{word}\t{df}\t{unigram_n.get(word, 0)}\t{owner_df.get(word, 0)}\n")

    summary = {
        "generated_at": now(),
        "papers": len(manifest),
        "owner_papers": sum(1 for m in manifest if m["tier"] == "owner"),
        "prose_words": sum(m["words"] for m in manifest),
        "word_forms": len(unigram_n),
        "lexicon_entries": len(unigram_df),
        "common_word_threshold_papers": COMMON_DF,
        "common_words": sum(1 for df in unigram_df.values() if df >= COMMON_DF),
        "duplicates": duplicate_items,
        "duplicate_files": duplicate_files,
        "items": manifest,
    }
    (out / "corpus.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def now() -> str:
    return subprocess.run(
        ["date", "+%Y-%m-%dT%H:%M:%S%z"], capture_output=True, text=True, check=True,
    ).stdout.strip()


# --- check -------------------------------------------------------------------


def load_lexicon(out: Path) -> dict[str, tuple[int, int]]:
    unigrams = {}
    for line in (out / "unigrams.tsv").read_text(encoding="utf-8").splitlines()[1:]:
        word, df, _, owner = line.split("\t")
        unigrams[word] = (int(df), int(owner))
    return unigrams


def check(root: Path, out: Path, targets: list[Path], rare_max: int) -> dict:
    unigrams = load_lexicon(out)

    unknown: dict[str, list] = defaultdict(list)
    rare: dict[str, list] = defaultdict(list)
    owner_absent: dict[str, list] = defaultdict(list)
    total = 0

    for target in targets:
        # Locators are repository-relative when possible; a manuscript kept
        # outside the repository keeps its absolute path rather than failing.
        rel = str(target)
        if target.is_absolute():
            try:
                rel = str(target.relative_to(root))
            except ValueError:
                pass
        prose = strip_tex(read(target))
        for word, line in tokens(prose):
            total += 1
            entry = unigrams.get(word)
            if entry is None:
                unknown[word].append(f"{rel}:{line}")
            else:
                df, owner = entry
                if df <= rare_max:
                    rare[word].append(f"{rel}:{line}")
                if OWNER_SURNAME and owner == 0:
                    owner_absent[word].append(f"{rel}:{line}")

    known = set(unigrams)

    def location_key(location: str) -> tuple[str, int]:
        path, line = location.rsplit(":", 1)
        return path, int(line)

    def pack(bucket: dict[str, list], classify: bool = False) -> list[dict]:
        rows = []
        for key, where in sorted(bucket.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            row = {
                "text": key,
                "count": len(where),
                "where": sorted(set(where), key=location_key),
            }
            if classify:
                stem = derived_from(key, known)
                if "-" in key:
                    row["kind"] = "compound"
                    row["stem"] = ", ".join(
                        p for p in parts(key) if p in known) or "none"
                elif stem:
                    row["kind"] = "derived"
                    row["stem"] = stem
                else:
                    row["kind"] = "plain"
            rows.append(row)
        return rows

    return {
        "generated_at": now(),
        "targets": [str(t) for t in targets],
        "prose_words": total,
        "rare_max": rare_max,
        "unattested_words": pack(unknown, classify=True),
        "rare_words": pack(rare),
        "owner_absent_words": pack(owner_absent),
    }


SECTIONS = [
    ("plain", "Unattested, with no relative recognized by the heuristic",
     "No source item in the corpus attests this exact form, and the simple "
     "prefix/suffix heuristic found no attested relative. This is a prompt for "
     "inspection, not evidence that the wording is wrong."),
    ("compound", "Hyphenated compound unattested in the corpus",
     "No source item attests this exact compound. The stem column lists any "
     "separately attested parts. Inspect whether the spelling and definition "
     "are clear; corpus absence alone does not determine the wording."),
    ("derived", "Unattested, but formed from an attested word",
     "The heuristic found the attested stem shown below; only this inflection "
     "or prefixed form is absent. Inspect any form that names a construction."),
]


def render_markdown(result: dict, corpus: dict) -> str:
    def table(rows: list[dict], columns: tuple[str, ...]) -> list[str]:
        out = ["| " + " | ".join(columns) + " |",
               "|" + "|".join(["---"] * len(columns)) + "|"]
        for row in rows:
            cells = [f"`{row['text']}`", str(row["count"])]
            if "stem" in columns:
                cells.append(f"`{row.get('stem', '')}`")
            cells.append(" ".join(f"`{w}`" for w in row["where"][:3]))
            out.append("| " + " | ".join(cells) + " |")
        return out + [""]

    manuscript = Path(result["targets"][0]).parent.name or "manuscript"
    lines = [
        f"# Vocabulary check: {manuscript}",
        "",
        f"Generated {result['generated_at']} by `tools/lexicon.py`.",
        "",
        "Every prose word of the manuscript was compared against a lexicon built",
        f"from {corpus['papers']} TeX source items filed under `references/items/`.",
        "The corpus contains",
        f"{corpus['owner_papers']} items by the author, {corpus['prose_words']:,} words of prose,",
        f"and {corpus['word_forms']:,} distinct surface word forms. The checker removes",
        "recognized math, citation, label, figure, table, and bibliography markup",
        "on both sides. It is a lexical audit, not a full TeX parser. An entry",
        "records non-attestation, low document frequency, or absence from the",
        "author's sources; it is a prompt for inspection, not a verdict.",
        "",
        "## Summary",
        "",
        f"- manuscript prose words: {result['prose_words']:,}",
        f"- distinct unattested word forms: {len(result['unattested_words'])}",
        f"- distinct forms attested in at most {result['rare_max']} source items: "
        f"{len(result['rare_words'])}",
        f"- distinct corpus-attested forms absent from the author's sources: "
        f"{len(result['owner_absent_words'])}",
        "",
    ]

    for kind, title, note in SECTIONS:
        rows = [r for r in result["unattested_words"] if r["kind"] == kind]
        lines += [f"## {title} ({len(rows)})", "", note, ""]
        if rows:
            columns = ("word", "manuscript uses", "stem", "where") \
                if kind in ("derived", "compound") \
                else ("word", "manuscript uses", "where")
            lines += table(rows, columns)

    rare = result["rare_words"]
    lines += [
        f"## Attested in at most {result['rare_max']} source items ({len(rare)})",
        "",
        "These forms are rare in this finite corpus. They may be standard,",
        "specialized, proper names, or ordinary words; inspect their use and",
        "first definition in the manuscript.", "",
    ]
    lines += table(rare, ("word", "manuscript uses", "where"))

    off = result["owner_absent_words"]
    lines += [
              f"## Corpus-attested, but absent from the author's sources ({len(off)})",
              "", "This section is informational and overlaps the rare-form section.",
              "Every corpus-attested manuscript form with owner document frequency",
              "zero is listed here; the JSON report retains all locations.", "",
              ", ".join(f"`{r['text']}`" for r in off), ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="build the lexicon from the reference corpus")
    b.add_argument("--root", type=Path, default=REPO)
    b.add_argument("--out", type=Path, default=REPO / "paper" / "vocab")

    c = sub.add_parser("check", help="flag manuscript wording against the lexicon")
    c.add_argument("targets", type=Path, nargs="+")
    c.add_argument("--root", type=Path, default=REPO)
    c.add_argument("--out", type=Path, default=REPO / "paper" / "vocab")
    c.add_argument("--rare-max", type=int, default=2,
                   help="attested in at most this many source items counts as rare")
    c.add_argument("--json", type=Path, help="write the full result here")
    c.add_argument("--markdown", type=Path, help="write a readable report here")

    args = parser.parse_args()
    if args.command == "build":
        summary = build(args.root, args.out)
        print(json.dumps({k: v for k, v in summary.items() if k != "items"}, indent=2))
        return 0

    result = check(args.root, args.out, args.targets, args.rare_max)
    if args.json:
        args.json.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if args.markdown:
        corpus = json.loads((args.out / "corpus.json").read_text(encoding="utf-8"))
        args.markdown.write_text(render_markdown(result, corpus), encoding="utf-8")
    print(json.dumps({
        "prose_words": result["prose_words"],
        "unattested_words": len(result["unattested_words"]),
        "rare_words": len(result["rare_words"]),
        "owner_absent_words": len(result["owner_absent_words"]),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
