from pathlib import Path

from tools.audit_claim_catalog import audit_catalog


def entry(number: int, *, extra: str = "") -> str:
    return f"""### {number}. Example

Status: proved/agent

Statement: Exact example statement.

Evidence:

- [`note.md`](notes/note.md)

Dependencies: none
{extra}
"""


def test_accepts_ordered_compact_catalog(tmp_path: Path) -> None:
    path = tmp_path / "CLAIMS.md"
    path.write_text("# Claims\n\n" + entry(1) + "\n" + entry(2))

    assert audit_catalog(path) == []


def test_accepts_multiline_dependencies(tmp_path: Path) -> None:
    path = tmp_path / "CLAIMS.md"
    path.write_text(
        "# Claims\n\n"
        + entry(1).replace(
            "Dependencies: none",
            "Dependencies: example-thread:1 and\nexample-thread:2",
        )
    )

    assert audit_catalog(path) == []


def test_rejects_out_of_order_identifiers(tmp_path: Path) -> None:
    path = tmp_path / "CLAIMS.md"
    path.write_text("# Claims\n\n" + entry(3) + "\n" + entry(1))

    diagnostics = audit_catalog(path)

    assert any("not in strictly increasing" in item.message for item in diagnostics)


def test_rejects_identifier_gaps(tmp_path: Path) -> None:
    path = tmp_path / "CLAIMS.md"
    path.write_text("# Claims\n\n" + entry(1) + "\n" + entry(3))

    diagnostics = audit_catalog(path)

    assert any("must be consecutive" in item.message for item in diagnostics)


def test_rejects_legacy_metadata_and_proof_sections(tmp_path: Path) -> None:
    path = tmp_path / "CLAIMS.md"
    path.write_text(
        "# Claims\n\n"
        + entry(1, extra="\nProof: This belongs in a note.\nAgent: codex\n")
    )

    diagnostics = audit_catalog(path)

    assert any("legacy metadata" in item.message for item in diagnostics)
    assert any("proof/detail section" in item.message for item in diagnostics)


def test_warns_on_oversized_entry(tmp_path: Path) -> None:
    path = tmp_path / "CLAIMS.md"
    path.write_text("# Claims\n\n" + entry(1, extra="\n".join(["line"] * 20)))

    diagnostics = audit_catalog(path, max_entry_lines=10)

    assert any(item.level == "warning" for item in diagnostics)


def test_rejects_superseded_registry_entries(tmp_path: Path) -> None:
    path = tmp_path / "CLAIMS.md"
    path.write_text(
        "# Claims\n\n" + entry(1).replace("Status: proved/agent", "Status: superseded")
    )

    diagnostics = audit_catalog(path)

    assert any("not the live catalog" in item.message for item in diagnostics)


def test_accepts_declared_empty_catalog(tmp_path: Path) -> None:
    path = tmp_path / "CLAIMS.md"
    path.write_text("# Durable claims: example\n\nNo durable claims yet.\n")

    assert audit_catalog(path) == []


def test_rejects_undeclared_empty_catalog(tmp_path: Path) -> None:
    path = tmp_path / "CLAIMS.md"
    path.write_text("# Durable claims: example\n")

    diagnostics = audit_catalog(path)

    assert len(diagnostics) == 1
    assert diagnostics[0].level == "error"
