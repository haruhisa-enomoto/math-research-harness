from __future__ import annotations

import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.fetch_arxiv import install_source
from tools.fetch_hexagon import fetch, normalize_hexagon_id

TEX = b"\\documentclass{article}\n\\title{From TeX}\n\\begin{document}\nTest, see doi:10.1000/cited.elsewhere\n\\end{document}\n"
PDF = b"%PDF-1.4\n%%EOF\n"


def zipped(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def work_record(version_id: str, *, pdf: bytes = PDF, tex: bytes = TEX) -> dict[str, object]:
    identifier = version_id.split("v")[0]
    return {
        "work": {
            "identifier": identifier,
            "versionId": version_id,
            "versionNumber": int(version_id.split("v")[1]),
            "versionCreatedAt": "2099-10-20 14:24:16",
            "publishedAt": "2099-10-20T04:54:55.500Z",
            "title": "Determinants  over\nfinite fields",
            "abstract": "We prove a thing.",
            "status": "published",
            "authorshipMode": "mixed",
            "humanUnderstanding": "some",
            "provenance": "Text declaration: A mix of human-written and AI-generated.",
            "arxivId": None,
            "doi": None,
            "license": "CC BY 4.0",
            "withdrawnAt": None,
            "withdrawalNote": None,
            "formalizations": [],
            "tags": ["determinant"],
            "mscCodes": ["11T06", "15A15"],
            "authors": [{"name": "Ann Author"}, {"name": "Bo Writer"}],
            "files": [
                {
                    "kind": "paper",
                    "filename": f"{version_id}.pdf",
                    "sha256": hashlib.sha256(pdf).hexdigest(),
                },
                {
                    "kind": "source",
                    "filename": "main.tex",
                    "sha256": hashlib.sha256(tex).hexdigest(),
                },
            ],
        }
    }


class FakeHexagon:
    def __init__(self, version_id: str, *, pdf: bytes = PDF, archive: bytes | None = None) -> None:
        self.version_id = version_id
        self.pdf = pdf
        self.archive = archive if archive is not None else zipped({"main.tex": TEX})
        self.calls: list[str] = []

    def __call__(self, url: str, destination: Path, headers: Path) -> dict[str, object]:
        self.calls.append(url)
        headers.write_text("HTTP/2 200\n")
        if "/api/v1/works/" in url:
            destination.write_text(json.dumps(work_record(self.version_id)), encoding="utf-8")
        elif "/api/bibtex/" in url:
            destination.write_text(f"@misc{{hexagon:{self.version_id},\n}}\n", encoding="utf-8")
        elif "/src/" in url:
            destination.write_bytes(self.archive)
        elif "/pdf/" in url:
            destination.write_bytes(self.pdf)
        else:
            raise AssertionError(url)
        return {"request_url": url, "effective_url": url, "http_status": "200", "headers": {}}


class FetchHexagonTests(unittest.TestCase):
    def test_normalize_identifier_prefix_and_record_urls(self) -> None:
        self.assertEqual(normalize_hexagon_id("hexagon:2099.00392v2"), "2099.00392v2")
        self.assertEqual(normalize_hexagon_id("2099.00392"), "2099.00392")
        for url in (
            "https://hexagonmath.org/2099.00392v2",
            "https://hexagonmath.org/abs/2099.00392v2",
            "https://hexagonmath.org/pdf/2099.00392v2",
            "https://hexagonmath.org/api/v1/works/2099.00392v2/source",
        ):
            self.assertEqual(normalize_hexagon_id(url), "2099.00392v2")
        for bad in ("https://arxiv.org/abs/2099.00392v2", "https://hexagonmath.org/about", "2099.0039v1"):
            with self.assertRaises(ValueError):
                normalize_hexagon_id(bad)

    def test_fetch_files_record_source_pdf_identity_and_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_raw:
            root = Path(temporary_raw) / "references"
            fake = FakeHexagon("2099.00392v2")
            result = fetch("hexagon:2099.00392v2", root=root, downloader=fake)

            item = root / "items/hexagon/2099.00392v2"
            self.assertEqual(len(fake.calls), 4)
            for name in ("work.json", "citation.bib", "source.zip", "paper.pdf"):
                self.assertTrue((item / "original" / name).is_file(), name)
            self.assertTrue((item / "source/main.tex").is_file())
            self.assertEqual(result["source_check"], {"matched": ["main.tex"], "absent_from_archive": []})
            self.assertEqual(result["audit"]["status"], "ok")
            self.assertTrue(any("human understanding 'some'" in warning for warning in result["warnings"]))

            metadata = json.loads((item / "item.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["id"], "hexagon:2099.00392v2")
            self.assertEqual(metadata["hexagon"]["authorship_mode"], "mixed")
            self.assertTrue(metadata["resources"]["pdf"]["published_sha256_checked"])
            identity = metadata["bibliographic_identity"]
            # The API record wins over the TeX title.
            self.assertEqual(identity["title"], "Determinants over finite fields")
            self.assertEqual(identity["authors"], ["Ann Author", "Bo Writer"])
            self.assertEqual(identity["year"], 2099)
            self.assertEqual(identity["msc"], ["11T06", "15A15"])
            self.assertEqual(identity["persistent_identifier"], "hexagon:2099.00392v2")
            self.assertEqual(identity["exact_version"], "v2")
            self.assertIsNone(identity["arxiv_id"])
            # A DOI inside the TeX belongs to a cited work, not to this record.
            self.assertIsNone(identity["doi"])
            self.assertTrue(metadata["metadata_provenance"]["title"].startswith("hexagon-api:"))

            catalog = json.loads((root / "CATALOG.json").read_text(encoding="utf-8"))
            (record,) = catalog["items"]
            self.assertEqual(record["kind"], "hexagon")
            self.assertEqual(record["hexagon"]["human_understanding"], "some")

            fake.calls.clear()
            fetch("2099.00392v2", root=root, downloader=fake)
            self.assertEqual(fake.calls, [])

    def test_unversioned_request_is_filed_under_current_version(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_raw:
            root = Path(temporary_raw) / "references"
            fake = FakeHexagon("2099.00392v3")
            result = fetch("2099.00392", root=root, want_pdf=False, downloader=fake)
            self.assertEqual(result["hexagon_id"], "2099.00392v3")
            self.assertTrue((root / "items/hexagon/2099.00392v3/item.json").is_file())
            self.assertIn("resolved to current version", result["warnings"][0])
            # The record was downloaded once and reused for the item.
            self.assertEqual(sum("/api/v1/works/" in call for call in fake.calls), 1)

    def test_digest_mismatch_aborts_without_leaving_an_item(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_raw:
            root = Path(temporary_raw) / "references"
            fake = FakeHexagon("2099.00392v2", pdf=b"%PDF-1.4\ntampered\n")
            with self.assertRaisesRegex(RuntimeError, "published SHA-256"):
                fetch("2099.00392v2", root=root, downloader=fake)
            self.assertFalse((root / "items/hexagon/2099.00392v2").exists())

    def test_zip_source_rejects_unsafe_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_raw:
            temporary = Path(temporary_raw)
            download = temporary / "source.download"
            download.write_bytes(zipped({"../escape.tex": TEX}))
            with self.assertRaisesRegex(RuntimeError, "unsafe path"):
                install_source(download, temporary / "original", temporary / "source")
            self.assertFalse((temporary / "escape.tex").exists())


if __name__ == "__main__":
    unittest.main()
