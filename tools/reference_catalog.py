from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

try:
    from tools.reference_utils import sha256, write_json_atomic
except ModuleNotFoundError:  # Direct execution starts with tools/ on sys.path.
    from reference_utils import sha256, write_json_atomic


KINDS = {"arxiv": "arxiv", "papers": "paper", "books": "book"}

# Bibliographic fields written by tools/reference_metadata.py into each
# item.json and mirrored into the catalog so a search never opens 300 files.
CARRIED_FIELDS = (
    "bibliographic_identity",
    "metadata_provenance",
    "aliases",
    "derivatives",
    "citations",
    "citation_count",
    "search_text",
    "metadata_refreshed_at",
)


def display(path: Path, root: Path) -> str:
    return (Path("references") / path.relative_to(root)).as_posix()


def regular_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(candidate for candidate in path.rglob("*") if candidate.is_file())


def read_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def external_records(root: Path) -> list[dict[str, object]]:
    """Externally held sources (inbox, external libraries) known only through derivatives."""
    external_root = root / "external"
    if not external_root.is_dir():
        return []
    records: list[dict[str, object]] = []
    for path in sorted(external_root.glob("*.json")):
        payload = read_json(path)
        if payload.get("id"):
            payload["record_path"] = display(path, root)
            records.append(payload)
    return records


def item_records(root: Path) -> list[tuple[Path, dict[str, object]]]:
    records: list[tuple[Path, dict[str, object]]] = []
    for plural in KINDS:
        kind_root = root / "items" / plural
        if not kind_root.is_dir():
            continue
        for item in sorted(path for path in kind_root.iterdir() if path.is_dir()):
            metadata_path = item / "item.json"
            if not metadata_path.is_file():
                continue
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise RuntimeError(f"item metadata is not an object: {metadata_path}")
            records.append((metadata_path, payload))
    return records


def refresh_catalog(root: Path) -> dict[str, object]:
    root = root.resolve()
    items: list[dict[str, object]] = []
    described = 0
    for metadata_path, payload in item_records(root):
        item_path = metadata_path.parent
        original_dir = item_path / "original"
        source_dir = item_path / "source"
        record: dict[str, object] = {
            "id": payload.get("id"),
            "kind": payload.get("kind"),
            "key": payload.get("key"),
            "path": display(item_path, root),
            "item_path": payload.get("item_path"),
            "metadata_path": metadata_path.relative_to(root).as_posix(),
            "checked_at": payload.get("checked_at"),
            "original_files": (
                [display(path, root) for path in regular_files(original_dir)]
                if original_dir.is_dir()
                else []
            ),
            "source_file_count": len(regular_files(source_dir)) if source_dir.is_dir() else 0,
        }
        for name in CARRIED_FIELDS:
            if name in payload:
                record[name] = payload[name]
        if isinstance(record.get("bibliographic_identity"), dict):
            described += 1
        items.append(record)
    items.sort(key=lambda item: str(item.get("id")))

    external = external_records(root)
    catalog = {
        "schema_version": 2,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "items": items,
        "external_sources": external,
    }
    output = root / "CATALOG.json"
    write_json_atomic(output, catalog)
    return {
        "catalog_items": len(items),
        "described_items": described,
        "external_sources": len(external),
        "path": output.relative_to(root).as_posix(),
    }


def _safe_workspace_path(root: Path, raw: object) -> Path | None:
    if not isinstance(raw, str) or not raw:
        return None
    candidate = (root / raw).resolve()
    if not candidate.is_relative_to(root.resolve()):
        return None
    return candidate


def audit(root: Path) -> dict[str, object]:
    root = root.resolve()
    problems: list[str] = []
    seen_ids: set[str] = set()

    for plural in KINDS:
        kind_root = root / "items" / plural
        if not kind_root.is_dir():
            continue
        for item in sorted(path for path in kind_root.iterdir() if path.is_dir()):
            if not (item / "item.json").is_file():
                problems.append(f"item lacks item.json: {item}")

    for metadata_path, payload in item_records(root):
        item_id = payload.get("id")
        if not isinstance(item_id, str) or not item_id:
            problems.append(f"missing item id: {metadata_path}")
        elif item_id in seen_ids:
            problems.append(f"duplicate item id: {item_id}")
        else:
            seen_ids.add(item_id)

        item_path = _safe_workspace_path(root, payload.get("item_path"))
        if item_path != metadata_path.parent.resolve():
            problems.append(f"incorrect item_path: {metadata_path}")

        resources = payload.get("resources", {})
        if not isinstance(resources, dict):
            problems.append(f"resources is not an object: {metadata_path}")
            continue
        for name, raw_resource in resources.items():
            if not isinstance(raw_resource, dict):
                problems.append(f"resource {name!r} is not an object: {metadata_path}")
                continue
            path = _safe_workspace_path(root, raw_resource.get("path"))
            if path is None or not path.is_file():
                problems.append(f"missing or unsafe resource {name!r}: {metadata_path}")
                continue
            expected_hash = raw_resource.get("sha256")
            if isinstance(expected_hash, str) and sha256(path) != expected_hash:
                problems.append(f"hash mismatch for resource {name!r}: {metadata_path}")

    catalog_path = root / "CATALOG.json"
    if catalog_path.is_file():
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        catalog_ids = [item.get("id") for item in catalog.get("items", [])]
        if catalog_ids != sorted(seen_ids):
            problems.append("CATALOG.json is stale; refresh it")

    if problems:
        raise RuntimeError(json.dumps({"problems": problems}, indent=2))
    return {"status": "ok", "items": len(seen_ids)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh or audit the local reference catalog.")
    parser.add_argument("--root", type=Path, default=Path("references"))
    parser.add_argument("--refresh-catalog", action="store_true")
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--hash", dest="hash_path", type=Path, help="print a file hash for item metadata")
    args = parser.parse_args()

    if not args.refresh_catalog and not args.audit and args.hash_path is None:
        parser.error("select --refresh-catalog, --audit, --hash, or a combination")

    output: dict[str, object] = {}
    if args.hash_path is not None:
        output["hash"] = {
            "path": str(args.hash_path),
            "sha256": sha256(args.hash_path),
            "bytes": args.hash_path.stat().st_size,
        }
    if args.refresh_catalog:
        output["refresh"] = refresh_catalog(args.root)
    if args.audit:
        output["audit"] = audit(args.root)
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
