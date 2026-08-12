from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path

from tools.reference_lookup import (
    fold,
    format_record,
    grep_workspace,
    load_catalog,
    matches,
    parse_years,
    sort_key,
)


def query(**overrides: object) -> argparse.Namespace:
    defaults: dict[str, object] = {
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
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


PAPER = {
    "id": "paper:noether-rings-of-invariants",
    "kind": "paper",
    "key": "noether-rings-of-invariants",
    "path": "references/items/papers/noether-rings-of-invariants",
    "source_file_count": 3,
    "citation_count": 12,
    "derivatives": [],
    "search_text": "rings of invariants noether-rings-of-invariants",
    "bibliographic_identity": {
        "title": "Rings of invariants",
        "authors": [],
        "year": None,
        "keywords": [],
        "msc": [],
    },
}
ARXIV = {
    "id": "arxiv:1509.06942",
    "kind": "arxiv",
    "key": "1509.06942",
    "path": "references/items/arxiv/1509.06942",
    "source_file_count": 4,
    "citation_count": 0,
    "derivatives": ["references/derived/text/erdos.txt"],
    "search_text": "extremal properties of finite lattices paul erdős",
    "bibliographic_identity": {
        "title": "Extremal Properties of Finite Lattices",
        "authors": ["Paul Erdős"],
        "year": 2015,
        "doi": "10.1007/s00026-016-0330-0",
        "keywords": ["finite lattices"],
        "msc": ["06A07"],
    },
}


class MatchingTests(unittest.TestCase):
    def test_fold_ignores_case_accents_and_dash_style(self) -> None:
        self.assertEqual(fold("Riemann--Roch"), "riemann-roch")
        self.assertEqual(fold("Erdős"), "erdos")

    def test_author_search_tolerates_accents_and_falls_back_to_the_key(self) -> None:
        self.assertTrue(matches(ARXIV, query(author=["erdos"])))
        self.assertTrue(matches(PAPER, query(author=["noether"])))
        self.assertFalse(matches(ARXIV, query(author=["noether"])))

    def test_title_year_keyword_and_doi_filters(self) -> None:
        self.assertTrue(matches(ARXIV, query(title=["extremal"], year=(2010, 2020))))
        self.assertFalse(matches(ARXIV, query(title=["extremal"], year=(2016, 2020))))
        self.assertTrue(matches(ARXIV, query(keyword=["06A07"])))
        self.assertTrue(matches(ARXIV, query(doi="s00026")))
        self.assertFalse(matches(PAPER, query(year=(2000, 2020))))

    def test_availability_and_kind_filters(self) -> None:
        self.assertTrue(matches(PAPER, query(cited=True)))
        self.assertFalse(matches(ARXIV, query(cited=True)))
        self.assertTrue(matches(ARXIV, query(has_derivative=True)))
        self.assertFalse(matches(PAPER, query(has_derivative=True)))
        self.assertTrue(matches(ARXIV, query(kind=["arxiv"])))
        self.assertFalse(matches(ARXIV, query(kind=["paper", "book"])))

    def test_free_text_terms_are_conjunctive(self) -> None:
        self.assertTrue(matches(ARXIV, query(terms=["extremal", "lattices"])))
        self.assertFalse(matches(ARXIV, query(terms=["extremal", "cohomology"])))

    def test_sorting_is_by_surname_then_recency(self) -> None:
        self.assertEqual(
            [record["id"] for record in sorted([ARXIV, PAPER], key=sort_key)],
            ["arxiv:1509.06942", "paper:noether-rings-of-invariants"],
        )

    def test_parse_years_accepts_a_point_or_a_range(self) -> None:
        self.assertEqual(parse_years("2019"), (2019, 2019))
        self.assertEqual(parse_years("2015-2022"), (2015, 2022))
        with self.assertRaises(SystemExit):
            parse_years("recent")

    def test_format_record_shows_identity_and_location(self) -> None:
        rendered = format_record(ARXIV, verbose=False)
        self.assertIn("Paul Erdős (2015)", rendered)
        self.assertIn("references/items/arxiv/1509.06942", rendered)
        self.assertIn("doi:10.1007/s00026-016-0330-0", rendered)


class WorkspaceQueryTests(unittest.TestCase):
    def test_load_catalog_merges_items_and_external_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "CATALOG.json").write_text(
                json.dumps({"items": [PAPER], "external_sources": [{"id": "external:x", "kind": "external"}]}),
                encoding="utf-8",
            )
            records = load_catalog(root)
        self.assertEqual([record["id"] for record in records], ["paper:noether-rings-of-invariants", "external:x"])

    def test_missing_catalog_is_reported_not_crashed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(SystemExit):
                load_catalog(Path(temporary))

    def test_grep_searches_extracted_text_and_tex_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "derived" / "text").mkdir(parents=True)
            (root / "derived" / "text" / "sample.txt").write_text(
                "first line\nfinitely generated modules appear here\n", encoding="utf-8"
            )
            (root / "items" / "arxiv" / "1234.5678" / "source").mkdir(parents=True)
            (root / "items" / "arxiv" / "1234.5678" / "source" / "main.tex").write_text(
                "\\section{Finitely generated modules}\n", encoding="utf-8"
            )

            hits = grep_workspace(root, "finitely generated", limit=10)

        self.assertEqual(len(hits), 2)
        self.assertEqual(hits[0]["line"], 2)
        self.assertTrue(hits[1]["path"].endswith("main.tex"))


if __name__ == "__main__":
    unittest.main()
