"""Corpus lexicon for manuscript wording checks.

Builds a comparison lexicon from mathematical TeX source items, then flags
words with narrow corpus support and compares hyphenated manuscript forms with
their open and solid spellings.  Evidence breadth is measured by conservative
author signatures as well as distinct papers, so neither one prolific author
nor one large collaboration decides the result.  The point is mechanical: a
flag is a candidate for inspection, not a verdict or a request to respell the
token.  Mathematics is never inspected; only prose outside math mode is read.

    uv run python tools/lexicon.py build
    uv run python tools/lexicon.py check <manuscript>/*.tex --markdown <report>.md

See `paper/vocab/README.md` for the corpus definition and output formats.
"""

from __future__ import annotations

import argparse
import json
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
    "verbatim", "Verbatim", "BVerbatim", "LVerbatim", "SaveVerbatim",
    "lstlisting", "minted", "comment", "thebibliography", "tabular",
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
    "hyphenation", "pagestyle", "numberwithin", "bibitem", "verb", "path",
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

# These thresholds describe broad corpus attestation; they do not certify that
# a word is correct or usual mathematical language.
COMMON_MIN_PAPERS = 25
COMMON_MIN_AUTHORS = 25

DEFAULT_RARE_MAX_PAPERS = 2
DEFAULT_RARE_MAX_AUTHORS = 2
DEFAULT_COMPOUND_MIN_PAPERS = 3
DEFAULT_COMPOUND_MIN_AUTHORS = 5
DEFAULT_COMPOUND_DOMINANCE_RATIO = 4.0


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

    # Pandoc and similar converters place list-label definitions inside the
    # document body.  They are TeX implementation, not article prose.
    text = re.sub(
        r"(?m)^\s*\\def\\[A-Za-z@]+[^\n]*$", _blank, text,
    )

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


def word_sequences(text: str) -> list[tuple[str, ...]]:
    """Return prose-word runs separated by markup or punctuation.

    Open-compound counts may cross whitespace and removed TeX commands, but
    not deleted math/citations or punctuation.  This prevents, for example,
    the end of one sentence and the start of the next from becoming a phrase.
    """
    text = fold_unicode(text)
    sequences = []
    for block in text.split(BREAK):
        current = []
        previous_end = None
        for match in WORD.finditer(block):
            if previous_end is not None and block[previous_end:match.start()].strip():
                if current:
                    sequences.append(tuple(current))
                current = []
            current.append(match.group(0).lower().replace("\u2019", "'"))
            previous_end = match.end()
        if current:
            sequences.append(tuple(current))
    return sequences


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

def author_key(name: str) -> str:
    """Return a conservative initial-plus-surname author signature."""
    name = fold_unicode(name).casefold()
    words = re.findall(r"[^\W\d_]+", name, flags=re.UNICODE)
    if len(words) <= 1:
        return " ".join(words)
    return " ".join([*(word[0] for word in words[:-1]), words[-1]])


NONPERSON_MARKERS = {
    "academia", "address", "college", "department", "email", "faculty",
    "institute", "institut", "laboratoire", "memory", "school",
    "university", "universite", "whose", "cnrs", "umr", "statistics",
    "france", "usa", "canada", "hungary", "israel", "taiwan",
}
NONPERSON_PHRASES = {
    "computer science", "research group", "united kingdom",
}


def clean_author_names(raw: str) -> list[str]:
    """Extract plausible personal names from one metadata author field.

    Several older TeX sources put affiliations in the same macro as authors.
    Reject obvious institutional/address debris rather than letting it inflate
    author breadth.  A semicolon always separates people; a comma does so only
    when both sides already look like multiword personal names.
    """
    raw = re.sub(r"^\s*\[[^]]*]\s*", "", raw)
    raw = re.sub(
        r"^\s*[+-]?\d+(?:\.\d+)?(?:cm|mm|pt|ex|em)?\s*", "", raw,
        flags=re.IGNORECASE,
    )
    raw = re.sub(r"(?<=[^\W\d_])\d+(?:\s*,\s*\d+)*\s*$", "", raw)
    raw = " ".join(raw.split())
    if not raw:
        return []

    fields = [part.strip() for part in raw.split(";") if part.strip()]
    expanded = []
    for field in fields:
        comma_parts = [part.strip() for part in field.split(",")]
        if (
            len(comma_parts) == 2
            and all(len(re.findall(r"[^\W\d_]+", part, flags=re.UNICODE)) >= 2
                    for part in comma_parts)
        ):
            expanded.extend(comma_parts)
        else:
            expanded.append(field)

    names = []
    for field in expanded:
        folded = fold_unicode(field).casefold()
        words = re.findall(r"[^\W\d_]+", folded, flags=re.UNICODE)
        if (
            not words
            or len(words) > 6
            or any(char.isdigit() for char in field)
            or any(char in field for char in "@[]:")
            or "," in field
            or NONPERSON_MARKERS.intersection(words)
            or any(phrase in folded for phrase in NONPERSON_PHRASES)
        ):
            continue
        names.append(field)
    return names


