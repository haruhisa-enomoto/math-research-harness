from __future__ import annotations

import errno
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import fitz

from tools.extract_pdf_text import extract_pdf
from tools.prepare_reference import (
    prepare,
    relabel_selected_pages,
    replace_with_cross_device_fallback,
)
from tools.reference_utils import parse_pages
from tools.render_pdf_pages import render_pages


class PrepareReferenceTests(unittest.TestCase):
    def make_pdf(self, path: Path) -> None:
        document = fitz.open()
        page = document.new_page()
        page.insert_text(
            (72, 72),
            "This fictional research document has enough searchable text for native extraction.",
        )
        document.save(path)
        document.close()

    def test_page_parser_rejects_ambiguous_ranges(self) -> None:
        self.assertEqual(parse_pages("1,3-5", 6), [1, 3, 4, 5])
        with self.assertRaises(ValueError):
            parse_pages("4-2", 6)
        with self.assertRaises(ValueError):
            parse_pages("1,1", 6)

    def test_auto_mode_extracts_pdf_text_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_raw:
            temporary = Path(temporary_raw)
            pdf = temporary / "paper.pdf"
            self.make_pdf(pdf)
            result = prepare(pdf, slug="sample-paper", output_root=temporary / "derived")

            self.assertEqual(result["mode"], "extract")
            text = Path(result["text"]).read_text(encoding="utf-8")
            self.assertIn("===== PAGE 1 / 1 =====", text)
            metadata = json.loads(Path(result["metadata"]).read_text(encoding="utf-8"))
            self.assertEqual(metadata["source_pages"], [1])
            self.assertIsNone(metadata["output_ocr_pdf"])
            self.assertEqual(len(metadata["source_sha256"]), 64)

    def test_low_level_extractor_always_writes_default_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_raw:
            temporary = Path(temporary_raw)
            pdf = temporary / "paper.pdf"
            text_output = temporary / "paper-text.txt"
            metadata_output = temporary / "paper-text.metadata.json"
            self.make_pdf(pdf)

            metadata = extract_pdf(pdf, text_output)

            self.assertTrue(text_output.is_file())
            self.assertTrue(metadata_output.is_file())
            self.assertEqual(metadata["metadata_output"], str(metadata_output))
            persisted = json.loads(metadata_output.read_text(encoding="utf-8"))
            self.assertEqual(persisted["source_sha256"], metadata["source_sha256"])

    def test_page_renderer_writes_selected_png(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_raw:
            temporary = Path(temporary_raw)
            pdf = temporary / "paper.pdf"
            self.make_pdf(pdf)
            outputs = render_pages(pdf, "1", temporary / "pages", dpi=72)
            self.assertEqual(len(outputs), 1)
            self.assertTrue(outputs[0].is_file())

    def test_relabel_selected_djvu_pages(self) -> None:
        text = "===== PAGE 1 / 2 =====\nfirst\n\n===== PAGE 2 / 2 =====\nsecond\n"
        relabeled = relabel_selected_pages(text, [7, 11], 20)
        self.assertIn("===== PAGE 7 / 20 =====", relabeled)
        self.assertIn("===== PAGE 11 / 20 =====", relabeled)

    def test_cross_device_replace_falls_back_to_copy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_raw:
            temporary = Path(temporary_raw)
            source = temporary / "source.pdf"
            target = temporary / "derived" / "target.pdf"
            source.write_bytes(b"reference bytes")
            target.parent.mkdir()

            with mock.patch.object(
                Path,
                "replace",
                side_effect=OSError(errno.EXDEV, "cross-device link"),
            ):
                replace_with_cross_device_fallback(source, target)

            self.assertFalse(source.exists())
            self.assertEqual(target.read_bytes(), b"reference bytes")

    @unittest.skipUnless(
        all(shutil.which(command) for command in ("ocrmypdf", "tesseract")),
        "OCR integration tools are not installed",
    )
    def test_ocr_mode_creates_searchable_derivatives(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_raw:
            temporary = Path(temporary_raw)
            born_digital = fitz.open()
            page = born_digital.new_page(width=600, height=800)
            page.insert_text(
                (72, 120),
                "Scanned fictional theorem text for the integration test.",
                fontsize=16,
            )
            pixmap = page.get_pixmap(dpi=200, alpha=False)

            scan = fitz.open()
            scan_page = scan.new_page(width=600, height=800)
            scan_page.insert_image(scan_page.rect, pixmap=pixmap)
            pdf = temporary / "scan.pdf"
            scan.save(pdf)
            scan.close()
            born_digital.close()

            result = prepare(
                pdf,
                slug="scanned-paper",
                mode="ocr",
                output_root=temporary / "derived",
            )
            self.assertEqual(result["mode"], "ocr")
            self.assertTrue(Path(result["ocr_pdf"]).is_file())
            self.assertTrue(Path(result["text"]).is_file())

    @unittest.skipUnless(
        all(
            shutil.which(command)
            for command in (
                "c44",
                "djvused",
                "djvutxt",
                "ddjvu",
                "ocrmypdf",
                "tesseract",
            )
        ),
        "DjVu and OCR integration tools are not installed",
    )
    def test_djvu_mode_renders_ocrs_and_preserves_source_page_map(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_raw:
            temporary = Path(temporary_raw)
            document = fitz.open()
            page = document.new_page(width=600, height=800)
            page.insert_text((72, 120), "Fictional scanned DjVu research page.", fontsize=18)
            pixmap = page.get_pixmap(dpi=200, colorspace=fitz.csGRAY, alpha=False)
            pgm = temporary / "page.pgm"
            pixmap.save(pgm)
            document.close()

            djvu = temporary / "source.djvu"
            subprocess.run(["c44", str(pgm), str(djvu)], check=True)
            result = prepare(
                djvu,
                slug="djvu-source",
                mode="ocr",
                output_root=temporary / "derived",
            )
            metadata = json.loads(Path(result["metadata"]).read_text(encoding="utf-8"))
            self.assertEqual(metadata["source_kind"], "djvu")
            self.assertEqual(metadata["source_pages"], [1])
            self.assertTrue(Path(result["text"]).is_file())


if __name__ == "__main__":
    unittest.main()
