from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import fitz

try:
    from tools.extract_pdf_text import extract_pdf
    from tools.reference_utils import (
        command_version,
        parse_pages,
        require_commands,
        sha256,
        slugify,
        write_json_atomic,
        write_text_atomic,
    )
except ModuleNotFoundError:  # Direct execution starts with tools/ on sys.path.
    from extract_pdf_text import extract_pdf
    from reference_utils import (
        command_version,
        parse_pages,
        require_commands,
        sha256,
        slugify,
        write_json_atomic,
        write_text_atomic,
    )


def run(command: list[str], commands: list[list[str]], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    commands.append(command)
    return subprocess.run(command, check=True, capture_output=capture, text=True)


def pdf_page_count(path: Path) -> int:
    with fitz.open(path) as document:
        return document.page_count


def pdf_has_usable_text(path: Path, pages: list[int]) -> bool:
    with fitz.open(path) as document:
        counts = [len(document[page - 1].get_text("text").strip()) for page in pages]
    useful = sum(count >= 40 for count in counts)
    return useful >= max(1, (len(counts) * 3 + 4) // 5)


def djvu_page_count(path: Path, commands: list[list[str]]) -> int:
    completed = run(["djvused", str(path), "-e", "n"], commands, capture=True)
    return int(completed.stdout.strip())


def djvu_text(
    path: Path,
    pages: list[int],
    total: int,
    commands: list[list[str]],
) -> tuple[str, bool]:
    blocks: list[str] = []
    useful = 0
    for page in pages:
        completed = run(["djvutxt", f"--page={page}", str(path)], commands, capture=True)
        text = completed.stdout.strip()
        useful += len(text) >= 40
        blocks.append(f"===== PAGE {page} / {total} =====\n{text}\n")
    return "\n".join(blocks), useful >= max(1, (len(pages) * 3 + 4) // 5)


def image_document_to_pdf(input_path: Path, output_path: Path) -> None:
    with fitz.open(input_path) as image_document:
        payload = image_document.convert_to_pdf()
    with fitz.open("pdf", payload) as pdf_document:
        pdf_document.save(output_path)


def relabel_selected_pages(text: str, source_pages: list[int], source_total: int) -> str:
    result = text
    for extracted_page, source_page in reversed(list(enumerate(source_pages, start=1))):
        marker = f"===== PAGE {extracted_page} / {len(source_pages)} ====="
        result = result.replace(marker, f"===== PAGE {source_page} / {source_total} =====")
    return result


def prepare(
    input_path: Path,
    *,
    slug: str | None = None,
    pages_spec: str | None = None,
    mode: str = "auto",
    language: str = "eng",
    output_root: Path = Path("references/derived"),
    force: bool = False,
    invocation: list[str] | None = None,
) -> dict[str, object]:
    input_path = input_path.resolve()
    if not input_path.is_file():
        raise FileNotFoundError(input_path)
    suffix = input_path.suffix.casefold()
    if suffix not in {".pdf", ".djvu", ".djv"}:
        raise ValueError("reference preparation supports PDF and DjVu inputs")
    if mode not in {"auto", "extract", "ocr"}:
        raise ValueError(f"unknown mode: {mode}")

    source_kind = "pdf" if suffix == ".pdf" else "djvu"
    output_slug = slugify(slug or input_path.stem)
    commands: list[list[str]] = []
    if source_kind == "pdf":
        total_pages = pdf_page_count(input_path)
    else:
        require_commands("djvused", "djvutxt")
        total_pages = djvu_page_count(input_path, commands)
    pages = parse_pages(pages_spec, total_pages)

    hidden_djvu_text: str | None = None
    if source_kind == "pdf":
        usable_text = pdf_has_usable_text(input_path, pages)
    else:
        hidden_djvu_text, usable_text = djvu_text(input_path, pages, total_pages, commands)

    selected_mode = mode
    if mode == "auto":
        selected_mode = "extract" if usable_text else "ocr"
    if mode == "extract" and not usable_text:
        raise RuntimeError("selected pages lack a usable text layer; use --mode ocr")

    text_name = f"{output_slug}.txt" if selected_mode == "extract" else f"{output_slug}.ocr.txt"
    text_output = output_root / "text" / text_name
    metadata_output = text_output.with_name(f"{text_output.stem}.metadata.json")
    ocr_output = output_root / "ocr" / f"{output_slug}.ocr.pdf"
    expected_outputs = [text_output, metadata_output]
    if selected_mode == "ocr":
        expected_outputs.append(ocr_output)
    existing = [path for path in expected_outputs if path.exists()]
    if existing and not force:
        raise FileExistsError(f"output exists (use --force to replace): {existing[0]}")
    if force:
        for path in existing:
            path.unlink()

    djvu_rendered = False
    with tempfile.TemporaryDirectory(prefix="prepare-reference-") as temporary_raw:
        temporary = Path(temporary_raw)
        if selected_mode == "extract":
            if source_kind == "pdf":
                extract_pdf(
                    input_path,
                    text_output,
                    metadata_output=metadata_output,
                    pages_spec=pages_spec,
                    repair_glyphs=True,
                )
            else:
                assert hidden_djvu_text is not None
                write_text_atomic(text_output, hidden_djvu_text)
        else:
            require_commands("ocrmypdf", "tesseract")
            ocr_input = input_path
            ocr_pages_spec = pages_spec
            if source_kind == "djvu":
                require_commands("ddjvu")
                rendered_tiff = temporary / "selected-pages.tiff"
                rendered_pdf = temporary / "selected-pages.pdf"
                command = ["ddjvu", "-format=tiff"]
                if pages_spec is not None:
                    command.append(f"-page={pages_spec}")
                command.extend([str(input_path), str(rendered_tiff)])
                run(command, commands)
                image_document_to_pdf(rendered_tiff, rendered_pdf)
                ocr_input = rendered_pdf
                ocr_pages_spec = None
                djvu_rendered = True

            temporary_ocr = temporary / "output.ocr.pdf"
            command = [
                "ocrmypdf",
                "--output-type",
                "pdf",
                "--rotate-pages",
                "--deskew",
                "--skip-text",
                "--language",
                language,
            ]
            if ocr_pages_spec is not None:
                command.extend(["--pages", ocr_pages_spec])
            command.extend([str(ocr_input), str(temporary_ocr)])
            run(command, commands)
            ocr_output.parent.mkdir(parents=True, exist_ok=True)
            temporary_ocr.replace(ocr_output)

            extract_pdf(
                ocr_output,
                text_output,
                metadata_output=metadata_output,
                pages_spec=None if djvu_rendered else pages_spec,
                repair_glyphs=True,
            )
            if djvu_rendered:
                relabeled = relabel_selected_pages(
                    text_output.read_text(encoding="utf-8"), pages, total_pages
                )
                write_text_atomic(text_output, relabeled)

    extractor_metadata: dict[str, object] = {}
    if metadata_output.is_file():
        extractor_metadata = json.loads(metadata_output.read_text(encoding="utf-8"))
    metadata = {
        **extractor_metadata,
        "schema_version": 1,
        "prepared_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source_original": str(input_path),
        "source_sha256": sha256(input_path),
        "source_kind": source_kind,
        "selected_mode": selected_mode,
        "language": language if selected_mode == "ocr" else None,
        "source_page_count": total_pages,
        "source_pages": pages,
        "output_text": str(text_output),
        "output_ocr_pdf": str(ocr_output) if selected_mode == "ocr" else None,
        "tools": {
            "ocrmypdf": command_version("ocrmypdf") if selected_mode == "ocr" else None,
            "tesseract": command_version("tesseract") if selected_mode == "ocr" else None,
            "djvulibre": command_version("ddjvu") if source_kind == "djvu" else None,
            "pymupdf": fitz.VersionBind,
        },
        "commands": commands,
        "invocation": invocation or ["tools/prepare_reference.py", str(input_path)],
    }
    write_json_atomic(metadata_output, metadata)
    return {
        "source": str(input_path),
        "mode": selected_mode,
        "pages": pages,
        "text": str(text_output),
        "ocr_pdf": str(ocr_output) if selected_mode == "ocr" else None,
        "metadata": str(metadata_output),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract or OCR selected PDF/DjVu pages without modifying the original."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("--slug", help="stable derivative filename slug")
    parser.add_argument("--pages", dest="pages_spec", help="one-indexed pages, e.g. 1-12")
    parser.add_argument("--mode", choices=("auto", "extract", "ocr"), default="auto")
    parser.add_argument("--language", default="eng", help="OCR language expression")
    parser.add_argument("--output-root", type=Path, default=Path("references/derived"))
    parser.add_argument("--force", action="store_true", help="replace exact derivative outputs")
    args = parser.parse_args()

    result = prepare(
        args.input,
        slug=args.slug,
        pages_spec=args.pages_spec,
        mode=args.mode,
        language=args.language,
        output_root=args.output_root,
        force=args.force,
        invocation=["tools/prepare_reference.py", *sys.argv[1:]],
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
