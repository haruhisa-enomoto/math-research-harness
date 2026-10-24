"""Bibliographic enrichment for the local reference workspace.

The workspace catalog records where files live. This module records what they
are: title, authors, year, identifiers, keywords, and abstract, together with a
per-field provenance note. Everything is extracted from material already on
disk -- unpacked TeX sources, PDF metadata captured by earlier extractions, the
head of extracted text, and item slugs. No network access and no metadata API
query is involved, in line with `docs/LITERATURE.md`.

Sources read by preferred order, per field:

1. `tex`      -- `\\title`, `\\author`, `\\abstract`, `\\keywords`, `\\subjclass`
2. `pdf`      -- PDF document metadata stored in `references/derived/text/*.metadata.json`
3. `text-head` -- the title block at the head of an extracted text derivative
4. `slug`     -- the item key itself
5. `identifier` -- the arXiv identifier (announcement year only)

A Hexagon item is first described from the public work record its fetcher
stored as `original/work.json` (`hexagon-api`); the sources above only fill
fields that record leaves empty. Its arXiv identifier and DOI are kept even when
empty, since a DOI found in the TeX usually belongs to a cited work.

An externally held source -- a file in the inbox, or an item in a separate
library outside this workspace -- has no item directory. Where a derivative was
generated from one, an `external:<slug>` record is written under
`references/external/` so the source is searchable next to the local items.
"""

from __future__ import annotations

import argparse
import gzip
import html
import json
import os
import re
import sys
import tarfile
import tempfile
import unicodedata
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

try:
    from tools.reference_catalog import refresh_catalog
    from tools.reference_utils import write_json_atomic
except ModuleNotFoundError:  # Direct execution: sys.path starts at tools/.
    from reference_catalog import refresh_catalog
    from reference_utils import write_json_atomic


SCHEMA_VERSION = 2

KIND_DIRECTORIES = (("arxiv", "arxiv"), ("papers", "paper"), ("books", "book"), ("hexagon", "hexagon"))
KIND_SINGULAR = dict(KIND_DIRECTORIES)

# Repository trees scanned for the citation back-index. `data/`, `experiments/`,
# and `lib/` are deliberately excluded: they are multi-gigabyte computation
# trees that hold no literature citations, and walking them on this filesystem
# costs minutes.
CITATION_ROOTS = (
    "threads",
    "docs",
    "paper",
    "results",
    "briefings",
    "templates",
    "examples",
)
CITATION_FILES = ("AGENTS.md", "README.md", "STEERING.md", "CLAUDE.md")
CITATION_SUFFIXES = {".md", ".tex", ".json", ".py", ".txt", ".bib", ".lean"}
# Build outputs and caches hold no citations and dominate the walk otherwise.
CITATION_PRUNE = {
    ".lake", ".git", ".venv", ".venv-win", "__pycache__", "node_modules", "build",
    ".pytest_cache", ".ruff_cache", "target", ".mypy_cache", "lake-packages",
}
CITATION_LIMIT = 40
# A generated result table is not a citation site and can be very large.
CITATION_MAX_BYTES = 4 * 1024 * 1024

ACCENTS = {
    "'": "\u0301",
    "`": "\u0300",
    "^": "\u0302",
    '"': "\u0308",
    "~": "\u0303",
    "=": "\u0304",
    ".": "\u0307",
    "u": "\u0306",
    "v": "\u030c",
    "H": "\u030b",
    "c": "\u0327",
    "k": "\u0328",
    "r": "\u030a",
    "d": "\u0323",
    "b": "\u0331",
}
LIGATURES = {
    "ss": "ß",
    "o": "ø",
    "O": "Ø",
    "ae": "æ",
    "AE": "Æ",
    "aa": "å",
    "AA": "Å",
    "l": "ł",
    "L": "Ł",
    "oe": "œ",
    "OE": "Œ",
    "i": "ı",
    "j": "ȷ",
}
GREEK = {
    "alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta", "iota",
    "kappa", "lambda", "mu", "nu", "xi", "pi", "rho", "sigma", "tau", "upsilon",
    "phi", "chi", "psi", "omega", "Gamma", "Delta", "Theta", "Lambda", "Xi",
    "Pi", "Sigma", "Phi", "Psi", "Omega", "varphi", "vartheta", "varepsilon",
}
# Commands whose single argument is ordinary text worth keeping.
TEXT_COMMANDS = {
    "emph", "textit", "textbf", "textrm", "textsc", "textsf", "texttt", "text",
    "mathrm", "mathbf", "mathcal", "mathbb", "mathfrak", "mathsf", "operatorname",
    "lowercase", "uppercase", "MakeLowercase", "MakeUppercase", "mbox", "hbox",
}
# Commands whose argument is discarded entirely.
DROP_COMMANDS = {
    "thanks", "footnote", "footnotemark", "address", "email", "urladdr", "date",
    "inst", "institute", "affil", "affiliation", "label", "index", "vspace",
    "hspace", "protect", "linebreak", "newline", "footnotetext", "orcid",
}

DOI = re.compile(r"10\.\d{4,9}/[^\s\"'{},]+")
YEAR = re.compile(r"\b(1[89]\d\d|20\d\d)\b")
MSC_CODE = re.compile(r"\b\d{2}[A-Z]\d{2}\b")
ARXIV_STAMP = re.compile(r"arXiv:(\S+?)\s*\[[^\]]+\]\s*\d{1,2}\s+\w+\s+(\d{4})")
PAGE_MARKER = re.compile(r"^={2,}\s*page\s*\d+(\s*/\s*\d+)?\s*={2,}", re.IGNORECASE)
# Running heads and publisher furniture that precede the title in scanned papers.
JOURNAL_NOISE = re.compile(
    r"(journal of|annales|proceedings of|transactions of|article (no|id)|available online"
    r"|www\.|https?://|doi:|issn|isbn|©|copyright|all rights reserved|printed in"
    r"|academic press|elsevier|springer|vol\.\s*\d|volume\s+\d|pp\.\s*\d)",
    re.IGNORECASE,
)
MODERN_ARXIV = re.compile(r"^(\d{2})(\d{2})\.\d{4,5}(v\d+)?$")
OLD_ARXIV = re.compile(r"^[a-z][a-z0-9.-]*[-/](\d{2})(\d{2})\d{3}(v\d+)?$")
VERSION_SUFFIX = re.compile(r"v(\d+)$")


# --------------------------------------------------------------------------
# TeX text handling
# --------------------------------------------------------------------------


def strip_comments(text: str) -> str:
    lines = []
    for line in text.splitlines():
        cut = None
        index = 0
        while index < len(line):
            character = line[index]
            if character == "\\":
                index += 2
                continue
            if character == "%":
                cut = index
                break
            index += 1
        lines.append(line if cut is None else line[:cut])
    return "\n".join(lines)


