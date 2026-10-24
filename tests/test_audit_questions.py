from pathlib import Path

from tools.audit_questions import audit_text, audit_transition


PATH = Path("threads/example/RESEARCH-QUESTIONS.md")


def entry(identifier: str, *, extra: str = "") -> str:
    return f"""## {identifier}: Is the objectwise isomorphism natural?

Serves: naturality of the comparison for all algebras in the territory.
Observation: Constructions A and B both fail at the same step
([note](notes/a.md)).
Explanations: a common universal property, or a coincidence of choices.
Next action: test commutativity on one map exposing the choice.
Either way: a uniform construction, or the condition blocking naturality.
{extra}
"""


def page(*entries: str) -> str:
    return "# Questions: example\n\nTerritory: see LEDGER.md.\n\n" + "\n".join(entries)


def test_accepts_compact_page() -> None:
    assert audit_text(PATH, page(entry("first"), entry("second"))) == []


def test_rejects_more_than_six_questions() -> None:
    text = page(*(entry(f"q{index}") for index in range(7)))

    diagnostics = audit_text(PATH, text)

    assert any("exceed the cap of 6" in item.message for item in diagnostics)


def test_rejects_long_entry() -> None:
    text = page(entry("long", extra="More detail.\n" * 12))

    diagnostics = audit_text(PATH, text)

    assert any("entry cap" in item.message for item in diagnostics)


def test_rejects_note_summary_entry() -> None:
    links = "".join(f"See [n{index}](notes/n{index}.md).\n" for index in range(3))

    diagnostics = audit_text(PATH, page(entry("linky", extra=links)))

    assert any("links exceed" in item.message for item in diagnostics)


def test_rejects_missing_field() -> None:
    text = page(entry("bare").replace("Either way:", "Outcome:"))

    diagnostics = audit_text(PATH, text)

    assert any("Either way:" in item.message for item in diagnostics)


def test_rejects_unstructured_heading() -> None:
    text = page(entry("ok"), "## Session log 2026-10-09\n\nDid things.\n")

    diagnostics = audit_text(PATH, text)

    assert any("second-level heading" in item.message for item in diagnostics)


def test_removed_question_must_be_retired() -> None:
    previous = page(entry("old"), entry("kept"))
    current = page(entry("kept"))

    diagnostics = audit_transition(PATH, previous, current, None, None)

    assert any("removed without" in item.message for item in diagnostics)


def test_retired_question_passes() -> None:
    previous = page(entry("old"), entry("kept"))
    current = page(entry("kept"))
    retired = "# Retired questions\n\n" + entry("old") + "Retired: 2026-10-09; answered: see note.\n"

    assert audit_transition(PATH, previous, current, None, retired) == []


def test_retired_file_is_append_only() -> None:
    old_retired = "# Retired questions\n\n" + entry("old")
    new_retired = "# Retired questions\n\n" + entry("old").replace("A and B", "A")

    diagnostics = audit_transition(PATH, None, page(), old_retired, new_retired)

    assert any("append-only" in item.message for item in diagnostics)


def retire(kind_and_reason: str) -> list:
    previous = page(entry("old"), entry("kept"))
    current = page(entry("kept"))
    retired = "# Retired questions\n\n" + entry("old") + f"Retired: 2026-10-10; {kind_and_reason}\n"
    return audit_transition(PATH, previous, current, None, retired)


def test_retirement_needs_a_kind() -> None:
    diagnostics = retire("solved it.")

    assert any("kind" in item.message for item in diagnostics)


def test_parked_needs_reopen_condition() -> None:
    diagnostics = retire("parked: the Ext pullback image is uncontrolled.")

    assert any("reopen when" in item.message for item in diagnostics)


def test_accepts_each_retirement_kind() -> None:
    for reason in (
        "answered: claim 30.",
        "refuted: the D4 example.",
        "superseded by kept: contained in it.",
        "parked: image control fails; reopen when a rank bound is known.",
        "dropped: lower value than the live questions.",
    ):
        assert retire(reason) == []


def test_rejects_missing_serves_line() -> None:
    text = page(entry("unanchored").replace("Serves:", "Context:"))

    diagnostics = audit_text(PATH, text)

    assert any("Serves:" in item.message for item in diagnostics)
