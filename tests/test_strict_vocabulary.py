from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.strict_vocabulary import (
    build_corpus,
    load_decision_policy,
    load_manifest,
    render_markdown,
    scan_manuscript,
)


FILLER = (
    "The module and the category are considered in this paper. "
    "We record the result and the proof for the reader. "
) * 24


def add_source(root: Path, key: str, sentence: str) -> None:
    source = root / "references" / "items" / "arxiv" / key / "source"
    source.mkdir(parents=True)
    (source / "main.tex").write_text(
        "\\begin{document}\n" + sentence + " " + FILLER
        + "\n\\end{document}\n",
        encoding="utf-8",
    )


class StrictVocabularyTests(unittest.TestCase):
    def test_owner_repeated_comparison_and_violations_are_distinguished(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            out = root / "strict"
            add_source(root, "owner", "An ownerword occurs.")
            add_source(root, "comparison-a", "A sharedword and singleword occur.")
            add_source(root, "comparison-b", "A sharedword occurs.")
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps({
                "name": "test",
                "comparison_min_papers": 2,
                "require_distinct_comparison_authors": True,
                "papers": [
                    {"group": "owner", "key": "owner", "title": "Owner",
                     "authors": ["Owner Author"]},
                    {"group": "comparison", "key": "comparison-a",
                     "title": "A", "authors": ["First Author"]},
                    {"group": "comparison", "key": "comparison-b",
                     "title": "B", "authors": ["Second Author"]},
                ],
            }), encoding="utf-8")
            manifest = load_manifest(manifest_path)
            corpus = build_corpus(root, manifest, out)

            manuscript = root / "paper" / "main.tex"
            manuscript.parent.mkdir()
            manuscript.write_text(
                "\\begin{document}\nOwnerword sharedword singleword absentword.\n"
                "\\end{document}\n",
                encoding="utf-8",
            )
            report = scan_manuscript(root, [manuscript], corpus, 2)

            self.assertIn(
                "ownerword", {row["text"] for row in report["categories"]["owner"]}
            )
            self.assertIn(
                "sharedword",
                {row["text"] for row in report["categories"]["comparison_repeated"]},
            )
            self.assertIn(
                "singleword",
                {row["text"] for row in report["categories"]["comparison_single"]},
            )
            self.assertIn(
                "absentword",
                {row["text"] for row in report["categories"]["unattested"]},
            )
            rendered = render_markdown(report, corpus["summary"])
            self.assertIn("editorial discussion instrument", rendered)
            self.assertIn("Only one comparison paper", rendered)

    def test_owner_decisions_are_applied_without_overriding_guards(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            add_source(root, "owner", "An ordinary source occurs.")
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps({
                "papers": [
                    {"group": "owner", "key": "owner", "title": "Owner",
                     "authors": ["Owner Author"]},
                ],
            }), encoding="utf-8")
            decision_path = root / "decisions.json"
            decision_path.write_text(json.dumps({
                "approved": [{"terms": ["contour"]}],
                "conditional": [{"term": "branch"}],
                "not_approved": [{"term": "arm"}],
                "non_prose_exact_forms": [
                    {"term": "BGRS", "reason": "bibliographic acronym"}
                ],
            }), encoding="utf-8")
            corpus = build_corpus(
                root, load_manifest(manifest_path), root / "strict"
            )
            manuscript = root / "paper" / "main.tex"
            manuscript.parent.mkdir()
            manuscript.write_text(
                "\\begin{document}\nContours branch arms BGRS.\n\\end{document}\n",
                encoding="utf-8",
            )
            report = scan_manuscript(
                root, [manuscript], corpus, 2,
                decisions=load_decision_policy(decision_path),
            )
            self.assertEqual(
                {row["text"] for row in report["categories"]["decision_approved"]},
                {"contours"},
            )
            self.assertEqual(
                {row["text"] for row in report["categories"]["conditional"]},
                {"branch"},
            )
            self.assertIn(
                "arms", {row["text"] for row in report["categories"]["unattested"]}
            )
            self.assertEqual(
                {row["text"] for row in report["categories"]["non_prose"]},
                {"bgrs"},
            )
            self.assertEqual(
                report["categories"]["non_prose"][0]["non_prose_reason"],
                "bibliographic acronym",
            )

    def test_repeated_comparison_authors_are_rejected_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest_path = Path(temporary) / "manifest.json"
            manifest_path.write_text(json.dumps({
                "require_distinct_comparison_authors": True,
                "papers": [
                    {"group": "comparison", "key": "a", "title": "A",
                     "authors": ["Repeated Author"]},
                    {"group": "comparison", "key": "b", "title": "B",
                     "authors": ["Repeated Author"]},
                ],
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "must be distinct"):
                load_manifest(manifest_path)


if __name__ == "__main__":
    unittest.main()