def balanced_argument(text: str, start: int) -> tuple[str, int] | None:
    """Return the brace-delimited argument beginning at ``start`` and its end."""
    while start < len(text) and text[start] in " \n\t":
        start += 1
    if start >= len(text) or text[start] != "{":
        return None
    depth = 0
    for index in range(start, len(text)):
        character = text[index]
        if character == "\\":
            continue
        if index and text[index - 1] == "\\":
            continue
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1 : index], index + 1
    return None


def find_command(text: str, name: str, position: int = 0) -> tuple[str, int] | None:
    """Return the argument of ``\\name`` (skipping an optional argument)."""
    pattern = re.compile(r"\\" + name + r"\s*(?=[\[{])")
    match = pattern.search(text, position)
    while match:
        cursor = match.end()
        if cursor < len(text) and text[cursor] == "[":
            depth = 0
            for index in range(cursor, len(text)):
                if text[index] == "[":
                    depth += 1
                elif text[index] == "]":
                    depth -= 1
                    if depth == 0:
                        cursor = index + 1
                        break
            else:
                return None
        argument = balanced_argument(text, cursor)
        if argument is not None:
            return argument[0], argument[1]
        match = pattern.search(text, match.end())
    return None


def _apply_accents(text: str) -> str:
    def accent(match: re.Match[str]) -> str:
        command, letter = match.group(1), match.group(2) or match.group(3) or ""
        return unicodedata.normalize("NFC", letter + ACCENTS[command])

    text = re.sub(r"\\([`'^\"~=.])\s*(?:\{(\w)\}|(\w))", accent, text)
    text = re.sub(r"\\([uvHckrdb])\s*(?:\{(\w)\}|\s(\w))", accent, text)
    for command, replacement in sorted(LIGATURES.items(), key=lambda pair: -len(pair[0])):
        text = re.sub(r"\\" + command + r"(?![a-zA-Z])\s*\{\}|\\" + command + r"(?![a-zA-Z])", replacement, text)
    return text


