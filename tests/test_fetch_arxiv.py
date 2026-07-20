from __future__ import annotations

import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path

from tools.fetch_arxiv import fetch, install_source, normalize_arxiv_id, safe_extract


class FetchArxivTests(unittest.TestCase):
    def test_normalize_identifier_or_official_url(self) -> None:
        self.assertEqual(normalize_arxiv_id("arXiv:2099.00001v2"), "2099.00001v2")
        self.assertEqual(
            normalize_arxiv_id("https://arxiv.org/pdf/math/0000000v1.pdf"),
            "math/0000000v1",
        )
        with self.assertRaises(ValueError):
            normalize_arxiv_id("https://example.com/abs/2099.00001")

    def test_fetch_files_source_pdf_metadata_and_catalog_without_network(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_raw:
            temporary = Path(temporary_raw)
            root = temporary / "references"
            source_archive = temporary / "source.tar.gz"
            with tarfile.open(source_archive, "w:gz") as archive:
                content = b"\\documentclass{article}\n\\begin{document}\nTest\\end{document}\n"
                member = tarfile.TarInfo("paper/main.tex")
                member.size = len(content)
                archive.addfile(member, io.BytesIO(content))

            calls: list[str] = []

            def downloader(url: str, destination: Path, headers: Path) -> dict[str, object]:
                calls.append(url)
                headers.write_text("HTTP/2 200\ncontent-type: application/octet-stream\n")
                if "/e-print/" in url:
                    destination.write_bytes(source_archive.read_bytes())
                else:
                    destination.write_bytes(b"%PDF-1.4\n%%EOF\n")
                return {
                    "request_url": url,
                    "effective_url": url,
                    "http_status": "200",
                    "headers": {},
                }

            result = fetch("2099.00001v2", root=root, downloader=downloader)
            item = root / "items/arxiv/2099.00001v2"
            self.assertEqual(len(calls), 2)
            self.assertTrue((item / "original/source.tar.gz").is_file())
            self.assertTrue((item / "original/paper.pdf").is_file())
            self.assertTrue((item / "source/paper/main.tex").is_file())
            self.assertEqual(result["main_tex_candidates"], ["paper/main.tex"])
            self.assertEqual(result["audit"], {"status": "ok", "items": 1})

            metadata = json.loads((item / "item.json").read_text(encoding="utf-8"))
            self.assertTrue(metadata["versioned"])
            self.assertEqual(metadata["resources"]["source"]["status"], "downloaded")
            self.assertTrue((root / "CATALOG.json").is_file())

            calls.clear()
            fetch("2099.00001v2", root=root, downloader=downloader)
            self.assertEqual(calls, [])

    def test_unversioned_item_is_explicitly_hash_pinned(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_raw:
            temporary = Path(temporary_raw)

            def downloader(_url: str, destination: Path, headers: Path) -> dict[str, object]:
                headers.write_text("HTTP/2 200\n")
                destination.write_bytes(b"\\documentclass{article}\n")
                return {}

            result = fetch(
                "2099.00001",
                root=temporary / "references",
                want_pdf=False,
                downloader=downloader,
            )
            self.assertIn("unversioned", str(result["version_warning"]))

    def test_archive_path_traversal_and_links_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_raw:
            temporary = Path(temporary_raw)
            archive_path = temporary / "bad.tar"
            with tarfile.open(archive_path, "w") as archive:
                content = b"bad"
                member = tarfile.TarInfo("../outside.tex")
                member.size = len(content)
                archive.addfile(member, io.BytesIO(content))
            with self.assertRaises(RuntimeError):
                install_source(archive_path, temporary / "original", temporary / "source")

            link_archive = temporary / "link.tar"
            with tarfile.open(link_archive, "w") as archive:
                link = tarfile.TarInfo("paper/link.tex")
                link.type = tarfile.SYMTYPE
                link.linkname = "../../outside"
                archive.addfile(link)
            with tarfile.open(link_archive) as archive:
                with self.assertRaises(RuntimeError):
                    safe_extract(archive, temporary / "link-source")


if __name__ == "__main__":
    unittest.main()