def item_authors(item: Path) -> list[str]:
    """Return the bibliographic authors recorded for one reference item."""
    metadata = item / "item.json"
    if not metadata.is_file():
        return []
    try:
        record = json.loads(metadata.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    authors = record.get("bibliographic_identity", {}).get("authors", [])
    if not isinstance(authors, list):
        return []
    cleaned = {
        name
        for author in authors if isinstance(author, str)
        for name in clean_author_names(author)
    }
    return sorted(cleaned, key=author_key)


def corpus_items(root: Path) -> list[tuple[str, list[str], list[Path]]]:
    """Return (item_key, authors, tex_files) for each corpus paper."""
    items = []

    arxiv = root / "references" / "items" / "arxiv"
    for item in sorted(arxiv.iterdir()) if arxiv.is_dir() else []:
        if not item.is_dir():
            continue
        tex = sorted(p for p in item.rglob("*.tex") if p.is_file())
        if not tex:
            continue
        items.append((item.name, item_authors(item), tex))

    papers = root / "references" / "items" / "papers"
    for item in sorted(papers.iterdir()) if papers.is_dir() else []:
        if not item.is_dir():
            continue
        tex = sorted(p for p in item.rglob("*.tex") if p.is_file())
        if not tex:
            continue
        items.append((item.name, item_authors(item), tex))
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
    unigram_authors: dict[str, set[str]] = defaultdict(set)
    unigram_unknown_author_df: Counter = Counter()
    manifest = []
    duplicate_items = []
    duplicate_files = []
    seen_documents: dict[tuple[tuple[str, int], ...], str] = {}

    for key, authors, tex_files in corpus_items(root):
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
            unigram_authors[token].update(author_key(author) for author in authors)
            if not authors:
                unigram_unknown_author_df[token] += 1
        manifest.append({
            "item": key, "authors": authors, "files": used,
            "words": sum(item_words.values()), "types": len(item_words),
        })

    out.mkdir(parents=True, exist_ok=True)
    with (out / "unigrams.tsv").open("w", encoding="utf-8") as handle:
        handle.write(
            "word\tpapers\toccurrences\tauthors\tunknown_author_papers\n"
        )
        for word, df in sorted(unigram_df.items(), key=lambda kv: (-kv[1], kv[0])):
            handle.write(
                f"{word}\t{df}\t{unigram_n.get(word, 0)}\t"
                f"{len(unigram_authors[word])}\t"
                f"{unigram_unknown_author_df[word]}\n"
            )

    corpus_authors = {
        author_key(author)
        for item in manifest
        for author in item["authors"]
    }

    summary = {
        "generated_at": now(),
        "papers": len(manifest),
        "authors": len(corpus_authors),
        "papers_without_author_metadata": sum(
            1 for item in manifest if not item["authors"]
        ),
        "prose_words": sum(m["words"] for m in manifest),
        "word_forms": len(unigram_n),
        "lexicon_entries": len(unigram_df),
        "common_word_threshold_papers": COMMON_MIN_PAPERS,
        "common_word_threshold_authors": COMMON_MIN_AUTHORS,
        "common_words": sum(
            1 for word, df in unigram_df.items()
            if df >= COMMON_MIN_PAPERS
            and len(unigram_authors[word]) >= COMMON_MIN_AUTHORS
        ),
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


def load_lexicon(out: Path) -> dict[str, dict[str, int]]:
    unigrams = {}
    for line in (out / "unigrams.tsv").read_text(encoding="utf-8").splitlines()[1:]:
        word, papers, occurrences, authors, unknown_author_papers = line.split("\t")
        unigrams[word] = {
            "papers": int(papers),
            "occurrences": int(occurrences),
            "authors": int(authors),
            "unknown_author_papers": int(unknown_author_papers),
        }
    return unigrams


def location_key(location: str) -> tuple[str, int]:
    path, line = location.rsplit(":", 1)
    return path, int(line)


def compound_comparisons(
    root: Path,
    corpus: dict,
    compounds: dict[str, list[str]],
    min_papers: int,
    min_authors: int,
    dominance_ratio: float,
) -> list[dict]:
    """Compare each manuscript hyphenation with exact open/solid spellings."""
    candidates = {
        word: {
            "hyphenated": (word,),
            "open": tuple(parts(word)),
            "solid": ("".join(parts(word)),),
        }
        for word in compounds
    }
    evidence = {
        word: {
            variant: {
                "occurrences": 0,
                "papers": set(),
                "authors": set(),
                "unknown_author_papers": set(),
            }
            for variant in variants
        }
        for word, variants in candidates.items()
    }

    for item in corpus["items"]:
        item_counts = {
            word: {variant: 0 for variant in variants}
            for word, variants in candidates.items()
        }
        lengths = {len(variants["open"]) for variants in candidates.values()}
        for relpath in item["files"]:
            prose = strip_tex(read(root / relpath))
            flat = Counter(word for word, _ in tokens(prose))
            sequence_counts: dict[int, Counter] = {
                length: Counter() for length in lengths
            }
            for sequence in word_sequences(prose):
                for length in lengths:
                    if len(sequence) < length:
                        continue
                    sequence_counts[length].update(
                        tuple(sequence[index:index + length])
                        for index in range(len(sequence) - length + 1)
                    )

            for word, variants in candidates.items():
                item_counts[word]["hyphenated"] += flat[variants["hyphenated"][0]]
                item_counts[word]["solid"] += flat[variants["solid"][0]]
                item_counts[word]["open"] += sequence_counts[
                    len(variants["open"])
                ][variants["open"]]

        authors = {
            author_key(author) for author in item.get("authors", [])
            if author_key(author)
        }
        for word, variants in item_counts.items():
            for variant, count in variants.items():
                if not count:
                    continue
                stats = evidence[word][variant]
                stats["occurrences"] += count
                stats["papers"].add(item["item"])
                stats["authors"].update(authors)
                if not authors:
                    stats["unknown_author_papers"].add(item["item"])

    def dominates(best: int, alternative: int) -> bool:
        return alternative == 0 or best / alternative >= dominance_ratio

    rows = []
    for word in sorted(compounds, key=lambda key: (-len(compounds[key]), key)):
        internal = evidence[word]
        serialized = {
            variant: {
                "occurrences": stats["occurrences"],
                "papers": len(stats["papers"]),
                "authors": len(stats["authors"]),
                "unknown_author_papers": len(stats["unknown_author_papers"]),
                "paper_keys": sorted(stats["papers"]),
                "author_keys": sorted(stats["authors"]),
                "unknown_author_paper_keys": sorted(
                    stats["unknown_author_papers"]
                ),
                "spelling": (
                    word if variant == "hyphenated"
                    else " ".join(parts(word)) if variant == "open"
                    else "".join(parts(word))
                ),
            }
            for variant, stats in internal.items()
        }

        broad = []
        for variant, stats in serialized.items():
            alternatives = [
                other for name, other in serialized.items() if name != variant
            ]
            if (
                stats["papers"] >= min_papers
                and stats["authors"] >= min_authors
                and all(dominates(stats["papers"], other["papers"])
                        for other in alternatives)
                and all(dominates(stats["authors"], other["authors"])
                        for other in alternatives)
                and not any(other["unknown_author_papers"] for other in alternatives)
            ):
                broad.append(variant)

        if len(broad) == 1:
            assessment = f"broad support for {broad[0]} form"
        elif not any(stats["occurrences"] for stats in serialized.values()):
            assessment = "no comparative evidence"
        elif (
            max(stats["papers"] for stats in serialized.values()) < min_papers
            or max(stats["authors"] for stats in serialized.values()) < min_authors
        ):
            assessment = "sparse evidence"
        else:
            assessment = "mixed or inconclusive evidence"

        author_sets = {
            variant: stats["authors"] for variant, stats in internal.items()
        }
        exclusive = {
            variant: len(author_sets[variant].difference(
                *(author_sets[other] for other in author_sets if other != variant)
            ))
            for variant in author_sets
        }
        all_authors = set().union(*author_sets.values())
        mixed_authors = sum(
            1 for author in all_authors
            if sum(author in authors for authors in author_sets.values()) >= 2
        )
        rows.append({
            "text": word,
            "count": len(compounds[word]),
            "where": sorted(set(compounds[word]), key=location_key),
            "variants": serialized,
            "exclusive_authors": exclusive,
            "mixed_authors": mixed_authors,
            "assessment": assessment,
        })
    return rows


def check(
    root: Path,
    out: Path,
    targets: list[Path],
    rare_max_papers: int = DEFAULT_RARE_MAX_PAPERS,
    rare_max_authors: int = DEFAULT_RARE_MAX_AUTHORS,
    compound_min_papers: int = DEFAULT_COMPOUND_MIN_PAPERS,
    compound_min_authors: int = DEFAULT_COMPOUND_MIN_AUTHORS,
    compound_dominance_ratio: float = DEFAULT_COMPOUND_DOMINANCE_RATIO,
) -> dict:
    unigrams = load_lexicon(out)
    corpus = json.loads((out / "corpus.json").read_text(encoding="utf-8"))

    unknown: dict[str, list] = defaultdict(list)
    rare: dict[str, list] = defaultdict(list)
    compounds: dict[str, list] = defaultdict(list)
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
            location = f"{rel}:{line}"
            if "-" in word:
                compounds[word].append(location)
            entry = unigrams.get(word)
            if entry is None:
                unknown[word].append(location)
            else:
                if (
                    entry["papers"] <= rare_max_papers
                    or entry["authors"] <= rare_max_authors
                ):
                    rare[word].append(location)

    known = set(unigrams)

    def pack(
        bucket: dict[str, list],
        classify: bool = False,
        include_evidence: bool = False,
    ) -> list[dict]:
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
            if include_evidence:
                row.update(unigrams[key])
            rows.append(row)
        return rows

    return {
        "generated_at": now(),
        "targets": [str(t) for t in targets],
        "prose_words": total,
        "rare_max_papers": rare_max_papers,
        "rare_max_authors": rare_max_authors,
        "compound_min_papers": compound_min_papers,
        "compound_min_authors": compound_min_authors,
        "compound_dominance_ratio": compound_dominance_ratio,
        "compound_comparisons": compound_comparisons(
            root, corpus, compounds, compound_min_papers,
            compound_min_authors, compound_dominance_ratio,
        ),
        "unattested_words": pack(unknown, classify=True),
        "rare_words": pack(rare, include_evidence=True),
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
    def word_table(rows: list[dict], columns: tuple[str, ...]) -> list[str]:
        out = ["| " + " | ".join(columns) + " |",
               "|" + "|".join(["---"] * len(columns)) + "|"]
        for row in rows:
            cells = [f"`{row['text']}`", str(row["count"])]
            if "stem" in columns:
                cells.append(f"`{row.get('stem', '')}`")
            if "corpus author signatures" in columns:
                cells += [
                    str(row["authors"]),
                    str(row["papers"]),
                    str(row["unknown_author_papers"]),
                ]
            cells.append(" ".join(f"`{w}`" for w in row["where"][:3]))
            out.append("| " + " | ".join(cells) + " |")
        return out + [""]

    def evidence_cell(stats: dict) -> str:
        cell = f"{stats['authors']} / {stats['papers']} / {stats['occurrences']}"
        if stats["unknown_author_papers"]:
            cell += f" (+{stats['unknown_author_papers']} paper(s) without authors)"
        return cell

    def compound_table(rows: list[dict]) -> list[str]:
        if not rows:
            return []
        out = [
            "| manuscript form | manuscript uses | hyphenated | open | solid | "
            "exclusive author signatures H/O/S; mixed | assessment | where |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for row in rows:
            variants = row["variants"]
            exclusive = row["exclusive_authors"]
            split = (
                f"{exclusive['hyphenated']}/{exclusive['open']}/"
                f"{exclusive['solid']}; {row['mixed_authors']}"
            )
            out.append("| " + " | ".join([
                f"`{row['text']}`",
                str(row["count"]),
                evidence_cell(variants["hyphenated"]),
                evidence_cell(variants["open"]),
                evidence_cell(variants["solid"]),
                split,
                row["assessment"],
                " ".join(f"`{where}`" for where in row["where"][:3]),
            ]) + " |")
        return out + [""]

    manuscript = Path(result["targets"][0]).parent.name or "manuscript"
    lines = [
        f"# Vocabulary check: {manuscript}",
        "",
        f"Generated {result['generated_at']} by `tools/lexicon.py`.",
        "",
        "Every prose word of the manuscript was compared against a lexicon built",
        f"from {corpus['papers']} TeX source items in representation theory and",
        (
            f"neighboring combinatorics, with {corpus['authors']} conservative "
            "author signatures"
        ),
        f"and {corpus['papers_without_author_metadata']} paper(s) lacking author metadata.",
        f"The corpus contains {corpus['prose_words']:,} words of prose",
        f"and {corpus['word_forms']:,} distinct surface word forms. The checker removes",
        "recognized math, citation, label, figure, table, and bibliography markup",
        "on both sides. It is a lexical audit, not a full TeX parser. An entry",
        "records non-attestation or narrow support by papers or author signatures;",
        "it is a prompt for inspection, not a verdict. General-English hyphenation",
        "rules are not evidence of mathematical usage.",
        "",
        "## Summary",
        "",
        f"- manuscript prose words: {result['prose_words']:,}",
        f"- distinct hyphenated forms compared: {len(result['compound_comparisons'])}",
        f"- distinct unattested word forms: {len(result['unattested_words'])}",
        "- distinct narrowly attested forms "
        f"(at most {result['rare_max_papers']} papers or "
        f"{result['rare_max_authors']} author signatures): "
        f"{len(result['rare_words'])}",
        "",
        "## How to use this report",
        "",
        "The checker has no manuscript-level pass or fail result. Inspect each",
        "flagged form in its complete sentence and audit the mathematical meaning",
        "and expository role before changing its spelling. A warning may expose an",
        "undefined label, an imprecise English substitute for a formula or property,",
        "an apparent theorem name, a citation in place of the result used, or",
        "private-process prose. Repair that underlying defect when present.",
        "",
        "Never respell a token merely to make a row disappear. Compare surface",
        "forms only after the phrase is precise, necessary, and properly introduced.",
        "A justified technical term may remain flagged; completion means that every",
        "flag has been inspected and adjudicated on the recorded manuscript revision,",
        "not that this report is empty.",
        "",
        "## Hyphenated, open, and solid spellings",
        "",
        "Every hyphenated manuscript form is compared with its exact open and",
        "solid spellings. Each evidence cell is `author signatures / papers / occurrences`;",
        "occurrences are informational, while broad support requires agreement of",
        "the distinct-paper and author-signature counts. Author counts are lower",
        "bounds when a supporting paper lacks author metadata.",
        "",
        f"A broad-support label requires at least {result['compound_min_papers']} papers,",
        (
            f"at least {result['compound_min_authors']} author signatures, and "
            f"at least a {result['compound_dominance_ratio']:g}:1 advantage "
            "under both counts."
        ),
        "A label describes this finite corpus only; it does not certify correctness",
        "or usual mathematical language, and it does not justify the surrounding",
        "phrase as mathematical exposition.",
        "",
    ]
    lines += compound_table(result["compound_comparisons"])

    for kind, title, note in SECTIONS:
        rows = [r for r in result["unattested_words"] if r["kind"] == kind]
        lines += [f"## {title} ({len(rows)})", "", note, ""]
        if rows:
            columns = ("word", "manuscript uses", "stem", "where") \
                if kind in ("derived", "compound") \
                else ("word", "manuscript uses", "where")
            lines += word_table(rows, columns)

    rare = result["rare_words"]
    lines += [
        f"## Narrowly attested by paper or author-signature breadth ({len(rare)})",
        "",
        f"These forms occur in at most {result['rare_max_papers']} distinct papers",
        f"or papers by at most {result['rare_max_authors']} author signatures.",
        "They may be standard, specialized, proper names, or ordinary words;",
        "inspect their use and first definition in the manuscript. A nonzero",
        "unknown-author-paper count means that the author count is a lower bound.",
        "",
    ]
    lines += word_table(
        rare,
        ("word", "manuscript uses", "corpus author signatures", "corpus papers",
         "unknown-author papers", "where"),
    )
    return "\n".join(lines)


def resolve_report_paths(
    targets: list[Path],
    json_path: Path | None = None,
    markdown_path: Path | None = None,
    report_dir: Path | None = None,
    stdout_only: bool = False,
) -> tuple[Path | None, Path | None]:
    """Resolve report outputs without guessing across manuscript directories."""
    if not targets:
        raise ValueError("at least one target TeX file is required")
    if stdout_only:
        if any(path is not None for path in (json_path, markdown_path, report_dir)):
            raise ValueError(
                "--stdout-only cannot be combined with report output options"
            )
        return None, None

    if json_path is None or markdown_path is None:
        if report_dir is not None:
            default_dir = report_dir
        else:
            parents = {target.resolve().parent for target in targets}
            if len(parents) != 1:
                raise ValueError(
                    "target TeX files have different parent directories; use "
                    "--report-dir or provide both --json and --markdown"
                )
            default_dir = targets[0].parent
        json_path = json_path or default_dir / "vocabulary-report.json"
        markdown_path = markdown_path or default_dir / "vocabulary-report.md"

    if json_path.resolve() == markdown_path.resolve():
        raise ValueError("JSON and Markdown reports must use different paths")
    return json_path, markdown_path


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
    c.add_argument(
        "--rare-max-papers", "--rare-max", dest="rare_max_papers", type=int,
        default=DEFAULT_RARE_MAX_PAPERS,
        help="at most this many supporting papers counts as narrowly attested",
    )
    c.add_argument(
        "--rare-max-authors", type=int, default=DEFAULT_RARE_MAX_AUTHORS,
        help="at most this many author signatures counts as narrowly attested",
    )
    c.add_argument(
        "--compound-min-papers", type=int, default=DEFAULT_COMPOUND_MIN_PAPERS,
        help="minimum supporting papers for a broad compound-spelling signal",
    )
    c.add_argument(
        "--compound-min-authors", type=int, default=DEFAULT_COMPOUND_MIN_AUTHORS,
        help="minimum author signatures for a broad compound-spelling signal",
    )
    c.add_argument(
        "--compound-dominance-ratio", type=float,
        default=DEFAULT_COMPOUND_DOMINANCE_RATIO,
        help="required paper and author ratio for a broad spelling signal",
    )
    c.add_argument(
        "--report-dir", type=Path,
        help="write standard report filenames in this directory",
    )
    c.add_argument(
        "--json", type=Path,
        help="override the JSON report path",
    )
    c.add_argument(
        "--markdown", type=Path,
        help="override the Markdown report path",
    )
    c.add_argument(
        "--stdout-only", action="store_true",
        help="print the summary without writing report files",
    )

    args = parser.parse_args()
    if args.command == "build":
        summary = build(args.root, args.out)
        print(json.dumps({k: v for k, v in summary.items() if k != "items"}, indent=2))
        return 0

    if min(
        args.rare_max_papers,
        args.rare_max_authors,
        args.compound_min_papers,
        args.compound_min_authors,
    ) < 0 or args.compound_dominance_ratio <= 0:
        parser.error("vocabulary thresholds must be nonnegative and the ratio positive")

    try:
        json_report, markdown_report = resolve_report_paths(
            args.targets,
            json_path=args.json,
            markdown_path=args.markdown,
            report_dir=args.report_dir,
            stdout_only=args.stdout_only,
        )
    except ValueError as error:
        parser.error(str(error))

    result = check(
        args.root,
        args.out,
        args.targets,
        rare_max_papers=args.rare_max_papers,
        rare_max_authors=args.rare_max_authors,
        compound_min_papers=args.compound_min_papers,
        compound_min_authors=args.compound_min_authors,
        compound_dominance_ratio=args.compound_dominance_ratio,
    )
    if json_report:
        json_report.parent.mkdir(parents=True, exist_ok=True)
        json_report.write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
    if markdown_report:
        corpus = json.loads((args.out / "corpus.json").read_text(encoding="utf-8"))
        markdown_report.parent.mkdir(parents=True, exist_ok=True)
        markdown_report.write_text(
            render_markdown(result, corpus), encoding="utf-8"
        )
    print(json.dumps({
        "manuscript_result": "not_pass_fail",
        "required_action": (
            "inspect_and_adjudicate_report" if markdown_report
            else "exploratory_only"
        ),
        "prose_words": result["prose_words"],
        "compound_comparisons": len(result["compound_comparisons"]),
        "unattested_words": len(result["unattested_words"]),
        "rare_words": len(result["rare_words"]),
        "json_report": str(json_report) if json_report else None,
        "markdown_report": str(markdown_report) if markdown_report else None,
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