def detex(text: str) -> str:
    """Flatten a TeX fragment to searchable plain text."""
    if not text:
        return ""
    text = strip_comments(text)
    text = _apply_accents(text)

    for command in DROP_COMMANDS:
        while True:
            found = find_command(text, command)
            if found is None:
                break
            match = re.search(r"\\" + command + r"\s*(?=[\[{])", text)
            if match is None:
                break
            text = text[: match.start()] + text[found[1] :]
    for command in TEXT_COMMANDS:
        text = re.sub(r"\\" + command + r"\s*\{", "{", text)

    # Greek and other math letters read better as names than as backslashes.
    text = re.sub(r"\\(" + "|".join(sorted(GREEK, key=len, reverse=True)) + r")(?![a-zA-Z])", r"\1", text)
    text = text.replace("\\&", "&").replace("\\_", "_").replace("\\#", "#")
    text = text.replace("\\%", "%").replace("\\$", "$").replace("~", " ")
    text = re.sub(r"\\\\\s*\[[^\]]*\]", " ", text)  # line break with a spacing argument
    text = re.sub(r"\\[a-zA-Z]+\s*", " ", text)
    text = re.sub(r"\\[^a-zA-Z]", " ", text)
    # TeX grouping braces imply no space: "M{\"u}hle" is one word.
    text = text.replace("$", "").replace("{", "").replace("}", "")
    # TeX en/em dashes are written as hyphen runs; keep one so that a search for
    # "Riemann-Roch" matches a title typeset as "Riemann--Roch".
    text = re.sub(r"-{2,}", "-", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


PLACEHOLDER_TITLES = {
    "untitled", "unbekannt", "unknown", "document", "microsoft word", "no title",
    "article", "paper", "manuscript", "output", "main",
}


def is_placeholder_title(value: str) -> bool:
    folded = value.strip().casefold()
    if folded in PLACEHOLDER_TITLES or folded.startswith("microsoft word"):
        return True
    return folded.endswith((".dvi", ".pdf", ".tex", ".ps", ".doc", ".docx"))


# Values scanning software writes into the PDF author field.
SCANNER_AUTHORS = {
    "administrator", "admin", "user", "windows user", "unknown", "owner", "author",
    "pc", "hp", "toshiba", "acer", "dell", "guest", "scanner", "adobe acrobat",
    "microsoft word", "default", "customer",
}


def is_junk_name(value: str) -> bool:
    """Reject macro leftovers and placeholders that are not personal names."""
    folded = value.casefold()
    if folded in SCANNER_AUTHORS or len(value) < 2:
        return True
    if not any(character.isupper() for character in value):
        return True  # "authorsfortoc" and similar macro remnants
    return bool(re.fullmatch(r"[^A-Za-z]+", value))


def clean_name(value: str) -> str:
    """Strip footnote markers and stray punctuation from an author name."""
    name = re.sub(r"[\^*†‡§¶⋆∗]+", "", value)
    name = re.sub(r"\s*\d+\s*$", "", name)
    name = re.sub(r"\s+", " ", name).strip(" ,.;:-")
    words = name.split()
    # "Kevin COULEMBIER" and "Hanpeng GAO" shout the surname; even it out.
    if len(words) > 1 and any(_is_all_caps(word) and len(word) > 2 for word in words):
        if not all(_is_all_caps(word) for word in words if word.isalpha()):
            name = " ".join(
                word.capitalize() if _is_all_caps(word) and len(word) > 2 and "." not in word else word
                for word in words
            )
    return name


def split_authors(raw: str) -> list[str]:
    """Split a raw TeX author field into individual names."""
    parts = re.split(r"\\and\b|\\\\|\\newauthor\b", raw)
    names: list[str] = []
    for part in parts:
        cleaned = detex(part)
        if not cleaned:
            continue
        pieces = re.split(r"\s+and\s+", cleaned)
        if len(pieces) == 1 and cleaned.count(",") >= 2:
            # "A. Author, B. Other, C. Third" -- a comma list, not "Surname, Initials".
            segments = [segment.strip() for segment in cleaned.split(",") if segment.strip()]
            if all(len(segment.split()) >= 2 for segment in segments):
                pieces = segments
        if len(pieces) > 1:
            expanded: list[str] = []
            for piece in pieces:
                expanded.extend(item for item in re.split(r"\s*,\s*", piece) if item)
            pieces = expanded
        for piece in pieces:
            name = clean_name(piece)
            name = re.sub(r"\s*\((eds?|editors?)\.?\)\s*$", "", name, flags=re.IGNORECASE)
            if name and not name.isdigit() and not is_junk_name(name):
                names.append(name)
    return names


def title_case_words(slug: str) -> str:
    words = [word for word in slug.split("-") if word]
    return " ".join(words).capitalize()


# --------------------------------------------------------------------------
# Identity record
# --------------------------------------------------------------------------


@dataclass
class Identity:
    title: str | None = None
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    arxiv_id: str | None = None
    doi: str | None = None
    venue: str | None = None
    keywords: list[str] = field(default_factory=list)
    msc: list[str] = field(default_factory=list)
    abstract: str | None = None
    provenance: dict[str, str] = field(default_factory=dict)

    def absorb(self, other: "Identity", source: str) -> None:
        """Fill empty fields from ``other``, recording ``source`` per field."""
        for name in ("title", "year", "arxiv_id", "doi", "venue", "abstract"):
            if getattr(self, name) in (None, "") and getattr(other, name) not in (None, ""):
                setattr(self, name, getattr(other, name))
                self.provenance[name] = other.provenance.get(name, source)
        for name in ("authors", "keywords", "msc"):
            if not getattr(self, name) and getattr(other, name):
                setattr(self, name, list(getattr(other, name)))
                self.provenance[name] = other.provenance.get(name, source)

    def to_json(self, *, persistent_identifier: str | None, exact_version: str | None) -> dict[str, object]:
        return {
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "arxiv_id": self.arxiv_id,
            "doi": self.doi,
            "venue": self.venue,
            "keywords": self.keywords,
            "msc": self.msc,
            "abstract": self.abstract,
            "persistent_identifier": persistent_identifier,
            "exact_version": exact_version,
        }


def identity_from_tex(source: Path, extra: Path | None = None) -> Identity:
    """Extract identity from an unpacked TeX tree."""
    identity = Identity()
    tex_files = list(source.rglob("*.tex")) if source.is_dir() else []
    # A few items predate the source/ convention and hold TeX at the item root.
    if extra is not None and extra.is_dir():
        tex_files.extend(path for path in extra.glob("*.tex"))
    if not tex_files:
        return identity
    source = source if source.is_dir() else (extra or source)

    candidates: list[tuple[int, Path]] = []
    for path in tex_files:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        score = 0
        if "\\documentclass" in text:
            score += 8
        if "\\begin{document}" in text:
            score += 4
        if "\\title" in text:
            score += 6
        if "\\begin{abstract}" in text:
            score += 2
        if path.stem.casefold() in {"main", "paper", "article", "ms"}:
            score += 2
        candidates.append((score, path))
    candidates.sort(key=lambda pair: (-pair[0], pair[1].as_posix()))

    for _, path in candidates[:12]:
        text = strip_comments(path.read_text(encoding="utf-8", errors="ignore"))
        try:
            relative = path.relative_to(source).as_posix()
        except ValueError:
            relative = path.name
        locator = f"tex:{relative}"
        found = Identity()

        title = next(
            (
                found_title
                for name in ("title", "Title", "ArticleName")
                if (found_title := find_command(text, name))
            ),
            None,
        )
        title_text = detex(title[0]) if title else ""
        if not title_text:
            # AmS-TeX: \title ... \endtitle carries no braces.
            plain = re.search(r"\\title\b(?!\s*[\[{])(.*?)\\endtitle", text, re.DOTALL)
            title_text = detex(plain.group(1)) if plain else ""
        if title_text and not is_placeholder_title(title_text):
            found.title = title_text
            found.provenance["title"] = locator

        authors: list[str] = []
        for command in ("author", "Author"):
            for match in re.finditer(r"\\" + command + r"\s*(?=[\[{])", text):
                argument = find_command(text, command, match.start())
                if argument:
                    authors.extend(split_authors(argument[0]))
        if not authors:
            for plain in re.finditer(r"\\author\b(?!\s*[\[{])(.*?)\\endauthor", text, re.DOTALL):
                authors.extend(split_authors(plain.group(1)))
        if authors:
            seen: set[str] = set()
            found.authors = [name for name in authors if not (name in seen or seen.add(name))]
            found.provenance["authors"] = locator

        abstract = None
        environment = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", text, re.DOTALL)
        if environment:
            abstract = detex(environment.group(1))
        else:
            command = find_command(text, "abstract")
            if command:
                abstract = detex(command[0])
        if abstract:
            found.abstract = abstract
            found.provenance["abstract"] = locator

        for name in ("keywords", "keyword"):
            command = find_command(text, name)
            if command:
                found.keywords = [
                    part.strip() for part in re.split(r"[,;]", detex(command[0])) if part.strip()
                ]
                found.provenance["keywords"] = locator
                break

        subject = find_command(text, "subjclass")
        if subject:
            codes = MSC_CODE.findall(detex(subject[0]))
            if codes:
                found.msc = sorted(set(codes))
                found.provenance["msc"] = locator

        date = find_command(text, "date")
        if date:
            years = YEAR.findall(detex(date[0]))
            if years:
                found.year = int(years[-1])
                found.provenance["year"] = locator

        doi = DOI.search(text)
        if doi:
            found.doi = doi.group(0).rstrip(".,;")
            found.provenance["doi"] = locator

        if not found.title:
            found.absorb(identity_from_centered_title(text, locator), locator)

        identity.absorb(found, locator)
        if identity.title and identity.authors and identity.abstract:
            break
    return identity


def identity_from_pdf_metadata(metadata: dict[str, object], locator: str) -> Identity:
    """Extract identity from PDF document metadata captured during extraction."""
    identity = Identity()
    raw = metadata.get("pdf_metadata")
    if not isinstance(raw, dict):
        return identity
    values = {
        str(key).casefold().lstrip("/"): html.unescape(str(value or "")).strip()
        for key, value in raw.items()
    }

    title = values.get("title", "")
    doi_in_title = DOI.search(title)
    if doi_in_title:
        identity.doi = doi_in_title.group(0).rstrip(".,;")
        identity.provenance["doi"] = locator
        title = ""
    if title and len(title) > 4 and not is_placeholder_title(title):
        identity.title = re.sub(r"\s+", " ", title)
        identity.provenance["title"] = locator

    author = values.get("author", "")
    if author and author.casefold() not in SCANNER_AUTHORS:
        names = [name for name in re.split(r"(?i:\s+and\s+)|;\s*", author) if name.strip()]
        if len(names) == 1 and names[0].count(",") >= 2:
            segments = [part.strip() for part in names[0].split(",") if part.strip()]
            # Split only a genuine list; "Surname, G." is one name, not two.
            if all(len(segment.split()) >= 2 for segment in segments):
                names = segments
        cleaned = [clean_name(name) for name in names]
        identity.authors = [name for name in cleaned if name and not is_junk_name(name)]
        if identity.authors:
            identity.provenance["authors"] = locator

    subject = values.get("subject", "")
    if subject:
        codes = MSC_CODE.findall(subject)
        if codes:
            identity.msc = sorted(set(codes))
            identity.provenance["msc"] = locator
        elif "doi:" in subject.casefold():
            found = DOI.search(subject)
            if found and not identity.doi:
                identity.doi = found.group(0).rstrip(".,;")
                identity.provenance["doi"] = locator
        elif 3 < len(subject) < 120 and "©" not in subject:
            identity.venue = subject
            identity.provenance["venue"] = locator

    keywords = values.get("keywords", "")
    if keywords and "cedram" not in keywords.casefold():
        identity.keywords = [part.strip() for part in re.split(r"[,;]", keywords) if part.strip()]
        identity.provenance["keywords"] = locator

    # PDF creation dates record when a scan or typesetting run happened, not when
    # the work was published, so they are deliberately not read as a year.
    return identity


SIZE_COMMANDS = ("LARGE", "Large", "large", "huge", "Huge", "bf", "bfseries", "sc", "scshape", "it")


def centered_groups(text: str) -> list[tuple[str, str]]:
    """Return `(command, content)` for size-switched groups in the title block.

    Sources predating `\\maketitle` typeset the title as a centered group such as
    `{\\large A Title}` followed by `{\\sc An Author}`.
    """
    start = text.find("\\begin{document}")
    if start < 0:
        return []
    head = text[start : start + 4000]
    block = re.search(r"\\begin\{center\}(.*?)\\end\{center\}", head, re.DOTALL)
    region = block.group(1) if block else head[:1200]

    groups: list[tuple[str, str]] = []
    for match in re.finditer(r"\{\s*\\(" + "|".join(SIZE_COMMANDS) + r")\b", region):
        argument = balanced_argument(region, match.start())
        if argument is None:
            continue
        content = argument[0]
        content = re.sub(r"^\s*\\" + match.group(1) + r"\b", "", content)
        cleaned = detex(content)
        if cleaned:
            groups.append((match.group(1), cleaned))
    return groups


def identity_from_centered_title(text: str, locator: str) -> Identity:
    """Recover title and authors from a pre-`\\maketitle` centered title block."""
    identity = Identity()
    groups = centered_groups(text)
    if not groups:
        return identity
    sizes = {"LARGE", "Large", "large", "huge", "Huge", "bf", "bfseries"}
    title_index = next((index for index, (command, _) in enumerate(groups) if command in sizes), None)
    if title_index is None:
        title_index = 0
    title = groups[title_index][1]
    if 6 < len(title) < 300:
        identity.title = title
        identity.provenance["title"] = locator

    for command, content in groups[title_index + 1 :]:
        names = author_line(content)
        if names and command in {"sc", "scshape", "it", "bf"}:
            identity.authors = names
            identity.provenance["authors"] = locator
            break

    start = text.find("\\begin{document}")
    abstract = re.search(
        r"Abstract[.:]?\s*\}?\s*(.{80,2500}?)(?:\n\s*\n|\\vskip|\\section|\\bigskip)",
        text[start : start + 8000] if start >= 0 else text[:8000],
        re.DOTALL,
    )
    if abstract:
        body = detex(abstract.group(1))
        if len(body) > 60:
            identity.abstract = body
            identity.provenance["abstract"] = locator
    return identity


def identity_from_pdf_file(path: Path, locator: str) -> Identity:
    """Read the PDF document information dictionary -- metadata only, no page text."""
    try:
        import fitz  # PyMuPDF, already a project dependency
    except ModuleNotFoundError:
        return Identity()
    try:
        with fitz.open(path) as document:
            raw = dict(document.metadata or {})
    except Exception:  # a damaged or encrypted PDF is not an error here
        return Identity()
    if not raw:
        return Identity()
    return identity_from_pdf_metadata({"pdf_metadata": raw}, locator)


def _is_all_caps(value: str) -> bool:
    letters = [character for character in value if character.isalpha()]
    return bool(letters) and all(character.isupper() for character in letters)


def _clean_display_case(value: str) -> str:
    """Turn an all-caps line into ordinary sentence case."""
    return value[:1].upper() + value[1:].casefold() if _is_all_caps(value) else value


def _clean_name_case(value: str) -> str:
    """Turn an all-caps by-line name into ordinary name case."""
    if not _is_all_caps(value):
        return value
    return re.sub(r"[A-Za-z]+", lambda match: match.group(0).capitalize(), value)


PARTICLES = {"de", "der", "den", "van", "von", "la", "le", "dos", "da", "di", "del", "y", "bin", "el"}
# A title wrapped onto the next line ends on one of these; a by-line does not.
CONTINUATIONS = {
    "a", "an", "the", "of", "for", "with", "and", "on", "in", "to", "from", "via",
    "over", "under", "between", "by", "into", "their", "its", "some", "at", "or",
}


LABELS = re.compile(
    r"^(abstract|introduction|keywords?|key words|mathematics subject classification"
    r"|subject classification|msc|contents|acknowledge?ments?|date|address|e-?mail|dedicated)",
    re.IGNORECASE,
)


def author_line(line: str) -> list[str] | None:
    """Return the names on ``line`` if it reads as a by-line, else None."""
    if not (4 < len(line) < 140) or LABELS.match(line):
        return None
    if re.search(r"\b(we|this|the|paper|university|department|email|arxiv)\b", line, re.IGNORECASE):
        return None
    segments = [
        re.sub(r"^(and|und|et)\s+", "", part.strip(" ,.;"), flags=re.IGNORECASE)
        for part in re.split(r"(?i:\s+and\s+)|\s*,\s*|\s*&\s*", line)
        if part.strip()
    ]
    segments = [segment for segment in segments if segment]
    if not 1 <= len(segments) <= 8:
        return None
    names: list[str] = []
    for segment in segments:
        words = segment.split()
        if not 1 <= len(words) <= 5:
            return None
        for word in words:
            token = word.strip(".").replace("-", "")
            if not token or not token[0].isalpha():
                return None
            if not (token[0].isupper() or token.casefold() in PARTICLES):
                return None
        names.append(clean_name(segment))
    names = [name for name in names if name]
    return names if names and any(" " in name or len(name) > 3 for name in names) else None


def identity_from_text_head(path: Path, locator: str) -> Identity:
    """Read title, authors, and abstract from the head of an extracted text file.

    Extracted text keeps the visual order of the first page: an optional arXiv
    stamp, the title, the by-line, then the abstract. Blank lines are unreliable
    across extractors, so the reading is line-based.
    """
    identity = Identity()
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return identity

    lines: list[str] = []
    for raw_line in text.splitlines()[:160]:
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line or line.isdigit():
            continue
        if PAGE_MARKER.match(line):
            line = PAGE_MARKER.sub("", line).strip()
            if not line:
                continue
        if JOURNAL_NOISE.search(line):
            continue
        stamp = ARXIV_STAMP.search(line)
        if stamp:
            identity.arxiv_id = stamp.group(1)
            identity.provenance["arxiv_id"] = locator
            identity.year = int(stamp.group(2))
            identity.provenance["year"] = locator
            continue
        if len(line) < 4:
            continue
        lines.append(line)
        if len(lines) >= 30:
            break
    if not lines:
        return identity

    title_parts: list[str] = []
    cursor = 0
    while cursor < len(lines) and len(title_parts) < 3:
        line = lines[cursor]
        if line.casefold().startswith(("abstract", "contents", "introduction")):
            break
        if len(line) > 160 or len(" ".join(title_parts)) > 200:
            break
        if title_parts and author_line(line):
            # A title broken across lines ends on a function word; a by-line does not.
            last = title_parts[-1].split()[-1].strip(",").casefold()
            if last not in CONTINUATIONS:
                break
        title_parts.append(_clean_display_case(line))
        cursor += 1
    title = " ".join(title_parts).strip(" .")
    if 6 < len(title) < 300:
        identity.title = title[:1].upper() + title[1:]
        identity.provenance["title"] = locator

    for line in lines[cursor : cursor + 3]:
        names = author_line(line)
        if names:
            identity.authors = [_clean_name_case(name) for name in names]
            identity.provenance["authors"] = locator
            break

    for index, line in enumerate(lines):
        if line.casefold().startswith("abstract"):
            body = " ".join(lines[index : index + 8])
            identity.abstract = re.sub(r"^abstract[.:\s]*", "", body, flags=re.IGNORECASE)[:2000]
            identity.provenance["abstract"] = locator
            break
    return identity


def identity_from_external_filename(source: str, locator: str) -> Identity:
    """Recover a title, and a year when present, from an external file name.

    An externally held source has no `item.json`, so its own file name is often
    the only structured description available. Only the file stem is read; no
    assumption is made about the directory layout of the external collection.
    """
    identity = Identity()
    stem = source.replace("\\", "/").rsplit("/", 1)[-1]
    stem = re.sub(r"\.(pdf|djvu)$", "", stem, flags=re.IGNORECASE)
    title = re.sub(r"[-_]+", " ", stem).strip()
    years = YEAR.findall(title)
    if years:
        identity.year = int(years[-1])
        identity.provenance["year"] = locator
        title = re.sub(r"\(?\b(1[89]\d\d|20\d\d)\b\)?", "", title).strip()
    if len(title) > 5:
        identity.title = title[:1].upper() + title[1:]
        identity.provenance["title"] = locator
    return identity


def identity_from_legacy(entries: list[str]) -> Identity:
    """Recover author and title from a pre-refactor `Author_Title` entry name."""
    identity = Identity()
    for entry in sorted(entries, key=len, reverse=True):
        name = re.sub(r"\.(gz|tar|tar\.gz|dl|zip|pdf|tex)$", "", entry)
        if name.casefold().startswith("arxiv-") or re.match(r"^\d{4}\.\d{4,5}", name):
            continue
        years = YEAR.findall(name)
        if years:
            identity.year = int(years[-1])
            identity.provenance["year"] = f"legacy:{entry}"
        if " - " in name:  # "George Grätzer, Friedrich Wehrung (eds.) - Lattice Theory..."
            author_part, title_part = name.split(" - ", 1)
        elif "-" in name and "_" in name:
            author_part, title_part = name.split("-", 1)
        else:
            continue
        authors = [
            re.sub(r"\s*\((eds?|editors?)\.?\)\s*$", "", part.replace("_", " ").strip(), flags=re.IGNORECASE)
            for part in re.split(r"[_,]", author_part)
            if part.strip() and part.strip().casefold() not in {"etal", "et al"}
        ]
        title = re.sub(r"_+", " ", title_part).strip()
        title = re.sub(r"\s*\(\d{4}\)\s*$", "", title).strip(" -_")
        if authors:
            identity.authors = authors
            identity.provenance["authors"] = f"legacy:{entry}"
        if title:
            identity.title = title
            identity.provenance["title"] = f"legacy:{entry}"
        if identity.title:
            break
    return identity


def identity_from_slug(key: str, kind: str) -> Identity:
    """Last-resort identity: read the item slug as `authors-title`."""
    identity = Identity()
    if kind in ("arxiv", "hexagon"):
        return identity
    words = key.split("-")
    identity.title = title_case_words(key)
    identity.provenance["title"] = f"slug:{key}"
    # A leading run of surname-like words before an article or preposition.
    stoppers = {"a", "an", "the", "on", "of", "and", "in", "for", "from", "via", "with", "to"}
    surnames: list[str] = []
    for word in words:
        if word in stoppers or word == "etal":
            break
        surnames.append(word)
    if surnames and len(surnames) < len(words):
        identity.authors = [word.capitalize() for word in surnames]
        identity.provenance["authors"] = f"slug:{key}"
        remainder = words[len(surnames) :]
        identity.title = title_case_words("-".join(remainder))
    return identity


def identity_from_hexagon_record(path: Path) -> Identity:
    """Identity from the Hexagon public work record stored by tools/fetch_hexagon.py."""
    identity = Identity()
    try:
        work = json.loads(path.read_text(encoding="utf-8")).get("work")
    except (OSError, json.JSONDecodeError, AttributeError):
        return identity
    if not isinstance(work, dict):
        return identity
    locator = f"hexagon-api:{path.parent.name}/{path.name}"

    def note(name: str, value: object, suffix: str = "") -> None:
        if value not in (None, "", []):
            setattr(identity, name, value)
            identity.provenance[name] = locator + suffix

    note("title", re.sub(r"\s+", " ", str(work.get("title") or "")).strip() or None)
    authors = work.get("authors")
    if isinstance(authors, list):
        note("authors", [str(entry["name"]) for entry in authors if isinstance(entry, dict) and entry.get("name")])
    for stamp in (work.get("versionCreatedAt"), work.get("publishedAt"), work.get("createdAt")):
        match = YEAR.search(str(stamp or ""))
        if match:
            note("year", int(match.group(1)), " (version date)")
            break
    note("abstract", str(work.get("abstract") or "").strip() or None)
    # Hexagon records the arXiv identifier as a submitter declaration it does not verify.
    note("arxiv_id", work.get("arxivId"), " (submitter-declared, unverified by Hexagon)")
    note("doi", work.get("doi"))
    note("venue", "Hexagon preprint")
    note("keywords", [str(tag) for tag in work.get("tags") or [] if tag])
    note("msc", [str(code) for code in work.get("mscCodes") or [] if code])
    return identity


def arxiv_year(key: str) -> int | None:
    """Announcement year implied by an arXiv identifier (not the publication year)."""
    modern = MODERN_ARXIV.match(key)
    if modern:
        return 2000 + int(modern.group(1))
    old = OLD_ARXIV.match(key)
    if old:
        prefix = int(old.group(1))
        return (1900 + prefix) if prefix >= 91 else (2000 + prefix)
    return None


# --------------------------------------------------------------------------
# Workspace scanning
# --------------------------------------------------------------------------


def derived_records(root: Path) -> list[tuple[Path, dict[str, object]]]:
    records: list[tuple[Path, dict[str, object]]] = []
    text_root = root / "derived" / "text"
    if not text_root.is_dir():
        return records
    for path in sorted(text_root.glob("*.metadata.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            records.append((path, payload))
    return records


def derived_source(payload: dict[str, object]) -> str:
    for key in ("source_original", "source_pdf", "source_djvu", "source"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def derived_slug(path: Path) -> str:
    return path.name.removesuffix(".metadata.json")


def derivative_files(root: Path, slug: str) -> list[str]:
    """Every generated reading aid whose name is keyed by ``slug``."""
    found: list[str] = []
    for subdirectory, patterns in (
        ("text", (f"{slug}.txt", f"{slug}.metadata.json")),
        ("ocr", (f"{slug}.ocr.pdf",)),
        ("pages", (f"{slug}_p*.png", f"{slug}_p*.jpg")),
    ):
        base = root / "derived" / subdirectory
        if not base.is_dir():
            continue
        for pattern in patterns:
            for path in sorted(base.glob(pattern)):
                found.append(f"references/derived/{subdirectory}/{path.name}")
    return found


def slug_to_item(root: Path, catalog_keys: dict[str, str]) -> dict[str, str]:
    """Map a derivative slug to an item id, by recorded source path or by key."""
    mapping: dict[str, str] = {}
    for path, payload in derived_records(root):
        slug = derived_slug(path)
        source = derived_source(payload)
        match = re.search(r"references/items/(arxiv|papers|books|hexagon)/([^/]+)/", source.replace("\\", "/"))
        if match:
            singular = KIND_SINGULAR[match.group(1)]
            mapping[slug] = f"{singular}:{match.group(2)}"
        elif slug in catalog_keys:
            mapping[slug] = catalog_keys[slug]
    return mapping


def citation_index(repo_root: Path) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Scan tracked repository trees for references to items and derivatives."""
    item_pattern = re.compile(r"references/items/(arxiv|papers|books|hexagon)/([A-Za-z0-9._-]+)")
    derived_pattern = re.compile(r"references/derived/(?:text|ocr|pages)/([A-Za-z0-9._-]+?)(?:\.metadata)?\.(?:txt|json|pdf|png|jpg)")
    by_item: dict[str, set[str]] = {}
    by_slug: dict[str, set[str]] = {}

    paths: list[Path] = [repo_root / name for name in CITATION_FILES]
    for name in CITATION_ROOTS:
        base = repo_root / name
        if not base.is_dir():
            continue
        for directory, subdirectories, filenames in os.walk(base):
            subdirectories[:] = [name for name in subdirectories if name not in CITATION_PRUNE]
            paths.extend(Path(directory) / filename for filename in filenames)

    for path in paths:
        if path.suffix.casefold() not in CITATION_SUFFIXES or not path.is_file():
            continue
        if path.stat().st_size > CITATION_MAX_BYTES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if "references/" not in text:
            continue
        display = path.relative_to(repo_root).as_posix()
        for match in item_pattern.finditer(text):
            singular = KIND_SINGULAR[match.group(1)]
            by_item.setdefault(f"{singular}:{match.group(2)}", set()).add(display)
        for match in derived_pattern.finditer(text):
            slug = match.group(1).removesuffix(".ocr")
            slug = re.sub(r"_p\d+$", "", slug)
            by_slug.setdefault(slug, set()).add(display)

    return (
        {key: sorted(value) for key, value in by_item.items()},
        {key: sorted(value) for key, value in by_slug.items()},
    )


def manual_fields(previous: dict[str, object]) -> set[str]:
    provenance = previous.get("metadata_provenance")
    if not isinstance(provenance, dict):
        return set()
    return {name for name, value in provenance.items() if isinstance(value, str) and value.startswith("manual")}


# --------------------------------------------------------------------------
# Record construction
# --------------------------------------------------------------------------


def source_populated(item_path: Path) -> bool:
    source = item_path / "source"
    return source.is_dir() and any(source.iterdir())


def unpack_original(item_path: Path) -> str | None:
    """Unpack an already downloaded archive that was never expanded into source/.

    Purely local: it reads `original/source.*` and writes `source/`. Some items
    were filed before the unpacking step existed, which leaves them unreadable
    and undescribable.
    """
    source = item_path / "source"
    if source_populated(item_path):
        return None
    archives = sorted((item_path / "original").glob("source.*")) if (item_path / "original").is_dir() else []
    if not archives:
        return None
    archive = archives[0]

    try:
        from tools.fetch_arxiv import install_source
    except ModuleNotFoundError:
        from fetch_arxiv import install_source
    try:
        with tempfile.TemporaryDirectory(prefix="reference-metadata-") as temporary:
            staged = Path(temporary) / "original"
            staged.mkdir()
            _, extracted = install_source(archive, staged, source)
    except (OSError, RuntimeError, tarfile.TarError, zipfile.BadZipFile, gzip.BadGzipFile, EOFError) as error:
        return f"{archive.name}: {error}"
    return None if extracted else f"{archive.name}: nothing extracted"


def local_artifacts(item_path: Path, suffix: str, limit: int = 3) -> list[Path]:
    found: list[Path] = []
    for subdirectory in ("original", "source"):
        base = item_path / subdirectory
        if base.is_dir():
            found.extend(sorted(path for path in base.rglob(f"*{suffix}") if path.is_file()))
    return found[:limit]


def build_identity(
    *,
    kind: str,
    key: str,
    item_path: Path,
    legacy_entries: list[str],
    pdf_identities: list[Identity],
    text_paths: list[Path],
) -> Identity:
    identity = Identity()
    record = Identity()
    if kind == "hexagon":
        record = identity_from_hexagon_record(item_path / "original" / "work.json")
        identity.absorb(record, "hexagon-api")
    tex = identity_from_tex(item_path / "source", item_path)
    identity.absorb(tex, "tex")
    for candidate in pdf_identities:
        identity.absorb(candidate, "pdf")
    if not (identity.title and identity.authors):
        for path in local_artifacts(item_path, ".pdf"):
            locator = f"pdf-metadata:{path.relative_to(item_path).as_posix()}"
            identity.absorb(identity_from_pdf_file(path, locator), locator)
        for path in [*local_artifacts(item_path, ".txt"), *text_paths]:
            locator = f"text-head:{path.name}"
            identity.absorb(identity_from_text_head(path, locator), locator)
    identity.absorb(identity_from_legacy(legacy_entries), "legacy")
    identity.absorb(identity_from_slug(key, kind), f"slug:{key}")

    if kind == "hexagon":
        # The record is authoritative for identifiers even when it has none; a
        # DOI found in the TeX usually belongs to a bibliography entry.
        for name in ("arxiv_id", "doi"):
            setattr(identity, name, getattr(record, name))
            if name in record.provenance:
                identity.provenance[name] = record.provenance[name]
            else:
                identity.provenance.pop(name, None)
    if kind == "arxiv":
        identity.arxiv_id = key
        identity.provenance["arxiv_id"] = f"identifier:{key}"
        if identity.year is None:
            year = arxiv_year(key)
            if year is not None:
                identity.year = year
                identity.provenance["year"] = f"identifier:{key} (announcement year)"
    return identity


def search_blob(identity: Identity, key: str, aliases: list[str]) -> str:
    parts = [identity.title or "", " ".join(identity.authors), str(identity.year or ""), identity.venue or ""]
    parts.extend([identity.doi or "", " ".join(identity.keywords), " ".join(identity.msc)])
    parts.extend([identity.abstract or "", key, " ".join(aliases)])
    return re.sub(r"\s+", " ", " ".join(part for part in parts if part)).casefold()


def refresh_items(
    root: Path,
    repo_root: Path,
    *,
    force: bool = False,
    only: str | None = None,
    unpack: bool = False,
    scan_citations: bool = True,
    update_catalog: bool = True,
) -> dict[str, object]:
    """Write or update `item.json` for every catalog item, plus external records."""
    catalog_path = root / "CATALOG.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8")) if catalog_path.is_file() else {"items": []}
    legacy_by_id = {
        str(item.get("id")): list(item.get("legacy_entries") or [])
        for item in catalog.get("items", [])
        if isinstance(item, dict)
    }

    catalog_keys = {
        str(item.get("key")): str(item.get("id"))
        for item in catalog.get("items", [])
        if isinstance(item, dict)
    }
    slug_map = slug_to_item(root, catalog_keys)
    # Scanning the repository is the slow part; a single-item refresh after a
    # download keeps the citations already recorded instead of rescanning.
    item_citations, slug_citations = citation_index(repo_root) if scan_citations else ({}, {})

    pdf_by_item: dict[str, list[Identity]] = {}
    derived_by_item: dict[str, list[str]] = {}
    external_payloads: dict[str, dict[str, object]] = {}
    for path, payload in derived_records(root):
        slug = derived_slug(path)
        locator = f"pdf:references/derived/text/{path.name}"
        identity = identity_from_pdf_metadata(payload, locator)
        item_id = slug_map.get(slug)
        if item_id:
            pdf_by_item.setdefault(item_id, []).append(identity)
            derived_by_item.setdefault(item_id, []).extend(derivative_files(root, slug))
        else:
            external_payloads[slug] = {"identity": identity, "payload": payload}

    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    written = 0
    unresolved: list[str] = []
    unpacked: list[str] = []
    unpack_failures: list[str] = []
    empty: list[str] = []
    for plural, singular in KIND_DIRECTORIES:
        kind_root = root / "items" / plural
        if not kind_root.is_dir():
            continue
        for item_path in sorted(path for path in kind_root.iterdir() if path.is_dir()):
            key = item_path.name
            item_id = f"{singular}:{key}"
            if only and only not in (item_id, key):
                continue
            metadata_path = item_path / "item.json"
            previous: dict[str, object] = {}
            if metadata_path.is_file():
                try:
                    previous = json.loads(metadata_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    previous = {}
            if not isinstance(previous, dict):
                previous = {}

            if unpack and not source_populated(item_path):
                problem = unpack_original(item_path)
                if problem:
                    unpack_failures.append(f"{item_id}: {problem}")
                elif source_populated(item_path):
                    unpacked.append(item_id)

            legacy_entries = legacy_by_id.get(item_id, [])
            text_paths = [
                root.parent / name
                for name in derived_by_item.get(item_id, [])
                if name.endswith(".txt")
            ]
            identity = build_identity(
                kind=singular,
                key=key,
                item_path=item_path,
                legacy_entries=legacy_entries,
                pdf_identities=pdf_by_item.get(item_id, []),
                text_paths=[path for path in text_paths if path.is_file()],
            )

            kept = manual_fields(previous) if not force else set()
            previous_identity = previous.get("bibliographic_identity")
            previous_provenance = previous.get("metadata_provenance")
            if kept:
                if isinstance(previous_identity, dict):
                    for name in kept:
                        if name in previous_identity:
                            setattr(identity, name, previous_identity[name])
                            if isinstance(previous_provenance, dict):
                                identity.provenance[name] = str(previous_provenance[name])

            version = VERSION_SUFFIX.search(key) if singular in ("arxiv", "hexagon") else None
            if singular == "arxiv":
                persistent = f"arXiv:{key}"
            elif singular == "hexagon":
                persistent = f"hexagon:{key}"
            else:
                persistent = f"doi:{identity.doi}" if identity.doi else None
            exact_version = version.group(0) if version else None
            if isinstance(previous_identity, dict):
                if "persistent_identifier" in kept:
                    persistent = previous_identity.get("persistent_identifier")
                if "exact_version" in kept:
                    exact_version = previous_identity.get("exact_version")
            aliases = sorted(set(legacy_entries))
            derivatives = sorted(set(derived_by_item.get(item_id, [])))
            citations = sorted(item_citations.get(item_id, []))
            for slug, mapped in slug_map.items():
                if mapped == item_id:
                    citations.extend(slug_citations.get(slug, []))
            citations = sorted(set(citations))
            if not scan_citations:
                previous_citations = previous.get("citations")
                citations = [str(entry) for entry in previous_citations] if isinstance(previous_citations, list) else []
                citation_total = int(previous.get("citation_count") or len(citations))
            else:
                citation_total = len(citations)

            payload = dict(previous)
            payload.update(
                {
                    "schema_version": SCHEMA_VERSION,
                    "id": item_id,
                    "kind": singular,
                    "key": key,
                    # Workspace-relative, as the catalog audit requires.
                    "item_path": item_path.relative_to(root).as_posix(),
                    "bibliographic_identity": identity.to_json(
                        persistent_identifier=persistent,
                        exact_version=exact_version,
                    ),
                    "metadata_provenance": dict(sorted(identity.provenance.items())),
                    "aliases": aliases,
                    "derivatives": derivatives,
                    "citations": citations[:CITATION_LIMIT],
                    "citation_count": citation_total,
                    "search_text": search_blob(identity, key, aliases),
                    "metadata_refreshed_at": timestamp,
                }
            )
            payload.setdefault("checked_at", timestamp)
            write_json_atomic(metadata_path, payload)
            written += 1
            if identity.provenance.get("title", "").startswith("slug"):
                unresolved.append(item_id)
            if not any(
                path.is_file()
                for path in item_path.rglob("*")
                if path.name != "item.json"
            ):
                empty.append(item_id)

    external_written = 0
    if not only:
        external_written = write_external_records(
            root, external_payloads, slug_citations, timestamp, force=force
        )

    catalog_result: dict[str, object] | None = None
    if update_catalog:
        catalog_result = refresh_catalog(root)
        catalog_result["index"] = write_index(root)
    return {
        "items_written": written,
        "external_records": external_written,
        "unpacked_originals": sorted(unpacked),
        "unpack_failures": sorted(unpack_failures),
        "unresolved_titles": sorted(unresolved),
        "items_without_files": sorted(empty),
        "catalog": catalog_result,
    }


def write_external_records(
    root: Path,
    external_payloads: dict[str, dict[str, object]],
    slug_citations: dict[str, list[str]],
    timestamp: str,
    *,
    force: bool = False,
) -> int:
    """Record externally held sources (inbox, external libraries) held only as derivatives."""
    external_root = root / "external"
    external_root.mkdir(parents=True, exist_ok=True)
    written = 0
    for slug in sorted(external_payloads):
        identity = external_payloads[slug]["identity"]
        payload = external_payloads[slug]["payload"]
        assert isinstance(identity, Identity) and isinstance(payload, dict)
        source = derived_source(payload)
        holding = "inbox" if "references/inbox" in source else "external"

        if not identity.title and holding == "external":
            identity.absorb(
                identity_from_external_filename(source, f"external-filename:{slug}"),
                "external-filename",
            )
        if not (identity.title and identity.authors):
            extracted = root / "derived" / "text" / f"{slug}.txt"
            if extracted.is_file():
                identity.absorb(identity_from_text_head(extracted, f"text-head:{slug}.txt"), "text-head")
        if identity.title is None:
            identity.absorb(identity_from_slug(slug, "paper"), f"slug:{slug}")

        record_path = external_root / f"{slug}.json"
        previous: dict[str, object] = {}
        if record_path.is_file():
            try:
                previous = json.loads(record_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                previous = {}
        kept = manual_fields(previous) if not force else set()
        previous_identity = previous.get("bibliographic_identity")
        previous_provenance = previous.get("metadata_provenance")
        if kept and isinstance(previous_identity, dict):
            for name in kept:
                if name in previous_identity:
                    setattr(identity, name, previous_identity[name])
                    if isinstance(previous_provenance, dict):
                        identity.provenance[name] = str(previous_provenance[name])

        persistent = f"doi:{identity.doi}" if identity.doi else None
        exact_version = None
        if isinstance(previous_identity, dict):
            if "persistent_identifier" in kept:
                persistent = previous_identity.get("persistent_identifier")
            if "exact_version" in kept:
                exact_version = previous_identity.get("exact_version")

        citations = sorted(slug_citations.get(slug, []))
        record = dict(previous)
        record.update(
            {
                "schema_version": SCHEMA_VERSION,
                "id": f"external:{slug}",
                "kind": "external",
                "key": slug,
                "holding": holding,
                "original_path": source,
                "source_sha256": payload.get("source_sha256"),
                "bibliographic_identity": identity.to_json(
                    persistent_identifier=persistent,
                    exact_version=exact_version,
                ),
                "metadata_provenance": dict(sorted(identity.provenance.items())),
                "aliases": [],
                "derivatives": derivative_files(root, slug),
                "citations": citations[:CITATION_LIMIT],
                "citation_count": len(citations),
                "search_text": search_blob(identity, slug, []),
                "metadata_refreshed_at": timestamp,
            }
        )
        write_json_atomic(record_path, record)
        written += 1
    return written


def surname(name: str) -> str:
    if "," in name:
        return name.split(",", 1)[0].strip()
    words = [word for word in name.replace(".", " ").split() if word]
    return words[-1] if words else name


def hexagon_tags(record: dict[str, object]) -> list[str]:
    """Short labels for Hexagon's declarations and record status."""
    hexagon = record.get("hexagon")
    if not isinstance(hexagon, dict):
        return []
    tags = [
        f"authorship {hexagon.get('authorship_mode') or '?'}",
        f"human understanding {hexagon.get('human_understanding') or '?'}",
    ]
    if hexagon.get("status") != "published" or hexagon.get("withdrawn_at"):
        tags.append(f"status {hexagon.get('status')}")
    return tags


def index_line(record: dict[str, object]) -> str:
    bibliography = record.get("bibliographic_identity")
    bibliography = bibliography if isinstance(bibliography, dict) else {}
    authors = [str(name) for name in bibliography.get("authors") or []]
    shown = ", ".join(surname(name) for name in authors[:4]) + (" et al." if len(authors) > 4 else "")
    year = bibliography.get("year")
    title = str(bibliography.get("title") or "(untitled)")

    tags: list[str] = []
    if record.get("kind") == "hexagon":
        tags.append(str(bibliography.get("persistent_identifier") or record.get("id")))
        tags.extend(hexagon_tags(record))
    if bibliography.get("arxiv_id"):
        tags.append(f"arXiv:{bibliography['arxiv_id']}")
    if bibliography.get("doi"):
        tags.append(f"doi:{bibliography['doi']}")
    if bibliography.get("venue"):
        tags.append(str(bibliography["venue"]))
    if record.get("kind") == "external":
        tags.append(f"held in {record.get('holding', 'external')}")
    if record.get("citation_count"):
        tags.append(f"cited ×{record['citation_count']}")

    location = record.get("path") or record.get("original_path") or record.get("record_path") or ""
    suffix = f" — {'; '.join(tags)}" if tags else ""
    return f"- **{shown or '(unattributed)'}**{f' ({year})' if year else ''}. *{title}*{suffix}\n  `{location}`"


def write_index(root: Path) -> str:
    """Write the human-readable author-sorted index next to the JSON catalog."""
    catalog = json.loads((root / "CATALOG.json").read_text(encoding="utf-8"))
    records = [
        record
        for record in [*catalog.get("items", []), *catalog.get("external_sources", [])]
        if isinstance(record, dict)
    ]
    counts: dict[str, int] = {}
    for record in records:
        counts[str(record.get("kind"))] = counts.get(str(record.get("kind")), 0) + 1

    grouped: dict[str, list[dict[str, object]]] = {}
    for record in records:
        bibliography = record.get("bibliographic_identity")
        authors = (bibliography or {}).get("authors") if isinstance(bibliography, dict) else None
        first = surname(str(authors[0])) if authors else ""
        letter = first[:1].upper() if first[:1].isalpha() else "#"
        grouped.setdefault(letter, []).append(record)

    lines = [
        "# Local reference catalog",
        "",
        f"Generated {catalog.get('generated_at')} by `tools/reference_metadata.py`.",
        "Do not edit: rerun the tool instead. Search it with `tools/reference_lookup.py`.",
        "",
        "Bibliographic fields are extracted from local material (TeX sources, PDF",
        "document metadata, extracted text, item slugs). They are an availability",
        "index, not a checked citation: confirm identity in the source before citing.",
        "",
        "  ".join(f"**{kind}**: {count}" for kind, count in sorted(counts.items())),
        "",
    ]
    for letter in sorted(grouped):
        lines.append(f"## {letter}")
        lines.append("")
        entries = sorted(
            grouped[letter],
            key=lambda record: (
                surname(str((record.get("bibliographic_identity") or {}).get("authors") or [""])[0]).casefold(),
                str((record.get("bibliographic_identity") or {}).get("title") or "").casefold(),
            ),
        )
        lines.extend(index_line(record) for record in entries)
        lines.append("")

    path = root / "CATALOG.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return display_relative(path, root)


def display_relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root.parent).as_posix()
    except ValueError:
        return path.as_posix()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract bibliographic identity for local reference items from on-disk material.",
    )
    parser.add_argument("--root", type=Path, default=Path("references"))
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--item", help="refresh a single item id or key")
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite fields whose recorded provenance is manual",
    )
    parser.add_argument(
        "--unpack-originals",
        action="store_true",
        help="expand already downloaded archives that have no source/ tree (no network)",
    )
    args = parser.parse_args()

    result = refresh_items(
        args.root,
        args.repo_root,
        force=args.force,
        only=args.item,
        unpack=args.unpack_originals,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
