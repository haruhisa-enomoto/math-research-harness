#!/usr/bin/env python3
"""Audit question-driven RESEARCH-QUESTIONS.md files, not ordinary catalogs.

A question-driven program keeps its live questions in a capped
``threads/<thread>/RESEARCH-QUESTIONS.md`` and moves retired entries verbatim
to an append-only ``RESEARCH-QUESTIONS-RETIRED.md`` beside it.
Ordinary ``QUESTIONS.md`` files do not select this contract.
See ``docs/RECORDS.md``.

With ``--staged`` the audit reads the Git index and ``HEAD`` instead of the
working tree, and additionally checks that every question removed since
``HEAD`` was retired in the same commit and that the retired file only grew.
The pre-commit hook in ``tools/hooks/`` uses that mode.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


QUESTION_HEADING = re.compile(r"(?m)^## ([a-z0-9][a-z0-9-]*): (.+)$")
OTHER_SECOND_LEVEL = re.compile(r"(?m)^## ")
REQUIRED_FIELDS = (
    "Serves:",
    "Observation:",
    "Explanations:",
    "Next action:",
    "Either way:",
)
LINK = re.compile(r"\]\(")
RETIRED_NAME = "RESEARCH-QUESTIONS-RETIRED.md"
RETIRED_LINE = re.compile(
    r"(?m)^Retired: \d{4}-\d{2}-\d{2}; "
    r"(answered|refuted|superseded by [a-z0-9][a-z0-9-]*|parked|dropped): (.+)$"
)

MAX_QUESTIONS = 6
MAX_ENTRY_LINES = 15
MAX_LINKS = 2


@dataclass(frozen=True)
class Diagnostic:
    level: str
    path: Path
    question: str | None
    message: str

    def render(self) -> str:
        location = str(self.path)
        if self.question is not None:
            location += f": {self.question}"
        return f"{self.level}: {location}: {self.message}"


def question_sections(text: str) -> list[tuple[str, str]]:
    """Return ``(identifier, body)`` for each question heading in order."""

    matches = list(QUESTION_HEADING.finditer(text))
    return [
        (
            match.group(1),
            text[match.end() : matches[index + 1].start()]
            if index + 1 < len(matches)
            else text[match.end() :],
        )
        for index, match in enumerate(matches)
    ]


def audit_text(
    path: Path,
    text: str,
    *,
    max_questions: int = MAX_QUESTIONS,
    max_entry_lines: int = MAX_ENTRY_LINES,
    max_links: int = MAX_LINKS,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    questions = question_sections(text)

    headings = len(OTHER_SECOND_LEVEL.findall(text))
    if headings != len(questions):
        diagnostics.append(
            Diagnostic(
                "error",
                path,
                None,
                "every second-level heading must have the form "
                "'## <kebab-id>: <question>'",
            )
        )
    if len(questions) > max_questions:
        diagnostics.append(
            Diagnostic(
                "error",
                path,
                None,
                f"{len(questions)} live questions exceed the cap of {max_questions}; "
                f"retire one to {RETIRED_NAME} before adding another",
            )
        )

    seen: set[str] = set()
    for identifier, body in questions:
        if identifier in seen:
            diagnostics.append(
                Diagnostic("error", path, identifier, "duplicate question identifier")
            )
        seen.add(identifier)
        for field in REQUIRED_FIELDS:
            if not re.search(rf"(?m)^{re.escape(field)}", body):
                diagnostics.append(
                    Diagnostic("error", path, identifier, f"missing field {field!r}")
                )
        lines = len(body.strip().splitlines())
        if lines > max_entry_lines:
            diagnostics.append(
                Diagnostic(
                    "error",
                    path,
                    identifier,
                    f"{lines} lines exceed the entry cap of {max_entry_lines}; "
                    "rewrite the entry and move detail to a note",
                )
            )
        links = len(LINK.findall(body))
        if links > max_links:
            diagnostics.append(
                Diagnostic(
                    "error",
                    path,
                    identifier,
                    f"{links} links exceed {max_links}; an entry points to its "
                    "origin, it does not summarize notes",
                )
            )
    return diagnostics


def audit_transition(
    path: Path,
    previous: str | None,
    current: str,
    previous_retired: str | None,
    current_retired: str | None,
) -> list[Diagnostic]:
    """Check that removed questions were retired and the retired file only grew."""

    diagnostics: list[Diagnostic] = []
    retired_path = path.with_name(RETIRED_NAME)
    old_retired = previous_retired or ""
    new_retired = current_retired or ""
    if not new_retired.startswith(old_retired.rstrip()):
        diagnostics.append(
            Diagnostic(
                "error",
                retired_path,
                None,
                "the retired file is append-only; earlier content was changed",
            )
        )
    if previous is None:
        return diagnostics
    live = {identifier for identifier, _ in question_sections(current)}
    newly_retired = new_retired[len(old_retired.rstrip()) :]
    retired = question_sections(newly_retired)
    retired_ids = {identifier for identifier, _ in retired}
    for identifier, body in retired:
        match = RETIRED_LINE.search(body)
        if match is None:
            diagnostics.append(
                Diagnostic(
                    "error",
                    retired_path,
                    identifier,
                    "needs a line 'Retired: <YYYY-MM-DD>; <kind>: <reason>' with kind "
                    "answered, refuted, superseded by <id>, parked, or dropped",
                )
            )
        elif match.group(1) == "parked" and "reopen when" not in match.group(2).lower():
            diagnostics.append(
                Diagnostic(
                    "error",
                    retired_path,
                    identifier,
                    "a parked question names its obstruction and says 'reopen when ...'",
                )
            )
    for identifier, _ in question_sections(previous):
        if identifier not in live and identifier not in retired_ids:
            diagnostics.append(
                Diagnostic(
                    "error",
                    path,
                    identifier,
                    f"question removed without being appended to {RETIRED_NAME}",
                )
            )
    return diagnostics


def _git_show(spec: str) -> str | None:
    result = subprocess.run(
        ["git", "show", spec], capture_output=True, text=True, check=False
    )
    return result.stdout if result.returncode == 0 else None


def audit_staged(path: Path) -> list[Diagnostic]:
    # A staged deletion is an empty live list, not an escape from retirement.
    current = _git_show(f":{path.as_posix()}") or ""
    retired = path.with_name(RETIRED_NAME).as_posix()
    return audit_text(path, current) + audit_transition(
        path,
        _git_show(f"HEAD:{path.as_posix()}"),
        current,
        _git_show(f"HEAD:{retired}"),
        _git_show(f":{retired}"),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument(
        "--staged",
        action="store_true",
        help="audit the Git index against HEAD, including retirement checks",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    diagnostics: list[Diagnostic] = []
    for path in args.files:
        if args.staged:
            diagnostics.extend(audit_staged(path))
        else:
            diagnostics.extend(audit_text(path, path.read_text()))
    for diagnostic in diagnostics:
        print(diagnostic.render())
    if diagnostics:
        return 1
    print("question audit passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
