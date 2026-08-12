from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path

from tools.reference_catalog import audit
from tools.reference_lookup import load_catalog, matches
from tools.reference_metadata import refresh_items

TEX = r"""
\documentclass{article}
\title{Finiteness Properties of Rings of Invariants}
\author{Emmy Noether \and David Hilbert}
\subjclass{13A50, 20G05}
\begin{document}
\maketitle
\begin{abstract}
We give conditions under which the ring of invariants of a group action is
finitely generated over the base field.
\end{abstract}
\end{document}
"""


def query(**overrides: object) -> argparse.Namespace:
    defaults = {
        "terms": [],
        "author": None,
        "title": None,
        "keyword": None,
        "doi": None,
        "year": None,
        "kind": None,
        "cited": False,
        "has_derivative": False,
        "has_source": False,
    }
    return argparse.Namespace(**{**defaults, **overrides})


class ReferenceMetadataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.temporary.name)
        self.root = self.repo_root / "references"
        item = self.root / "items/arxiv/1503.01234v2"
        (item / "source").mkdir(parents=True)
        (item / "source/main.tex").write_text(TEX, encoding="utf-8")
        (item / "item.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "id": "arxiv:1503.01234v2",
                    "kind": "arxiv",
                    "key": "1503.01234v2",
                    "item_path": "items/arxiv/1503.01234v2",
                    "checked_at": "2026-01-01T00:00:00+00:00",
                    "resources": {},
                }
            ),
            encoding="utf-8",
        )
        self.metadata_path = item / "item.json"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def describe(self, **kwargs: object) -> dict[str, object]:
        return refresh_items(self.root, self.repo_root, scan_citations=False, **kwargs)

    def item(self) -> dict[str, object]:
        return json.loads(self.metadata_path.read_text(encoding="utf-8"))

    def test_extracts_identity_from_tex_and_stays_auditable(self) -> None:
        result = self.describe()
        self.assertEqual(result["items_written"], 1)
        self.assertEqual(result["catalog"]["described_items"], 1)

        identity = self.item()["bibliographic_identity"]
        self.assertEqual(identity["title"], "Finiteness Properties of Rings of Invariants")
        self.assertEqual(identity["authors"], ["Emmy Noether", "David Hilbert"])
        self.assertEqual(identity["arxiv_id"], "1503.01234v2")
        self.assertEqual(identity["year"], 2015)
        self.assertEqual(identity["msc"], ["13A50", "20G05"])
        self.assertIn("finitely generated", identity["abstract"])

        # item_path stays workspace-relative, so the catalog audit still passes.
        self.assertEqual(audit(self.root), {"status": "ok", "items": 1})
        self.assertIn("Noether", (self.root / "CATALOG.md").read_text(encoding="utf-8"))

    def test_manual_fields_survive_refresh_unless_forced(self) -> None:
        self.describe()
        payload = self.item()
        payload["bibliographic_identity"]["title"] = "Published title"
        payload["metadata_provenance"]["title"] = "manual: checked against the journal version"
        self.metadata_path.write_text(json.dumps(payload), encoding="utf-8")

        self.describe()
        self.assertEqual(self.item()["bibliographic_identity"]["title"], "Published title")

        self.describe(force=True)
        self.assertEqual(
            self.item()["bibliographic_identity"]["title"],
            "Finiteness Properties of Rings of Invariants",
        )

    def test_lookup_matches_by_author_title_and_year(self) -> None:
        self.describe()
        records = load_catalog(self.root)
        self.assertEqual(len(records), 1)

        self.assertTrue(matches(records[0], query(author=["noether"])))
        # Dash style and case are folded away before matching.
        self.assertTrue(matches(records[0], query(title=["rings of invariants"])))
        self.assertTrue(matches(records[0], query(year=(2014, 2016))))
        self.assertTrue(matches(records[0], query(terms=["finiteness"])))
        self.assertFalse(matches(records[0], query(author=["dedekind"])))
        self.assertFalse(matches(records[0], query(year=(2020, 2021))))
        self.assertFalse(matches(records[0], query(kind=["book"])))


if __name__ == "__main__":
    unittest.main()
