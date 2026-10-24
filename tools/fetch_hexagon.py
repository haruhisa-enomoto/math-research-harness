"""File known Hexagon (hexagonmath.org) works into the local reference workspace.

Hexagon identifiers have the same shape as modern arXiv identifiers
(`2610.00392v2`), so items live in their own `references/items/hexagon/`
tree and carry the `hexagon:` prefix everywhere. A bare identifier given to
this tool is a Hexagon identifier; it is never interpreted as arXiv.

Each item stores the public work record from the read-only API, the BibTeX,
the source zip, and the reading PDF. The record supplies authoritative
bibliographic metadata and Hexagon's authorship and human-understanding
declarations. Downloaded PDF and source files are checked against the SHA-256
digests the record publishes.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

try:
    from tools.fetch_arxiv import (
        DEFAULT_USER_AGENT,
        Download,
        curl_download,
        install_source,
        main_tex_candidates,
    )
    from tools.reference_catalog import audit_items, refresh_catalog_items
    from tools.reference_utils import sha256, write_json_atomic
except ModuleNotFoundError:  # Direct execution starts with tools/ on sys.path.
    from fetch_arxiv import (
        DEFAULT_USER_AGENT,
        Download,
        curl_download,
        install_source,
        main_tex_candidates,
    )
    from reference_catalog import audit_items, refresh_catalog_items
    from reference_utils import sha256, write_json_atomic


HEXAGON_BASE = "https://hexagonmath.org"
HEXAGON_HOSTS = {"hexagonmath.org", "www.hexagonmath.org"}
HEXAGON_ID = re.compile(r"\d{4}\.\d{5}(?:v[1-9]\d*)?")
VERSION = re.compile(r"v\d+$")
# Path prefixes of official record, file, and API URLs that end in an identifier.
URL_PREFIXES = ("abs/", "pdf/", "src/", "api/v1/works/", "api/bibtex/", "")


def normalize_hexagon_id(value: str) -> str:
    """Return a validated identifier from `hexagon:<id>`, a bare id, or a record URL."""
    candidate = value.strip()
    if candidate.casefold().startswith("hexagon:"):
        candidate = candidate.split(":", 1)[1].strip()

    if "://" in candidate:
        parsed = urlparse(candidate)
        if parsed.netloc.casefold() not in HEXAGON_HOSTS:
            raise ValueError(f"not a Hexagon URL: {value!r}")
        path = unquote(parsed.path).strip("/")
        for prefix in URL_PREFIXES:
            if path.startswith(prefix):
                rest = path[len(prefix) :].split("/", 1)[0]
                if HEXAGON_ID.fullmatch(rest):
                    candidate = rest
                    break
        else:
            raise ValueError(f"Hexagon URL has no work identifier: {value!r}")

    candidate = candidate.removesuffix(".pdf").strip("/")
    if not HEXAGON_ID.fullmatch(candidate):
        raise ValueError(f"invalid Hexagon identifier: {value!r}")
    return candidate


def item_key(hexagon_id: str) -> str:
    return hexagon_id.casefold()


def read_work(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    work = payload.get("work") if isinstance(payload, dict) else None
    if not isinstance(work, dict):
        raise RuntimeError(f"Hexagon work record has no 'work' object: {path}")
    return work


def declaration(work: dict[str, object]) -> dict[str, object]:
    """Hexagon's authorship and provenance declarations, kept beside the identity.

    These are submitter declarations, not checks. They matter when deciding
    how much weight a Hexagon source can bear.
    """
    return {
        "identifier": work.get("identifier"),
        "version_id": work.get("versionId"),
        "version_number": work.get("versionNumber"),
        "version_created_at": work.get("versionCreatedAt"),
        "published_at": work.get("publishedAt"),
        "status": work.get("status"),
        "withdrawn_at": work.get("withdrawnAt"),
        "withdrawal_note": work.get("withdrawalNote"),
        "authorship_mode": work.get("authorshipMode"),
        "human_understanding": work.get("humanUnderstanding"),
        "provenance_declaration": work.get("provenance"),
        "declared_arxiv_id": work.get("arxivId"),
        "doi": work.get("doi"),
        "license": work.get("license"),
        "formalizations": work.get("formalizations") or [],
        "record_url": f"{HEXAGON_BASE}/{work.get('versionId')}",
    }


def published_digests(work: dict[str, object]) -> dict[str, dict[str, str]]:
    """Map resource role to {filename: sha256} as published in the work record."""
    digests: dict[str, dict[str, str]] = {"paper": {}, "source": {}}
    files = work.get("files")
    if not isinstance(files, list):
        return digests
    for entry in files:
        if not isinstance(entry, dict):
            continue
        kind = entry.get("kind")
        name = entry.get("filename")
        digest = entry.get("sha256")
        if kind in digests and isinstance(name, str) and isinstance(digest, str):
            digests[str(kind)][name] = digest.casefold()
    return digests


def verify_source(source: Path, expected: dict[str, str]) -> dict[str, object]:
    """Compare extracted files with the record's per-file digests."""
    matched: list[str] = []
    absent: list[str] = []
    for name, digest in sorted(expected.items()):
        path = source / name
        if not path.is_file():
            absent.append(name)
            continue
        if sha256(path) != digest:
            raise RuntimeError(f"Hexagon source file {name!r} does not match its published SHA-256")
        matched.append(name)
    return {"matched": matched, "absent_from_archive": absent}


