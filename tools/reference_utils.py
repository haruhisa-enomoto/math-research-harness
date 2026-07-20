from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    if not slug:
        raise ValueError(f"cannot form a slug from {value!r}")
    return slug[:100]


def parse_pages(spec: str | None, total: int) -> list[int]:
    """Parse a one-indexed page selection, defaulting to every page."""
    if total < 1:
        raise ValueError("document has no pages")
    if spec is None:
        return list(range(1, total + 1))

    pages: list[int] = []
    for raw_part in spec.split(","):
        part = raw_part.strip()
        if not part:
            continue
        if "-" in part:
            start_raw, end_raw = part.split("-", 1)
            start, end = int(start_raw), int(end_raw)
            if end < start:
                raise ValueError(f"descending page range is not supported: {part!r}")
            pages.extend(range(start, end + 1))
        else:
            pages.append(int(part))

    if not pages:
        raise ValueError("empty page selection")
    bad = [page for page in pages if page < 1 or page > total]
    if bad:
        raise ValueError(f"page numbers outside 1..{total}: {bad[:10]}")
    if len(set(pages)) != len(pages):
        raise ValueError("duplicate pages in selection")
    return pages


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def write_json_atomic(path: Path, payload: object) -> None:
    write_text_atomic(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def command_version(command: str) -> str | None:
    executable = shutil.which(command)
    if executable is None:
        return None
    completed = subprocess.run([executable, "--version"], capture_output=True, text=True)
    output = (completed.stdout or completed.stderr).strip().splitlines()
    return output[0] if output else executable


def require_commands(*commands: str) -> None:
    missing = [command for command in commands if shutil.which(command) is None]
    if missing:
        raise RuntimeError(f"missing required commands: {', '.join(missing)}")
