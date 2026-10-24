#!/usr/bin/env python3
"""Audit the structural contract of one or more CLAIMS.md catalogs."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


CLAIM_HEADING = re.compile(r"(?m)^### (\d+)\. (.+)$")
REQUIRED_FIELDS = ("Status:", "Statement:", "Evidence:", "Dependencies:")
LEGACY_METADATA = re.compile(r"(?m)^(Date|Agent|Type|Last corrected|Last extended):")
EMPTY_CATALOG = re.compile(r"(?im)^No durable claims yet\.?\s*$")
PROOF_SECTIONS = re.compile(
    r"(?im)^(Proof|Proof sketch|Argument|Verification details|"
    r"Computation details|Implementation details|Runtime):"
)


@dataclass(frozen=True)
class Diagnostic:
    level: str
    path: Path
    claim: int | None
    message: str

    def render(self) -> str:
        location = str(self.path)
        if self.claim is not None:
            location += f": claim {self.claim}"
        return f"{self.level}: {location}: {self.message}"


def _claim_sections(text: str) -> list[tuple[int, str, str]]:
    matches = list(CLAIM_HEADING.finditer(text))
    return [
        (
            int(match.group(1)),
            match.group(2).strip(),
            text[match.end() : matches[index + 1].start()]
            if index + 1 < len(matches)
            else text[match.end() :],
        )
        for index, match in enumerate(matches)
    ]


def audit_catalog(path: Path, *, max_entry_lines: int = 60) -> list[Diagnostic]:
    text = path.read_text()
    claims = _claim_sections(text)
    diagnostics: list[Diagnostic] = []
    if not claims:
        if EMPTY_CATALOG.search(text):
            return []
        return [
            Diagnostic(
                "error",
                path,
                None,
                "no claim headings found; a catalog with no entry yet must say "
                "'No durable claims yet.'",
            )
        ]

    numbers = [number for number, _, _ in claims]
    if len(set(numbers)) != len(numbers):
        duplicates = sorted(
            number for number in set(numbers) if numbers.count(number) > 1
        )
        diagnostics.append(
            Diagnostic(
                "error",
                path,
                None,
                f"duplicate identifiers: {', '.join(map(str, duplicates))}",
            )
        )
    if numbers != sorted(numbers):
        diagnostics.append(
            Diagnostic(
                "error",
                path,
                None,
                "claim headings are not in strictly increasing identifier order",
            )
        )
    expected = list(range(1, len(numbers) + 1))
    if numbers != expected:
        diagnostics.append(
            Diagnostic(
                "error",
                path,
                None,
                "claim identifiers must be consecutive from 1 in reading order",
            )
        )

    for number, _title, body in claims:
        positions: list[int] = []
        for field in REQUIRED_FIELDS:
            occurrences = [
                match.start()
                for match in re.finditer(rf"(?m)^{re.escape(field)}(?:\s|$)", body)
            ]
            if len(occurrences) != 1:
                diagnostics.append(
                    Diagnostic(
                        "error",
                        path,
                        number,
                        f"expected exactly one {field} field, found {len(occurrences)}",
                    )
                )
            elif occurrences:
                positions.append(occurrences[0])
        if len(positions) == len(REQUIRED_FIELDS) and positions != sorted(positions):
            diagnostics.append(
                Diagnostic(
                    "error",
                    path,
                    number,
                    "fields are not ordered Status, Statement, Evidence, Dependencies",
                )
            )
        metadata = LEGACY_METADATA.search(body)
        if metadata:
            diagnostics.append(
                Diagnostic(
                    "error",
                    path,
                    number,
                    f"legacy metadata field {metadata.group(1)!r} belongs in the note",
                )
            )
        proof = PROOF_SECTIONS.search(body)
        if proof:
            diagnostics.append(
                Diagnostic(
                    "error",
                    path,
                    number,
                    f"proof/detail section {proof.group(1)!r} belongs in linked evidence",
                )
            )
        line_count = len(body.strip().splitlines()) + 1
        if max_entry_lines and line_count > max_entry_lines:
            diagnostics.append(
                Diagnostic(
                    "warning",
                    path,
                    number,
                    f"{line_count} lines exceeds the {max_entry_lines}-line review guard",
                )
            )

        status_match = re.search(r"(?ms)^Status:\s*(.*?)(?=^Statement:)", body)
        statement_match = re.search(r"(?ms)^Statement:\s*(.*?)(?=^Evidence:)", body)
        evidence_match = re.search(r"(?ms)^Evidence:\s*(.*?)(?=^Dependencies:)", body)
        dependencies_match = re.search(r"(?ms)^Dependencies:\s*(.*?)\s*\Z", body)
        for label, match in (
            ("Status", status_match),
            ("Statement", statement_match),
            ("Evidence", evidence_match),
            ("Dependencies", dependencies_match),
        ):
            if match and not match.group(1).strip():
                diagnostics.append(
                    Diagnostic("error", path, number, f"{label} is empty")
                )
        if status_match and "superseded" in status_match.group(1).lower():
            diagnostics.append(
                Diagnostic(
                    "error",
                    path,
                    number,
                    "superseded entries belong in notes or Git, not the live catalog",
                )
            )
    return diagnostics


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("catalogs", nargs="+", type=Path)
    parser.add_argument(
        "--max-entry-lines",
        type=int,
        default=60,
        help="warn when an entry exceeds this review guard; 0 disables it",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="treat warnings as failures",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    diagnostics: list[Diagnostic] = []
    for catalog in args.catalogs:
        diagnostics.extend(audit_catalog(catalog, max_entry_lines=args.max_entry_lines))
    for diagnostic in diagnostics:
        print(diagnostic.render())
    has_error = any(item.level == "error" for item in diagnostics)
    has_warning = any(item.level == "warning" for item in diagnostics)
    if has_error or (args.strict and has_warning):
        return 1
    print(
        "claim catalog audit passed"
        if not diagnostics
        else "claim catalog audit passed with warnings"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
