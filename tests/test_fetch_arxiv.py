from __future__ import annotations

import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import reference_catalog
from tools.fetch_arxiv import (
    fetch,
    fetch_many,
    install_source,
    normalize_arxiv_id,
    safe_extract,
)


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
            self.assertEqual(
                result["audit"],
                {
                    "status": "ok",
                    "items": 1,
                    "scope": "selected",
                    "hashes_checked": False,
                },
            )

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

    def test_fetch_many_is_sequential_and_catalogs_once(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_raw:
            temporary = Path(temporary_raw)
            calls: list[str] = []

            def downloader(url: str, destination: Path, headers: Path) -> dict[str, object]:
                calls.append(url)
                headers.write_text("HTTP/2 200\n")
                if "/e-print/" in url:
                    destination.write_bytes(b"\\documentclass{article}\n")
                else:
                    destination.write_bytes(b"%PDF-1.4\n%%EOF\n")
                return {}

            root = temporary / "references"
            result = fetch_many(
                ["2099.00001v1", "2099.00002v3"],
                root=root,
                downloader=downloader,
            )

            self.assertEqual(
                calls,
                [
                    "https://arxiv.org/e-print/2099.00001v1",
                    "https://arxiv.org/pdf/2099.00001v1",
                    "https://arxiv.org/e-print/2099.00002v3",
                    "https://arxiv.org/pdf/2099.00002v3",
                ],
            )
            self.assertEqual(len(result["items"]), 2)
            self.assertEqual(
                result["catalog"],
                {
                    "catalog_items": 2,
                    # Both items are described as they are filed, not only in a
                    # later full tools/reference_metadata.py run.
                    "described_items": 2,
                    "external_sources": 0,
                    "path": "CATALOG.json",
                },
            )
            self.assertEqual(
                result["audit"],
                {
                    "status": "ok",
                    "items": 2,
                    "scope": "selected",
                    "hashes_checked": False,
                },
            )
            self.assertTrue((root / "items/arxiv/2099.00001v1/item.json").is_file())
            self.assertTrue((root / "items/arxiv/2099.00002v3/item.json").is_file())

    def test_existing_catalog_update_does_not_scan_or_hash_unrelated_items(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_raw:
            root = Path(temporary_raw) / "references"

            def downloader(url: str, destination: Path, headers: Path) -> dict[str, object]:
                headers.write_text("HTTP/2 200\n")
                if "/e-print/" in url:
                    destination.write_bytes(b"\\documentclass{article}\n")
                else:
                    destination.write_bytes(b"%PDF-1.4\n%%EOF\n")
                return {}

            fetch("2099.00001v1", root=root, downloader=downloader)
            damaged = root / "items/arxiv/2099.00001v1/original/source.tex"
            damaged.write_bytes(b"changed after its recorded hash")

            with patch(
                "tools.reference_catalog.regular_files",
                wraps=reference_catalog.regular_files,
            ) as scans:
                result = fetch("2099.00002v1", root=root, downloader=downloader)

            scanned_paths = [str(call.args[0]) for call in scans.call_args_list]
            self.assertTrue(any("2099.00002v1" in path for path in scanned_paths))
            self.assertFalse(any("2099.00001v1" in path for path in scanned_paths))
            self.assertEqual(result["catalog"]["catalog_items"], 2)

            # The explicit full audit still detects unrelated stored-file damage.
            with self.assertRaisesRegex(RuntimeError, "hash mismatch"):
                reference_catalog.audit(root)

    def test_cached_fetch_reuses_recorded_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_raw:
            root = Path(temporary_raw) / "references"

            def downloader(_url: str, destination: Path, headers: Path) -> dict[str, object]:
                headers.write_text("HTTP/2 200\n")
                destination.write_bytes(b"\\documentclass{article}\n")
                return {}

            fetch(
                "2099.00001v1",
                root=root,
                want_pdf=False,
                downloader=downloader,
            )
            with patch("tools.fetch_arxiv.sha256") as hash_file:
                result = fetch(
                    "2099.00001v1",
                    root=root,
                    want_pdf=False,
                    downloader=downloader,
                )

            hash_file.assert_not_called()
            self.assertEqual(result["resources"]["source"]["status"], "cached")

    def test_fetch_many_validates_entire_batch_before_downloading(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_raw:
            calls: list[str] = []

            def downloader(url: str, _destination: Path, _headers: Path) -> dict[str, object]:
                calls.append(url)
                return {}

            with self.assertRaises(ValueError):
                fetch_many(
                    ["2099.00001v1", "not-an-arxiv-id"],
                    root=Path(temporary_raw) / "references",
                    downloader=downloader,
                )
            self.assertEqual(calls, [])

    def test_failed_fetch_leaves_no_orphan_item(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_raw:
            root = Path(temporary_raw) / "references"

            def downloader(url: str, destination: Path, headers: Path) -> dict[str, object]:
                if "/e-print/" in url:
                    headers.write_text("HTTP/2 200\n")
                    destination.write_bytes(b"\\documentclass{article}\npartial\n")
                    return {}
                raise RuntimeError("simulated download failure")

            with self.assertRaisesRegex(RuntimeError, "simulated download failure"):
                fetch("2099.00001v1", root=root, downloader=downloader)

            self.assertFalse((root / "items/arxiv/2099.00001v1").exists())

    def test_failed_later_batch_item_keeps_earlier_items_catalogable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_raw:
            root = Path(temporary_raw) / "references"

            def downloader(url: str, destination: Path, headers: Path) -> dict[str, object]:
                if "2099.00002v1" in url:
                    raise RuntimeError("simulated later failure")
                headers.write_text("HTTP/2 200\n")
                if "/e-print/" in url:
                    destination.write_bytes(b"\\documentclass{article}\n")
                else:
                    destination.write_bytes(b"%PDF-1.4\n%%EOF\n")
                return {}

            with self.assertRaisesRegex(RuntimeError, "simulated later failure"):
                fetch_many(
                    ["2099.00001v1", "2099.00002v1"],
                    root=root,
                    downloader=downloader,
                )

            self.assertTrue((root / "items/arxiv/2099.00001v1/item.json").is_file())
            self.assertFalse((root / "items/arxiv/2099.00002v1").exists())
            catalog = json.loads((root / "CATALOG.json").read_text(encoding="utf-8"))
            self.assertEqual([item["id"] for item in catalog["items"]], ["arxiv:2099.00001v1"])

    def test_failed_force_refresh_preserves_existing_item(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_raw:
            root = Path(temporary_raw) / "references"

            def good_downloader(
                url: str, destination: Path, headers: Path
            ) -> dict[str, object]:
                headers.write_text("HTTP/2 200\n")
                if "/e-print/" in url:
                    destination.write_bytes(b"\\documentclass{article}\noriginal\n")
                else:
                    destination.write_bytes(b"%PDF-1.4\noriginal\n%%EOF\n")
                return {}

            fetch("2099.00001v1", root=root, downloader=good_downloader)
            item = root / "items/arxiv/2099.00001v1"
            metadata_before = (item / "item.json").read_bytes()
            source_before = (item / "original/source.tex").read_bytes()

            def failing_downloader(
                url: str, destination: Path, headers: Path
            ) -> dict[str, object]:
                if "/e-print/" in url:
                    headers.write_text("HTTP/2 200\n")
                    destination.write_bytes(b"\\documentclass{article}\nreplacement\n")
                    return {}
                raise RuntimeError("simulated force failure")

            with self.assertRaisesRegex(RuntimeError, "simulated force failure"):
                fetch(
                    "2099.00001v1",
                    root=root,
                    force=True,
                    downloader=failing_downloader,
                )

            self.assertEqual((item / "item.json").read_bytes(), metadata_before)
            self.assertEqual((item / "original/source.tex").read_bytes(), source_before)

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