def fetch(
    value: str,
    *,
    root: Path = Path("references"),
    want_source: bool = True,
    want_pdf: bool = True,
    force: bool = False,
    downloader: Download | None = None,
    user_agent: str = DEFAULT_USER_AGENT,
    update_catalog: bool = True,
    invocation: list[str] | None = None,
) -> dict[str, object]:
    requested = normalize_hexagon_id(value)
    root = root.resolve()
    download = downloader or (
        lambda url, destination, headers: curl_download(
            url, destination, headers, user_agent=user_agent
        )
    )
    root.mkdir(parents=True, exist_ok=True)
    (root / "items" / "hexagon").mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=".fetch-hexagon-", dir=root) as temporary_raw:
        temporary = Path(temporary_raw)

        # An unversioned request is resolved to the current version through the
        # API, so the item is always filed under an exact version.
        fresh_work: Path | None = None
        fresh_network: dict[str, object] = {}
        versioned_request = bool(VERSION.search(requested))
        version_id = requested
        cached_item = root / "items" / "hexagon" / item_key(requested)
        if not versioned_request or force or not (cached_item / "item.json").is_file():
            fresh_work = temporary / "work.json"
            fresh_network = download(
                f"{HEXAGON_BASE}/api/v1/works/{requested}", fresh_work, temporary / "work.headers"
            )
            work = read_work(fresh_work)
            version_id = str(work.get("versionId") or "")
            if not HEXAGON_ID.fullmatch(version_id) or not VERSION.search(version_id):
                raise RuntimeError(f"Hexagon record for {requested} has no versioned identifier")
            if versioned_request and version_id.casefold() != requested.casefold():
                raise RuntimeError(f"Hexagon returned {version_id} for requested {requested}")

        key = item_key(version_id)
        item = root / "items" / "hexagon" / key
        metadata_path = item / "item.json"
        previous: dict[str, object] = {}
        if metadata_path.is_file() and not force:
            previous = json.loads(metadata_path.read_text(encoding="utf-8"))
        previous_resources = previous.get("resources", {})
        resources = dict(previous_resources) if isinstance(previous_resources, dict) else {}
        extracted = list(previous.get("extracted_source_files", []))
        source_check = previous.get("source_check")
        downloaded_this_run = False

        # Stage the complete item, then commit it with same-filesystem renames,
        # exactly as tools/fetch_arxiv.py does.
        staged_item = temporary / "item"
        if item.exists() and metadata_path.is_file() and not force:
            shutil.copytree(item, staged_item)
        else:
            staged_item.mkdir()
        original = staged_item / "original"
        source = staged_item / "source"
        original.mkdir(parents=True, exist_ok=True)

        def final_path(staged_path: Path) -> str:
            return (item / staged_path.relative_to(staged_item)).relative_to(root).as_posix()

        def cached(name: str, stored: Path) -> None:
            entry = resources.get(name, {})
            entry = entry if isinstance(entry, dict) else {}
            resources[name] = {
                **entry,
                "status": "cached",
                "path": final_path(stored),
                "sha256": entry.get("sha256") if isinstance(entry.get("sha256"), str) else sha256(stored),
                "bytes": stored.stat().st_size,
            }

        def downloaded(name: str, stored: Path, network: dict[str, object]) -> None:
            resources[name] = {
                "status": "downloaded",
                "path": final_path(stored),
                "sha256": sha256(stored),
                "bytes": stored.stat().st_size,
                **network,
            }

        stored_work = original / "work.json"
        if stored_work.is_file() and not force:
            cached("work", stored_work)
        else:
            if fresh_work is None:
                fresh_work = temporary / "work.json"
                fresh_network = download(
                    f"{HEXAGON_BASE}/api/v1/works/{version_id}", fresh_work, temporary / "work.headers"
                )
            read_work(fresh_work)
            shutil.copy2(fresh_work, stored_work)
            downloaded("work", stored_work, fresh_network)
            downloaded_this_run = True
        work = read_work(stored_work)
        digests = published_digests(work)

        stored_bibtex = original / "citation.bib"
        if stored_bibtex.is_file() and not force:
            cached("bibtex", stored_bibtex)
        else:
            bibtex_download = temporary / "citation.bib"
            network = download(
                f"{HEXAGON_BASE}/api/bibtex/{version_id}", bibtex_download, temporary / "bibtex.headers"
            )
            if not bibtex_download.read_text(encoding="utf-8").lstrip().startswith("@"):
                raise RuntimeError("Hexagon BibTeX download did not return a BibTeX entry")
            shutil.copy2(bibtex_download, stored_bibtex)
            downloaded("bibtex", stored_bibtex, network)
            downloaded_this_run = True

        if want_source:
            existing_sources = sorted(original.glob("source.*"))
            if existing_sources and not force:
                cached("source", existing_sources[0])
            else:
                source_download = temporary / "source.download"
                network = download(
                    f"{HEXAGON_BASE}/src/{version_id}", source_download, temporary / "source.headers"
                )
                stored_source, extracted = install_source(source_download, original, source)
                source_check = verify_source(source, digests["source"])
                downloaded("source", stored_source, network)
                downloaded_this_run = True

        if want_pdf:
            stored_pdf = original / "paper.pdf"
            if stored_pdf.exists() and not force:
                cached("pdf", stored_pdf)
            else:
                pdf_download = temporary / "paper.pdf"
                network = download(
                    f"{HEXAGON_BASE}/pdf/{version_id}", pdf_download, temporary / "pdf.headers"
                )
                with pdf_download.open("rb") as handle:
                    if not handle.read(5).startswith(b"%PDF-"):
                        raise RuntimeError("Hexagon PDF download did not return a PDF")
                expected = set(digests["paper"].values())
                if expected and sha256(pdf_download) not in expected:
                    raise RuntimeError("Hexagon PDF does not match its published SHA-256")
                shutil.copy2(pdf_download, stored_pdf)
                downloaded("pdf", stored_pdf, network)
                resources["pdf"]["published_sha256_checked"] = bool(expected)
                downloaded_this_run = True

        checked_at = datetime.now().astimezone().isoformat(timespec="seconds")
        carried = {
            name: previous[name]
            for name in (
                "bibliographic_identity",
                "metadata_provenance",
                "aliases",
                "derivatives",
                "citations",
                "citation_count",
                "search_text",
                "metadata_refreshed_at",
            )
            if name in previous
        }
        # The declaration follows the freshest record seen: withdrawal is a
        # record-level change that does not create a new version.
        current = declaration(read_work(fresh_work) if fresh_work is not None else work)
        payload: dict[str, object] = {
            **carried,
            "schema_version": 2,
            "id": f"hexagon:{key}",
            "kind": "hexagon",
            "key": key,
            "hexagon_id": version_id,
            "requested_id": requested,
            "versioned": True,
            "hexagon": current,
            "downloaded_at": (
                checked_at if downloaded_this_run else previous.get("downloaded_at", checked_at)
            ),
            "checked_at": checked_at,
            "item_path": item.relative_to(root).as_posix(),
            "resources": resources,
            "extracted_source_files": extracted,
            "source_check": source_check,
            "main_tex_candidates": main_tex_candidates(source),
            "invocation": invocation or ["tools/fetch_hexagon.py", value],
        }
        write_json_atomic(staged_item / "item.json", payload)

        previous_item = temporary / "previous-item"
        if item.exists():
            item.rename(previous_item)
        try:
            staged_item.rename(item)
        except BaseException:
            if previous_item.exists() and not item.exists():
                previous_item.rename(item)
            raise

    if downloaded_this_run or not isinstance(previous.get("bibliographic_identity"), dict):
        try:
            from tools.fetch_arxiv import describe_item
        except ModuleNotFoundError:
            from fetch_arxiv import describe_item
        describe_item(root, f"hexagon:{key}")

    catalog_result: dict[str, object] | None = None
    audit_result: dict[str, object] | None = None
    if update_catalog:
        catalog_result = refresh_catalog_items(root, [item])
        audit_result = audit_items(root, [item])

    warnings: list[str] = []
    if not versioned_request:
        warnings.append(f"unversioned request resolved to current version {version_id}")
    if current.get("status") != "published" or current.get("withdrawn_at"):
        warnings.append(f"record status is {current.get('status')!r}; check the withdrawal note")
    if current.get("authorship_mode") != "human" or current.get("human_understanding") != "full":
        warnings.append(
            "declared authorship "
            f"{current.get('authorship_mode')!r}, human understanding "
            f"{current.get('human_understanding')!r}"
        )
    return {
        "hexagon_id": version_id,
        "warnings": warnings,
        "item": item.relative_to(root).as_posix(),
        "main_tex_candidates": payload["main_tex_candidates"],
        "source_check": source_check,
        "resources": resources,
        "catalog": catalog_result,
        "audit": audit_result,
    }


