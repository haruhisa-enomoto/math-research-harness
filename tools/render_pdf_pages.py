from __future__ import annotations

import argparse
import json
from pathlib import Path

import fitz

try:
    from tools.reference_utils import parse_pages
except ModuleNotFoundError:  # Direct execution starts with tools/ on sys.path.
    from reference_utils import parse_pages


def render_pages(pdf: Path, pages_spec: str, output_dir: Path, dpi: int = 180) -> list[Path]:
    pdf = pdf.resolve()
    if not pdf.is_file():
        raise FileNotFoundError(pdf)
    if dpi < 36 or dpi > 1200:
        raise ValueError("dpi must be between 36 and 1200")

    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    with fitz.open(pdf) as document:
        pages = parse_pages(pages_spec, document.page_count)
        stem = pdf.stem[:64]
        for page_number in pages:
            pixmap = document[page_number - 1].get_pixmap(dpi=dpi)
            output = output_dir / f"{stem}_p{page_number}.png"
            pixmap.save(output)
            outputs.append(output)
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Render selected PDF pages to PNG.")
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--pages", required=True, help="one-indexed pages, e.g. 1-4 or 1,5")
    parser.add_argument("--out-dir", default=Path("references/derived/pages"), type=Path)
    parser.add_argument("--dpi", default=180, type=int)
    args = parser.parse_args()
    outputs = render_pages(args.pdf, args.pages, args.out_dir, args.dpi)
    print(json.dumps([str(path) for path in outputs], indent=2))


if __name__ == "__main__":
    main()
