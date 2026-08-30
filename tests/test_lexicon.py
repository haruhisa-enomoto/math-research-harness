from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.lexicon import (
    author_key,
    build,
    check,
    clean_author_names,
    load_lexicon,
    main,
    render_markdown,
    resolve_report_paths,
)


FILLER = (
    "The module and the category are considered in this paper. "
    "We record the result and the proof for the reader. "
) * 24


def add_paper(
    root: Path,
    key: str,
    authors: list[str],
    sentence: str,
) -> None:
    item = root / "references" / "items" / "arxiv" / key
    source = item / "source"
    source.mkdir(parents=True)
    (item / "item.json").write_text(
        json.dumps({"bibliographic_identity": {"authors": authors}}),
        encoding="utf-8",
    )
    (source / "main.tex").write_text(
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        f"{sentence} {FILLER}\n"
        "\\end{document}\n",
        encoding="utf-8",
    )


class AuthorBalancedLexiconTests(unittest.TestCase):
    def test_fancy_verbatim_paths_and_body_macro_definitions_are_not_prose(
        self,
    ) -> None:
        from tools.lexicon import strip_tex, tokens

        source = r"""
\begin{document}
Readable prose remains.
\def\labelenumi{\arabic{enumi}.}
\path{experiments/private_checker.py}
\begin{Verbatim}[breaklines=true]
uv run python private_checker.py
\end{Verbatim}
\end{document}
"""
        words = {word for word, _ in tokens(strip_tex(source))}
        self.assertTrue({"readable", "prose", "remains"}.issubset(words))
        self.assertTrue({"enumi", "uv", "py", "private"}.isdisjoint(words))

    def test_prose_extraction_drops_math_and_keeps_line_numbers(self) -> None:
        from tools.lexicon import strip_tex, tokens

        source = (
            "\\begin{document}\n"
            "% a comment that must not become prose\n"
            "A module is called reflexive when the map is an isomorphism.\n"
            "\\begin{equation}\n"
            "\\operatorname{pd} M = \\flaggableinsidemath\n"
            "\\end{equation}\n"
            "\\end{document}\n"
        )
        found = tokens(strip_tex(source))
        words = {word for word, _ in found}
        self.assertIn("reflexive", words)
        self.assertNotIn("flaggableinsidemath", words)
        self.assertNotIn("comment", words)
        line = next(number for word, number in found if word == "reflexive")
        self.assertIn("reflexive", source.splitlines()[line - 1])

    def test_check_keeps_an_absolute_path_outside_the_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "vocab"
            add_paper(root, "0001", ["Sophie Germain"], "The resolution is exact.")
            build(root, output)

            with tempfile.TemporaryDirectory() as elsewhere:
                manuscript = Path(elsewhere) / "main.tex"
                manuscript.write_text(
                    "\\begin{document}\nA wobblesome module.\n\\end{document}\n",
                    encoding="utf-8",
                )
                result = check(root, output, [manuscript])

            row = next(
                entry for entry in result["unattested_words"]
                if entry["text"] == "wobblesome"
            )
            self.assertEqual(row["where"], [f"{manuscript}:2"])

    def test_report_paths_default_locally_and_do_not_guess_across_directories(
        self,
    ) -> None:
        targets = [Path("paper/example/main.tex"), Path("paper/example/body.tex")]
        self.assertEqual(
            resolve_report_paths(targets),
            (
                Path("paper/example/vocabulary-report.json"),
                Path("paper/example/vocabulary-report.md"),
            ),
        )
        self.assertEqual(
            resolve_report_paths(
                targets, json_path=Path("scratch/custom.json")
            ),
            (
                Path("scratch/custom.json"),
                Path("paper/example/vocabulary-report.md"),
            ),
        )
        different = [Path("paper/a/main.tex"), Path("paper/b/body.tex")]
        with self.assertRaisesRegex(ValueError, "different parent directories"):
            resolve_report_paths(different)
        self.assertEqual(
            resolve_report_paths(different, report_dir=Path("scratch/reports")),
            (
                Path("scratch/reports/vocabulary-report.json"),
                Path("scratch/reports/vocabulary-report.md"),
            ),
        )
        self.assertEqual(
            resolve_report_paths(
                different,
                json_path=Path("scratch/a.json"),
                markdown_path=Path("scratch/a.md"),
            ),
            (Path("scratch/a.json"), Path("scratch/a.md")),
        )
        self.assertEqual(resolve_report_paths(targets, stdout_only=True), (None, None))
        with self.assertRaisesRegex(ValueError, "cannot be combined"):
            resolve_report_paths(
                targets, json_path=Path("report.json"), stdout_only=True
            )
        with self.assertRaisesRegex(ValueError, "different paths"):
            resolve_report_paths(
                targets,
                json_path=Path("report"),
                markdown_path=Path("report"),
            )

    def test_author_signatures_are_conservative_and_metadata_is_cleaned(self) -> None:
        self.assertEqual(author_key("Aslak B. Buan"), author_key("Aslak Bakke Buan"))
        self.assertEqual(clean_author_names("Department of Mathematics"), [])
        self.assertEqual(
            clean_author_names("Antoine Mériaux, Gérard Cauchon"),
            ["Antoine Mériaux", "Gérard Cauchon"],
        )
        self.assertEqual(clean_author_names("1cm Bishal Deb"), ["Bishal Deb"])
        self.assertEqual(
            clean_author_names("Masahito Hayashi1,2"), ["Masahito Hayashi"]
        )

    def test_author_and_paper_breadth_control_compound_and_rare_signals(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "vocab"

            open_authors = [
                ["Open Author A", "Open Author B"],
                ["Open Author C"],
                ["Open Author D"],
                ["Open Author E"],
            ]
            for index, (authors, marker) in enumerate(zip(
                open_authors, ("amber", "bronze", "cobalt", "denim"), strict=True,
            )):
                add_paper(
                    root,
                    f"open-{index}",
                    authors,
                    f"The torsion pair is standardish marker{marker}.",
                )
            add_paper(
                root,
                "hyphenated",
                ["Hyphen Author"],
                "The torsion-pair is markerhyphen.",
            )

            for index, marker in enumerate(("alpha", "beta", "gamma", "delta")):
                add_paper(
                    root,
                    f"prolific-{index}",
                    ["One Prolific Author"],
                    f"The quasarword occurs with marker{marker}.",
                )
            add_paper(
                root,
                "large-collaboration",
                [f"Collaborator {letter}" for letter in "ABCDEF"],
                "The galaxyword occurs with markergalaxy.",
            )
            add_paper(
                root,
                "unknown-authors",
                [],
                "The metadataword occurs. Torsion. Pair does not form a phrase.",
            )

            corpus = build(root, output)
            manuscript = root / "paper" / "main.tex"
            manuscript.parent.mkdir()
            manuscript.write_text(
                "\\begin{document}\n"
                "A torsion-pair, standardish, quasarword, galaxyword, and "
                "metadataword occur here.\n"
                "\\end{document}\n",
                encoding="utf-8",
            )
            result = check(root, output, [manuscript])

            self.assertEqual(corpus["papers"], 11)
            self.assertEqual(corpus["papers_without_author_metadata"], 1)
            self.assertEqual(corpus["authors"], 13)

            comparison = next(
                row for row in result["compound_comparisons"]
                if row["text"] == "torsion-pair"
            )
            self.assertEqual(comparison["variants"]["hyphenated"]["papers"], 1)
            self.assertEqual(comparison["variants"]["hyphenated"]["authors"], 1)
            self.assertEqual(comparison["variants"]["open"]["occurrences"], 4)
            self.assertEqual(comparison["variants"]["open"]["papers"], 4)
            self.assertEqual(comparison["variants"]["open"]["authors"], 5)
            self.assertEqual(len(comparison["variants"]["open"]["paper_keys"]), 4)
            self.assertEqual(len(comparison["variants"]["open"]["author_keys"]), 5)
            self.assertEqual(
                comparison["assessment"], "broad support for open form"
            )

            rare = {row["text"]: row for row in result["rare_words"]}
            self.assertNotIn("standardish", rare)
            self.assertEqual(
                (rare["quasarword"]["papers"], rare["quasarword"]["authors"]),
                (4, 1),
            )
            self.assertEqual(
                (rare["galaxyword"]["papers"], rare["galaxyword"]["authors"]),
                (1, 6),
            )
            self.assertEqual(rare["metadataword"]["unknown_author_papers"], 1)

            lexicon = load_lexicon(output)
            self.assertEqual(lexicon["quasarword"]["authors"], 1)
            self.assertEqual(lexicon["galaxyword"]["papers"], 1)

            report = render_markdown(result, corpus)
            self.assertIn("General-English hyphenation", report)
            self.assertIn("broad support for open form", report)
            self.assertIn("no manuscript-level pass or fail result", report)
            self.assertIn("Never respell a token merely", report)
            self.assertNotIn("owner", report.lower())

            stdout = io.StringIO()
            with mock.patch.object(sys, "argv", [
                "lexicon.py", "check", str(manuscript),
                "--root", str(root), "--out", str(output),
            ]), contextlib.redirect_stdout(stdout):
                self.assertEqual(main(), 0)
            json_report = manuscript.parent / "vocabulary-report.json"
            markdown_report = manuscript.parent / "vocabulary-report.md"
            self.assertTrue(json_report.is_file())
            self.assertTrue(markdown_report.is_file())
            summary = json.loads(stdout.getvalue())
            self.assertEqual(summary["manuscript_result"], "not_pass_fail")
            self.assertEqual(
                summary["required_action"], "inspect_and_adjudicate_report"
            )
            self.assertEqual(summary["json_report"], str(json_report))
            self.assertEqual(summary["markdown_report"], str(markdown_report))

            json_report.unlink()
            markdown_report.unlink()
            stdout = io.StringIO()
            with mock.patch.object(sys, "argv", [
                "lexicon.py", "check", str(manuscript),
                "--root", str(root), "--out", str(output), "--stdout-only",
            ]), contextlib.redirect_stdout(stdout):
                self.assertEqual(main(), 0)
            self.assertFalse(json_report.exists())
            self.assertFalse(markdown_report.exists())
            summary = json.loads(stdout.getvalue())
            self.assertEqual(summary["manuscript_result"], "not_pass_fail")
            self.assertEqual(summary["required_action"], "exploratory_only")
            self.assertIsNone(summary["json_report"])
            self.assertIsNone(summary["markdown_report"])


if __name__ == "__main__":
    unittest.main()