def fetch_many(
    values: list[str],
    *,
    root: Path = Path("references"),
    want_source: bool = True,
    want_pdf: bool = True,
    force: bool = False,
    downloader: Download | None = None,
    user_agent: str = DEFAULT_USER_AGENT,
    invocation: list[str] | None = None,
) -> dict[str, object]:
    """Fetch known Hexagon works sequentially, then catalog the completed items."""
    if not values:
        raise ValueError("at least one Hexagon identifier is required")
    # Reject a malformed batch before making any network request or filesystem change.
    normalized = [normalize_hexagon_id(value) for value in values]
    root = root.resolve()
    results: list[dict[str, object]] = []
    try:
        for hexagon_id in normalized:
            results.append(
                fetch(
                    hexagon_id,
                    root=root,
                    want_source=want_source,
                    want_pdf=want_pdf,
                    force=force,
                    downloader=downloader,
                    user_agent=user_agent,
                    update_catalog=False,
                    invocation=invocation or ["tools/fetch_hexagon.py", *values],
                )
            )
    finally:
        completed_items = [root / str(result["item"]) for result in results]
        if completed_items:
            catalog_result = refresh_catalog_items(root, completed_items)

    audit_result = audit_items(root, completed_items)
    return {"items": results, "catalog": catalog_result, "audit": audit_result}


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "File known Hexagon works by sequential direct record/source/PDF download; "
            "performs no search."
        )
    )
    parser.add_argument(
        "identifiers",
        nargs="+",
        help="one or more Hexagon identifiers (hexagon:2610.00392v2 or bare) or hexagonmath.org URLs",
    )
    parser.add_argument("--root", type=Path, default=Path("references"))
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--source-only", action="store_true")
    selection.add_argument("--pdf-only", action="store_true")
    parser.add_argument("--force", action="store_true", help="replace this exact local item")
    parser.add_argument(
        "--user-agent",
        default=DEFAULT_USER_AGENT,
        help="HTTP User-Agent; may also be set with RESEARCH_HARNESS_USER_AGENT",
    )
    args = parser.parse_args()

    common = {
        "root": args.root,
        "want_source": not args.pdf_only,
        "want_pdf": not args.source_only,
        "force": args.force,
        "user_agent": args.user_agent,
        "invocation": ["tools/fetch_hexagon.py", *sys.argv[1:]],
    }
    if len(args.identifiers) == 1:
        result = fetch(args.identifiers[0], **common)
    else:
        result = fetch_many(args.identifiers, **common)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
