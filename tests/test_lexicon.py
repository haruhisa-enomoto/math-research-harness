from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import lexicon

# A corpus file joins the lexicon only above `MIN_FILE_WORDS` prose words, so
# the fixture repeats an ordinary English paragraph to clear that threshold.
FILLER = (
    "In this section we collect the elementary facts that will be needed later "
    "on, and we fix the conventions that are used in the rest of the paper for "
    "resolutions of modules and for the various dimensions attached to them. "
) * 8

FIELD_TEX = (
    r"""
\documentclass{amsart}
\begin{document}
\section{Resolutions}
% a comment that must not become prose
Let $A$ be a ring and let $\mod A$ denote the category of finitely generated
left modules over it. We say that a module is reflexive when the canonical
evaluation map to its double dual is an isomorphism, and we recall that the
projective dimension of a module is the length of its shortest projective
resolution.
"""
    + FILLER
    + r"""
\begin{equation}
\operatorname{pd} M = \flaggableinsidemath
\end{equation}
\end{document}
"""
)

AUTHOR_TEX = FIELD_TEX.replace(r"\section{Resolutions}", r"\section{Lattices}").replace(
    "reflexive", "coreflexive"
)


def texts(rows: list[dict]) -> set[str]:
    return {row["text"] for row in rows}


def row(rows: list[dict], text: str) -> dict:
    return next(r for r in rows if r["text"] == text)


class LexiconTest(unittest.TestCase):
    def setUp(self) -> None:
        # The author tier is off by default in the template; these tests
        # configure a surname the way a real project would.
        patcher = mock.patch.object(lexicon, "OWNER_SURNAME", "Germain")
        patcher.start()
        self.addCleanup(patcher.stop)

        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        items = self.root / "references" / "items"
        for key, text in (("0001.00001", FIELD_TEX), ("0002.00002v2", AUTHOR_TEX)):
            source = items / "arxiv" / key / "source"
            source.mkdir(parents=True)
            (source / "main.tex").write_text(text, encoding="utf-8")
        (self.root / "references" / "CATALOG.json").write_text(
            json.dumps(
                {
                    "items": [
                        {
                            "path": "references/items/arxiv/0001.00001",
                            "bibliographic_identity": {"authors": ["Emmy Noether"]},
                        },
                        {
                            "path": "references/items/arxiv/0002.00002v2",
                            "bibliographic_identity": {"authors": ["Sophie Germain"]},
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        self.out = self.root / "paper" / "vocab"
        self.out.mkdir(parents=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_author_tier_comes_from_the_catalog(self) -> None:
        self.assertEqual(lexicon.owner_items(self.root), {"0002.00002v2"})
        tiers = {key: tier for key, tier, _ in lexicon.corpus_items(self.root)}
        self.assertEqual(tiers, {"0001.00001": "field", "0002.00002v2": "owner"})

    def test_author_tier_is_empty_without_a_catalog(self) -> None:
        (self.root / "references" / "CATALOG.json").unlink()
        self.assertEqual(lexicon.owner_items(self.root), set())
        tiers = {tier for _, tier, _ in lexicon.corpus_items(self.root)}
        self.assertEqual(tiers, {"field"})

    def test_author_tier_is_empty_without_a_configured_surname(self) -> None:
        with mock.patch.object(lexicon, "OWNER_SURNAME", ""):
            self.assertEqual(lexicon.owner_items(self.root), set())
            tiers = {tier for _, tier, _ in lexicon.corpus_items(self.root)}
            self.assertEqual(tiers, {"field"})

    def test_prose_extraction_drops_math_and_comments_and_keeps_line_numbers(self) -> None:
        prose = lexicon.strip_tex(FIELD_TEX)
        found = lexicon.tokens(prose)
        words = {word for word, _ in found}
        self.assertIn("reflexive", words)
        self.assertNotIn("flaggableinsidemath", words)
        self.assertNotIn("comment", words)
        line = next(n for word, n in found if word == "reflexive")
        self.assertIn("reflexive", FIELD_TEX.splitlines()[line - 1])

    def test_check_flags_only_the_unattested_manuscript_word(self) -> None:
        summary = lexicon.build(self.root, self.out)
        self.assertEqual(summary["papers"], 2)
        self.assertEqual(summary["owner_papers"], 1)

        manuscript = self.root / "paper" / "draft" / "main.tex"
        manuscript.parent.mkdir(parents=True)
        manuscript.write_text(
            "A reflexive module is wobblesome and snork-preserving.\n",
            encoding="utf-8",
        )
        result = lexicon.check(self.root, self.out, [manuscript], rare_max=2)

        flagged = result["unattested_words"]
        self.assertIn("wobblesome", texts(flagged))
        self.assertNotIn("reflexive", texts(flagged))
        self.assertEqual(row(flagged, "snork-preserving")["kind"], "compound")
        self.assertEqual(
            row(flagged, "wobblesome")["where"], ["paper/draft/main.tex:1"]
        )

    def test_author_absent_section_separates_the_two_tiers(self) -> None:
        lexicon.build(self.root, self.out)
        manuscript = self.root / "paper" / "draft" / "main.tex"
        manuscript.parent.mkdir(parents=True)
        manuscript.write_text("A reflexive coreflexive module.\n", encoding="utf-8")
        result = lexicon.check(self.root, self.out, [manuscript], rare_max=2)

        absent = texts(result["owner_absent_words"])
        self.assertIn("reflexive", absent)
        self.assertNotIn("coreflexive", absent)

    def test_check_keeps_an_absolute_path_outside_the_repository(self) -> None:
        lexicon.build(self.root, self.out)
        with tempfile.TemporaryDirectory() as elsewhere:
            manuscript = Path(elsewhere) / "main.tex"
            manuscript.write_text("A wobblesome module.\n", encoding="utf-8")
            result = lexicon.check(self.root, self.out, [manuscript], rare_max=2)
        self.assertEqual(
            row(result["unattested_words"], "wobblesome")["where"],
            [f"{manuscript}:1"],
        )


if __name__ == "__main__":
    unittest.main()
