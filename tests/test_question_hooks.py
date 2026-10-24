"""Exercise the real question hooks in isolated Git repositories."""

from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
LIVE = "threads/program/RESEARCH-QUESTIONS.md"
RETIRED = "threads/program/RESEARCH-QUESTIONS-RETIRED.md"
VALID = """# Research questions

## first: Does the construction work?

Serves: the general construction.
Observation: two attempts meet the same obstruction.
Explanations: a common lemma, or a counterexample.
Next action: test the lemma.
Either way: resolve the obstruction.
"""
EMPTY = "# Research questions\n"


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=False
    )


def checked_git(repo: Path, *args: str) -> None:
    result = git(repo, *args)
    assert result.returncode == 0, result.stdout + result.stderr


def write(repo: Path, name: str, text: str, *, stage: bool = True) -> None:
    path = repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    if stage:
        checked_git(repo, "add", "--", name)


def commit(
    repo: Path, *, message: str = "Update records"
) -> subprocess.CompletedProcess[str]:
    return git(repo, "commit", "-m", message)


def accept(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, result.stdout + result.stderr


def reject(result: subprocess.CompletedProcess[str], reason: str) -> None:
    assert result.returncode != 0
    assert reason in result.stdout + result.stderr


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    checked_git(tmp_path, "init", "-b", "main")
    checked_git(tmp_path, "config", "user.name", "Hook test")
    checked_git(tmp_path, "config", "user.email", "hooks@example.invalid")
    checked_git(tmp_path, "config", "commit.gpgSign", "false")
    checked_git(tmp_path, "config", "core.hooksPath", "tools/hooks")
    tools = tmp_path / "tools"
    tools.mkdir()
    shutil.copytree(ROOT / "tools/hooks", tools / "hooks")
    shutil.copy2(ROOT / "tools/audit_questions.py", tools / "audit_questions.py")
    return tmp_path


def start_program(repo: Path) -> None:
    write(repo, LIVE, VALID)
    accept(commit(repo, message="Start program\n\nQuestion: first"))


# Ordinary catalogs: many entries, headings with identifiers, and free-form
# fields, none of which follow the program format or its cap of 6.
SOURCE_CATALOG = "# Problems from a survey\n\nDate: 2026-01-01\n\n" + "".join(
    f"## SUR-{n:03d}: Problem {n}\n\nSource: survey, section {n}.\n\n"
    "Statement: an open question.\n\n"
    for n in range(1, 10)
)
STATUS_CATALOG = """# Research questions: current status

## Original questions

### Q3: the remaining distinction

Partly answered; see the ledger.

### Q4 and Q7: what the criteria leave open

Open.

## Current boundary

Nothing further is claimed.
"""


@pytest.mark.parametrize(
    ("thread", "catalog"),
    [
        ("survey-problems", SOURCE_CATALOG),
        ("status-questions", STATUS_CATALOG),
    ],
)
def test_ordinary_catalogs_need_neither_program_format_nor_trailer(
    repo: Path, thread: str, catalog: str
) -> None:
    write(repo, f"threads/{thread}/QUESTIONS.md", catalog)
    accept(commit(repo))
    write(repo, f"threads/{thread}/LEDGER.md", "Updated status.\n")
    accept(commit(repo))


def test_new_program_requires_trailer(repo: Path) -> None:
    write(repo, LIVE, VALID)
    reject(commit(repo), "commit-msg:")
    accept(commit(repo, message="Start program\n\nQuestion: first"))


def test_existing_program_requires_trailer_for_other_files(repo: Path) -> None:
    start_program(repo)
    write(repo, "threads/program/LEDGER.md", "Update direction.\n")
    reject(commit(repo), "commit-msg:")
    accept(commit(repo, message="Update direction\n\nQuestion: none"))


def test_program_caps_still_enforced(repo: Path) -> None:
    text = EMPTY + "\n".join(
        VALID.split("\n\n", 1)[1].replace("first:", f"q{i}:") for i in range(7)
    )
    write(repo, LIVE, text)
    reject(commit(repo, message="Too many questions\n\nQuestion: q0"), "cap of 6")


def test_ordinary_catalog_can_coexist_with_program_list(repo: Path) -> None:
    start_program(repo)
    write(repo, "threads/program/QUESTIONS.md", "# Catalog\n\n## Q1\n\nUnstructured.\n")
    accept(commit(repo, message="Add catalog\n\nQuestion: none"))


def test_untracked_program_list_does_not_opt_in(repo: Path) -> None:
    write(repo, LIVE, "## Invalid program\n", stage=False)
    write(repo, "threads/program/QUESTIONS.md", "## Ordinary catalog\n")
    accept(commit(repo))


def test_audit_reads_staged_list_not_worktree(repo: Path) -> None:
    write(repo, LIVE, VALID)
    write(repo, LIVE, "## Broken unstaged edit\n", stage=False)
    accept(commit(repo, message="Start program\n\nQuestion: first"))


def test_unstaged_repair_does_not_hide_invalid_index(repo: Path) -> None:
    write(repo, LIVE, "## Broken staged edit\n")
    write(repo, LIVE, VALID, stage=False)
    reject(commit(repo, message="Start program\n\nQuestion: first"), "second-level heading")


def test_removed_question_needs_new_retirement_file(repo: Path) -> None:
    start_program(repo)
    write(repo, LIVE, EMPTY)
    reject(commit(repo, message="Retire question\n\nQuestion: first"), "removed without")
    write(
        repo,
        RETIRED,
        "# Retired\n\n" + VALID.split("\n\n", 1)[1]
        + "\nRetired: 2026-10-12; answered: see proof.\n",
    )
    accept(commit(repo, message="Retire question\n\nQuestion: first"))
    write(repo, RETIRED, "# Rewritten history\n")
    reject(commit(repo, message="Rewrite archive\n\nQuestion: none"), "append-only")


def test_deleting_program_list_does_not_skip_retirement(repo: Path) -> None:
    start_program(repo)
    checked_git(repo, "rm", "--", LIVE)
    reject(commit(repo, message="Delete program list\n\nQuestion: none"), "removed without")


def test_renaming_program_to_ordinary_catalog_does_not_skip_retirement(
    repo: Path,
) -> None:
    start_program(repo)
    checked_git(repo, "mv", LIVE, "threads/program/QUESTIONS.md")
    reject(commit(repo, message="Rename program list\n\nQuestion: none"), "removed without")


def test_migrate_legacy_program_without_bypassing_hooks(repo: Path) -> None:
    legacy_live = "threads/program/QUESTIONS.md"
    legacy_retired = "threads/program/QUESTIONS-RETIRED.md"
    archive = "# Retired\n\nEarlier historical records.\n"
    write(repo, legacy_live, VALID)
    write(repo, legacy_retired, archive)
    accept(commit(repo))
    checked_git(repo, "mv", legacy_live, LIVE)
    checked_git(repo, "mv", legacy_retired, RETIRED)
    accept(commit(repo, message="Rename program records\n\nQuestion: none"))
    assert (repo / LIVE).read_text() == VALID
    assert (repo / RETIRED).read_text() == archive
    write(repo, RETIRED, "Replaced history.\n")
    reject(commit(repo, message="Alter archive\n\nQuestion: none"), "append-only")


def test_legacy_archive_does_not_satisfy_new_retirement_contract(repo: Path) -> None:
    start_program(repo)
    write(repo, LIVE, EMPTY)
    write(
        repo,
        "threads/program/QUESTIONS-RETIRED.md",
        VALID + "\nRetired: 2026-10-12; answered: see proof.\n",
    )
    reject(commit(repo, message="Retire question\n\nQuestion: first"), "removed without")
