from __future__ import annotations

import argparse
import io
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

import fitz
from fontTools.agl import toUnicode
from fontTools.cffLib import CFFFontSet

try:
    from tools.reference_utils import parse_pages, sha256, write_json_atomic, write_text_atomic
except ModuleNotFoundError:  # Direct execution starts with tools/ on sys.path.
    from reference_utils import parse_pages, sha256, write_json_atomic, write_text_atomic


EXPLICIT_GLYPHS = {
    "mapsto": "↦",
    "hatwide": "^",
    "widehat": "^",
    "tildewide": "~",
    "widetilde": "~",
    "negationslash": "̸",
}
SIZE_SUFFIXES = ("display", "text", "bigg", "Bigg", "big", "Big")
CANONICAL = {"∆": "Δ", "Ω": "Ω"}


def glyph_name_to_unicode(name: str) -> str | None:
    """Resolve a PostScript glyph name to Unicode when possible."""
    if name in EXPLICIT_GLYPHS:
        return EXPLICIT_GLYPHS[name]

    candidates = [name]
    for suffix in SIZE_SUFFIXES:
        if name.endswith(suffix) and len(name) > len(suffix):
            candidates.append(name[: -len(suffix)])
    candidates.extend(candidate.rstrip("0123456789") for candidate in list(candidates))
    for candidate in candidates:
        if not candidate:
            continue
        resolved = toUnicode(candidate)
        if resolved:
            return "".join(CANONICAL.get(character, character) for character in resolved)
    return None


def build_glyph_order(document: fitz.Document) -> dict[str, list[str]]:
    """Map embedded CFF font basenames to glyph-id-ordered names."""
    orders: dict[str, list[str]] = {}
    for page in document:
        for font in page.get_fonts(full=True):
            xref, basename = font[0], font[3]
            if basename in orders:
                continue
            buffer = document.extract_font(xref)[3]
            if not buffer:
                continue
            try:
                cff = CFFFontSet()
                cff.decompile(io.BytesIO(buffer), None, isCFF2=False)
                orders[basename] = cff[cff.fontNames[0]].getGlyphOrder()
            except Exception:  # Non-CFF or damaged fonts simply use ordinary extraction.
                continue
    return orders


def build_origin_glyphs(page: fitz.Page) -> dict[tuple[int, int], tuple[str, int]]:
    origins: dict[tuple[int, int], tuple[str, int]] = {}
    for span in page.get_texttrace():
        for character in span["chars"]:
            _unicode, glyph_id, origin = character[0], character[1], character[2]
            key = (round(origin[0] * 100), round(origin[1] * 100))
            origins[key] = (span["font"], glyph_id)
    return origins


def repaired_page_text(
    page: fitz.Page,
    glyph_order: dict[str, list[str]],
    repaired: Counter[str],
    unresolved: Counter[str],
) -> str:
    origins = build_origin_glyphs(page)
    lines: list[str] = []
    for block in page.get_text("rawdict")["blocks"]:
        if block.get("type", 0) != 0:
            continue
        for line in block.get("lines", []):
            output: list[str] = []
            for span in line["spans"]:
                for character in span["chars"]:
                    text = character["c"]
                    if ord(text) >= 32 and text != "�":
                        output.append(text)
                        continue
                    key = (
                        round(character["origin"][0] * 100),
                        round(character["origin"][1] * 100),
                    )
                    font, glyph_id = origins.get(key, (span["font"], -1))
                    names = glyph_order.get(font)
                    name = names[glyph_id] if names and 0 <= glyph_id < len(names) else None
                    resolved = glyph_name_to_unicode(name) if name else None
                    if resolved is None:
                        unresolved[f"{font}/{name or hex(ord(text))}"] += 1
                        output.append(text)
                    else:
                        repaired[f"{name} -> {resolved!r}"] += 1
                        output.append(resolved)
            lines.append("".join(output))
    return "".join(f"{line}\n" for line in lines)


def extract_pdf(
    pdf: Path,
    output: Path,
    *,
    metadata_output: Path | None = None,
    pages_spec: str | None = None,
    repair_glyphs: bool = False,
) -> dict[str, object]:
    pdf = pdf.resolve()
    if not pdf.is_file():
        raise FileNotFoundError(pdf)

    repaired: Counter[str] = Counter()
    unresolved: Counter[str] = Counter()
    with fitz.open(pdf) as document:
        pages = parse_pages(pages_spec, document.page_count)
        glyph_order = build_glyph_order(document) if repair_glyphs else {}
        blocks: list[str] = []
        for page_number in pages:
            page = document[page_number - 1]
            text = (
                repaired_page_text(page, glyph_order, repaired, unresolved)
                if repair_glyphs
                else page.get_text("text")
            )
            blocks.append(
                f"===== PAGE {page_number} / {document.page_count} =====\n{text.rstrip()}\n"
            )
        page_count = document.page_count
        pdf_metadata = document.metadata

    write_text_atomic(output, "\n".join(blocks))
    metadata: dict[str, object] = {
        "schema_version": 1,
        "source_pdf": str(pdf),
        "source_sha256": sha256(pdf),
        "output_text": str(output),
        "extracted_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "page_count": page_count,
        "pages_extracted": pages,
        "pdf_metadata": pdf_metadata,
        "extractor": "tools/extract_pdf_text.py using PyMuPDF",
        "pymupdf_version": fitz.VersionBind,
        "glyph_repair": repair_glyphs,
    }
    if repair_glyphs:
        metadata["glyphs_repaired"] = dict(repaired.most_common())
        metadata["glyphs_unresolved"] = dict(unresolved.most_common())
    if metadata_output is not None:
        write_json_atomic(metadata_output, metadata)
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract page-delimited text from a PDF.")
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--metadata-out", type=Path)
    parser.add_argument("--pages", help="one-indexed pages, e.g. 1-4 or 1,5,20-22")
    parser.add_argument(
        "--repair-glyphs",
        action="store_true",
        help="attempt recovery of unmapped mathematical glyphs from embedded CFF fonts",
    )
    args = parser.parse_args()

    metadata = extract_pdf(
        args.pdf,
        args.out,
        metadata_output=args.metadata_out,
        pages_spec=args.pages,
        repair_glyphs=args.repair_glyphs,
    )
    print(json.dumps(metadata, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
