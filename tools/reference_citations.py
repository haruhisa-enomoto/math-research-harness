"""Discover papers that cite one identified source.

This is a discovery aid, not a citation certificate. It queries independent
scholarly graphs, merges their forward citations, and reports provider-level
coverage so a missing or truncated provider cannot silently look complete.

Examples:

    uv run python tools/reference_citations.py arxiv:2204.14182v3
    uv run python tools/reference_citations.py doi:10.1142/S0219498825500185
    uv run python tools/reference_citations.py "On non-counital Frobenius algebras"
    uv run python tools/reference_citations.py arxiv:2204.14182 --json
    uv run python tools/reference_citations.py hexagon:2610.00392v2

Semantic Scholar is queried first because it accepts arXiv identifiers
directly. Metadata resolved there and in the local catalog is then available
to OpenAlex, whose work lookup is strongest with a DOI or exact title.

A Hexagon (hexagonmath.org) work is resolved to its title, declared arXiv
identifier, and DOI through the local catalog or Hexagon's read-only API, then
looked up by those. The scholarly graphs may not index Hexagon at all, and
Hexagon offers no reverse-citation search, so the result says so.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time
import unicodedata
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen

from dotenv import load_dotenv

try:
    from tools.fetch_hexagon import HEXAGON_BASE, HEXAGON_HOSTS, normalize_hexagon_id
    from tools.reference_lookup import fold, identity, load_catalog
except ModuleNotFoundError:  # Direct execution starts with tools/ on sys.path.
    from fetch_hexagon import HEXAGON_BASE, HEXAGON_HOSTS, normalize_hexagon_id
    from reference_lookup import fold, identity, load_catalog

SEMANTIC_SCHOLAR_BASE = "https://api.semanticscholar.org/graph/v1"
OPENALEX_BASE = "https://api.openalex.org"
PROVIDERS = ("semantic-scholar", "openalex")
DEFAULT_USER_AGENT = os.environ.get(
    "RESEARCH_HARNESS_USER_AGENT",
    "math-research-harness/0.1 (citation discovery helper)",
)
ARXIV_ID = re.compile(
    r"(?:[a-z][a-z0-9.-]*/)?\d{4}\.\d{4,5}(?:v\d+)?"
    r"|[a-z][a-z0-9.-]*/\d{7}(?:v\d+)?",
    re.I,
)
ARXIV_VERSION = re.compile(r"v\d+$", re.I)
DOI = re.compile(r"10\.\d{4,9}/\S+", re.I)
SEMANTIC_FIELDS = (
    "title,authors,year,publicationDate,externalIds,url,venue,citationCount"
)
OPENALEX_SELECT = (
    "id,display_name,title,doi,ids,publication_year,publication_date,"
    "authorships,primary_location,cited_by_count"
)
# Private provider keys live in the git-ignored `.env` at the repository root.
DOTENV_PATH = Path(__file__).resolve().parents[1] / ".env"
MAX_ATTEMPTS = 6
MAX_RETRY_DELAY = 60.0
# Semantic Scholar allows one request per second for each API key.
MIN_REQUEST_INTERVAL = {"api.semanticscholar.org": 1.1}
_last_request: dict[str, float] = {}
RETRY_HINT = re.compile(r"retry in (\d+(?:\.\d+)?)\s*s", re.I)
TEX_COMMAND = re.compile(r"\\([a-z]+)")
GREEK_NAMES = frozenset(
    "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi "
    "omicron pi rho sigma tau upsilon phi chi psi omega".split()
)


HEXAGON_COVERAGE_NOTE = (
    " The target is a Hexagon work: the providers were queried by its title"
    " and any submitter-declared arXiv ID or DOI, may not index Hexagon, and"
    " cannot see Hexagon works that cite it."
)


class CitationLookupError(RuntimeError):
    """A provider or identity-resolution failure that should be reported."""


@dataclass(frozen=True)
class SourceQuery:
    raw: str
    arxiv_id: str | None = None
    doi: str | None = None
    title: str | None = None
    hexagon_id: str | None = None


JsonRequester = Callable[[str, dict[str, str], int], dict[str, object]]


def unversioned_arxiv(value: str) -> str:
    return ARXIV_VERSION.sub("", value.strip())


def normalize_doi(value: str) -> str:
    candidate = value.strip()
    if candidate.casefold().startswith("doi:"):
        candidate = candidate.split(":", 1)[1].strip()
    if candidate.casefold().startswith(("https://doi.org/", "http://doi.org/")):
        candidate = urlparse(candidate).path.lstrip("/")
    match = DOI.fullmatch(candidate.rstrip(".,;"))
    if not match:
        raise ValueError(f"invalid DOI: {value!r}")
    return match.group(0).casefold()


def arxiv_from_value(value: str) -> str | None:
    candidate = value.strip()
    if candidate.casefold().startswith("arxiv:"):
        candidate = candidate.split(":", 1)[1].strip()
    elif "://" in candidate:
        parsed = urlparse(candidate)
        if parsed.netloc.casefold() not in {
            "arxiv.org",
            "www.arxiv.org",
            "export.arxiv.org",
        }:
            return None
        path = parsed.path.strip("/")
        for prefix in ("abs/", "pdf/", "e-print/"):
            if path.startswith(prefix):
                candidate = path[len(prefix) :]
                break
        candidate = candidate.removesuffix(".pdf")
    return candidate if ARXIV_ID.fullmatch(candidate) else None


def hexagon_from_value(value: str) -> str | None:
    """A Hexagon identifier, only when the value says Hexagon explicitly.

    Hexagon and modern arXiv identifiers share one shape, so a bare
    `2610.00392v2` stays an arXiv identifier here.
    """
    candidate = value.strip()
    if candidate.casefold().startswith("hexagon:"):
        return normalize_hexagon_id(candidate)
    if "://" in candidate and urlparse(candidate).netloc.casefold() in HEXAGON_HOSTS:
        return normalize_hexagon_id(candidate)
    return None


def parse_source_query(value: str) -> SourceQuery:
    raw = value.strip()
    if not raw:
        raise ValueError("empty source query")
    hexagon_id = hexagon_from_value(raw)
    if hexagon_id:
        return SourceQuery(raw=raw, hexagon_id=hexagon_id)
    arxiv_id = arxiv_from_value(raw)
    if arxiv_id:
        return SourceQuery(raw=raw, arxiv_id=arxiv_id)
    if raw.casefold().startswith(
        ("doi:", "https://doi.org/", "http://doi.org/")
    ) or DOI.fullmatch(raw):
        return SourceQuery(raw=raw, doi=normalize_doi(raw))
    return SourceQuery(raw=raw, title=raw)


def enrich_from_catalog(query: SourceQuery, root: Path) -> SourceQuery:
    """Fill missing identifiers/title from one exact local catalog match."""
    if not (root / "CATALOG.json").is_file():
        return query
    matches: list[dict[str, object]] = []
    for record in load_catalog(root):
        bibliography = identity(record)
        recorded_arxiv = str(bibliography.get("arxiv_id") or "")
        recorded_doi = str(bibliography.get("doi") or "")
        recorded_title = str(bibliography.get("title") or "")
        recorded_persistent = str(bibliography.get("persistent_identifier") or "")
        if query.hexagon_id:
            if recorded_persistent.casefold().startswith("hexagon:") and unversioned_arxiv(
                recorded_persistent.split(":", 1)[1]
            ) == unversioned_arxiv(query.hexagon_id):
                matches.append(bibliography)
        elif query.arxiv_id and recorded_arxiv:
            if unversioned_arxiv(recorded_arxiv) == unversioned_arxiv(query.arxiv_id):
                matches.append(bibliography)
        elif query.doi and recorded_doi:
            try:
                if normalize_doi(recorded_doi) == query.doi:
                    matches.append(bibliography)
            except ValueError:
                continue
        elif (
            query.title and recorded_title and fold(recorded_title) == fold(query.title)
        ):
            matches.append(bibliography)
    if not matches:
        return query
    bibliography = matches[0]
    arxiv_id = query.arxiv_id or str(bibliography.get("arxiv_id") or "") or None
    doi = query.doi
    if not doi and bibliography.get("doi"):
        try:
            doi = normalize_doi(str(bibliography["doi"]))
        except ValueError:
            pass
    title = query.title or str(bibliography.get("title") or "") or None
    return replace(query, arxiv_id=arxiv_id, doi=doi, title=title)


def resolve_hexagon(
    query: SourceQuery,
    *,
    requester: JsonRequester,
    headers: dict[str, str],
    timeout: int,
) -> SourceQuery:
    """Fill title and declared identifiers of a Hexagon work from its public record."""
    if not query.hexagon_id or query.title:
        return query
    raw = requester(f"{HEXAGON_BASE}/api/v1/works/{query.hexagon_id}", headers, timeout)
    work = raw.get("work") if isinstance(raw, dict) else None
    if not isinstance(work, dict) or not work.get("title"):
        raise CitationLookupError(f"Hexagon record for {query.hexagon_id} has no title")
    doi = query.doi
    if not doi and work.get("doi"):
        try:
            doi = normalize_doi(str(work["doi"]))
        except ValueError:
            pass
    arxiv_id = query.arxiv_id or (str(work["arxivId"]) if work.get("arxivId") else None)
    return replace(query, title=str(work["title"]), arxiv_id=arxiv_id, doi=doi)


def wait_for_turn(host: str) -> None:
    """Space requests to one provider by its minimum interval."""
    interval = MIN_REQUEST_INTERVAL.get(host, 0.0)
    if host in _last_request:
        remaining = interval - (time.monotonic() - _last_request[host])
        if remaining > 0:
            time.sleep(remaining)
    _last_request[host] = time.monotonic()


def retry_delay(
    attempt: int, retry_after: str | None = None, detail: str = ""
) -> float:
    """Back off exponentially, honouring any longer wait the provider asks for."""
    delay = float(2 ** (attempt + 1))
    hints = [retry_after or ""]
    if match := RETRY_HINT.search(detail):
        hints.append(match.group(1))
    for hint in hints:
        try:
            delay = max(delay, float(hint))
        except ValueError:
            continue
    return min(delay, MAX_RETRY_DELAY)


def request_json(url: str, headers: dict[str, str], timeout: int) -> dict[str, object]:
    request = Request(url, headers=headers)
    host = urlparse(url).netloc
    for attempt in range(MAX_ATTEMPTS):
        last_attempt = attempt == MAX_ATTEMPTS - 1
        wait_for_turn(host)
        try:
            with urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8")
            break
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace").strip()[:500]
            retryable = error.code == 429 or 500 <= error.code < 600
            if retryable and not last_attempt:
                delay = retry_delay(attempt, error.headers.get("Retry-After"), detail)
                print(
                    f"{host}: HTTP {error.code}; retrying in {delay:.0f} s "
                    f"(attempt {attempt + 2}/{MAX_ATTEMPTS})",
                    file=sys.stderr,
                )
                time.sleep(delay)
                continue
            raise CitationLookupError(
                f"HTTP {error.code} from provider: {detail or error.reason}"
            ) from error
        except URLError as error:
            if not last_attempt:
                time.sleep(retry_delay(attempt))
                continue
            raise CitationLookupError(
                f"provider request failed: {error.reason}"
            ) from error
    else:  # pragma: no cover - the loop always breaks or raises.
        raise CitationLookupError("provider request retry loop exhausted")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as error:
        raise CitationLookupError(f"provider returned invalid JSON: {error}") from error
    if not isinstance(payload, dict):
        raise CitationLookupError("provider returned a non-object JSON response")
    return payload


def with_query(url: str, params: dict[str, object]) -> str:
    useful = {key: value for key, value in params.items() if value not in (None, "")}
    return f"{url}?{urlencode(useful)}" if useful else url


def author_names(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    names: list[str] = []
    for entry in raw:
        if isinstance(entry, dict):
            name = entry.get("name") or entry.get("display_name")
            if name:
                names.append(str(name))
    return names


def preferred_url(paper: dict[str, object]) -> str | None:
    arxiv_id = paper.get("arxiv_id")
    if arxiv_id:
        return f"https://arxiv.org/abs/{unversioned_arxiv(str(arxiv_id))}"
    doi = paper.get("doi")
    if doi:
        return f"https://doi.org/{doi}"
    return str(paper.get("url") or "") or None


def semantic_paper(raw: dict[str, object]) -> dict[str, object]:
    external = raw.get("externalIds")
    external_ids = external if isinstance(external, dict) else {}
    doi = None
    if external_ids.get("DOI"):
        try:
            doi = normalize_doi(str(external_ids["DOI"]))
        except ValueError:
            pass
    paper: dict[str, object] = {
        "title": str(raw.get("title") or "").strip() or None,
        "authors": author_names(raw.get("authors")),
        "year": (raw.get("year") if isinstance(raw.get("year"), int) else None),
        "publication_date": raw.get("publicationDate"),
        "venue": raw.get("venue"),
        "arxiv_id": str(external_ids.get("ArXiv") or "") or None,
        "doi": doi,
        "url": str(raw.get("url") or "") or None,
        "semantic_scholar_id": (str(raw.get("paperId") or "") or None),
        "openalex_id": None,
        "sources": ["semantic-scholar"],
    }
    paper["url"] = preferred_url(paper)
    return paper


def arxiv_from_openalex(raw: dict[str, object]) -> str | None:
    location = raw.get("primary_location")
    if not isinstance(location, dict):
        return None
    for field in ("landing_page_url", "pdf_url"):
        value = location.get(field)
        if value and (arxiv_id := arxiv_from_value(str(value))):
            return arxiv_id
    return None


def openalex_paper(raw: dict[str, object]) -> dict[str, object]:
    authorships = raw.get("authorships")
    authors: list[str] = []
    if isinstance(authorships, list):
        for authorship in authorships:
            if not isinstance(authorship, dict) or not isinstance(
                authorship.get("author"), dict
            ):
                continue
            name = authorship["author"].get("display_name")
            if name:
                authors.append(str(name))
    doi = None
    if raw.get("doi"):
        try:
            doi = normalize_doi(str(raw["doi"]))
        except ValueError:
            pass
    paper: dict[str, object] = {
        "title": (
            str(raw.get("display_name") or raw.get("title") or "").strip() or None
        ),
        "authors": authors,
        "year": (
            raw.get("publication_year")
            if isinstance(raw.get("publication_year"), int)
            else None
        ),
        "publication_date": raw.get("publication_date"),
        "venue": None,
        "arxiv_id": arxiv_from_openalex(raw),
        "doi": doi,
        "url": str(raw.get("id") or "") or None,
        "semantic_scholar_id": None,
        "openalex_id": str(raw.get("id") or "") or None,
        "sources": ["openalex"],
    }
    location = raw.get("primary_location")
    if isinstance(location, dict) and isinstance(location.get("source"), dict):
        paper["venue"] = location["source"].get("display_name")
    paper["url"] = preferred_url(paper)
    return paper


def greek_word(character: str) -> str:
    name = unicodedata.name(character, "")
    if not name.startswith("GREEK SMALL LETTER "):
        return character
    word = name.removeprefix("GREEK SMALL LETTER ").lower().replace("lamda", "lambda")
    return f" {word.removeprefix('final ')} "


def tex_word(command: str) -> str:
    word = command.removeprefix("var")
    return f" {word} " if word in GREEK_NAMES else " "


def title_words(value: str) -> list[str]:
    """Words of a title with markup, TeX commands, and Greek letters normalized.

    Providers render the same title as `$\\zeta$-functions`, `<i>ζ</i>-functions`,
    or `𝜁-functions`; all of these become the words `zeta functions`.
    """
    text = fold(re.sub(r"<[^>]+>", " ", html.unescape(value)))
    text = TEX_COMMAND.sub(lambda match: tex_word(match.group(1)), text)
    text = "".join(greek_word(character) for character in text)
    return re.findall(r"[^\W_]+", text)


def title_key(value: str) -> str:
    """Compare titles while ignoring spacing, punctuation, and notation."""
    return "".join(title_words(value))


def search_text(value: str) -> str:
    """Plain words for provider search, where `?`, `*`, `,`, `-` are syntax.

    Greek letters are left out: a provider may index `Λ` or `$\\Lambda$`,
    so the spelled name `lambda` would only hurt recall. Matching still
    compares them through `title_key`.
    """
    return " ".join(word for word in title_words(value) if word not in GREEK_NAMES)


def exact_title(candidates: list[dict[str, object]], title: str) -> dict[str, object]:
    wanted = title_key(title)
    exact = [
        candidate
        for candidate in candidates
        if wanted
        and title_key(
            str(candidate.get("title") or candidate.get("display_name") or "")
        )
        == wanted
    ]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        # Duplicate/version records are common. Prefer the record with the
        # richest citation linkage, then stable external identifiers.
        return max(
            exact,
            key=lambda item: (
                item.get("cited_by_count") or item.get("citationCount") or 0,
                int(bool(item.get("externalIds") or item.get("doi"))),
                int(bool(item.get("paperId") or item.get("id"))),
            ),
        )
    shown = "; ".join(
        str(item.get("title") or item.get("display_name") or "")
        for item in candidates[:3]
    )
    raise CitationLookupError(
        f"no exact title match for {title!r}; nearest results: {shown or 'none'}"
    )


def semantic_target(
    query: SourceQuery,
    *,
    requester: JsonRequester,
    headers: dict[str, str],
    timeout: int,
) -> tuple[dict[str, object], dict[str, object]]:
    paper_id = None
    if query.arxiv_id:
        paper_id = f"ARXIV:{unversioned_arxiv(query.arxiv_id)}"
    elif query.doi:
        paper_id = f"DOI:{query.doi}"
    if paper_id:
        url = with_query(
            f"{SEMANTIC_SCHOLAR_BASE}/paper/{quote(paper_id, safe='')}",
            {"fields": SEMANTIC_FIELDS},
        )
        try:
            raw = requester(url, headers, timeout)
            return raw, semantic_paper(raw)
        except CitationLookupError:
            if not query.title:
                raise
    if not query.title:
        raise CitationLookupError("Semantic Scholar needs an arXiv ID, DOI, or title")
    url = with_query(
        f"{SEMANTIC_SCHOLAR_BASE}/paper/search",
        {
            "query": search_text(query.title),
            "limit": 10,
            "fields": SEMANTIC_FIELDS,
        },
    )
    payload = requester(url, headers, timeout)
    data = payload.get("data")
    candidates = (
        [item for item in data if isinstance(item, dict)]
        if isinstance(data, list)
        else []
    )
    raw = exact_title(candidates, query.title)
    return raw, semantic_paper(raw)


def semantic_citations(
    target_raw: dict[str, object],
    *,
    requester: JsonRequester,
    headers: dict[str, str],
    timeout: int,
    max_results: int,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    paper_id = str(target_raw.get("paperId") or "")
    if not paper_id:
        raise CitationLookupError("Semantic Scholar target has no paperId")
    offset = 0
    citations: list[dict[str, object]] = []
    pages = 0
    complete = True
    while True:
        remaining = max_results - len(citations) if max_results else 1000
        if max_results and remaining <= 0:
            complete = False
            break
        batch = min(1000, remaining) if max_results else 1000
        url = with_query(
            (f"{SEMANTIC_SCHOLAR_BASE}/paper/{quote(paper_id, safe='')}/citations"),
            {
                "fields": SEMANTIC_FIELDS,
                "offset": offset,
                "limit": batch,
            },
        )
        payload = requester(url, headers, timeout)
        pages += 1
        data = payload.get("data")
        rows = data if isinstance(data, list) else []
        for row in rows:
            if isinstance(row, dict) and isinstance(row.get("citingPaper"), dict):
                citations.append(semantic_paper(row["citingPaper"]))
        next_offset = payload.get("next")
        if not isinstance(next_offset, int):
            break
        if max_results and len(citations) >= max_results:
            complete = False
            break
        if next_offset <= offset:
            raise CitationLookupError("Semantic Scholar pagination did not advance")
        offset = next_offset
    return citations, {
        "status": "ok",
        "target_id": paper_id,
        "reported_citation_count": target_raw.get("citationCount"),
        "retrieved": len(citations),
        "pages": pages,
        "complete": complete,
    }


def openalex_url(path: str, params: dict[str, object]) -> str:
    api_key = os.environ.get("OPENALEX_API_KEY")
    if api_key:
        params = {**params, "api_key": api_key}
    return with_query(f"{OPENALEX_BASE}{path}", params)


def openalex_title_candidates(
    title: str,
    *,
    requester: JsonRequester,
    headers: dict[str, str],
    timeout: int,
) -> list[dict[str, object]]:
    """Union general search with title-only search.

    General search can bury a short title under popular works; the title
    filter finds it, while general search still surfaces duplicate records.
    """
    text = search_text(title)
    if not text:
        raise CitationLookupError(f"title has no searchable words: {title!r}")
    candidates: dict[str, dict[str, object]] = {}
    for search in ({"search": text}, {"filter": f"title.search:{text}"}):
        payload = requester(
            openalex_url(
                "/works",
                {**search, "per_page": 25, "select": OPENALEX_SELECT},
            ),
            headers,
            timeout,
        )
        data = payload.get("results")
        for item in data if isinstance(data, list) else []:
            if isinstance(item, dict):
                candidates.setdefault(str(item.get("id") or len(candidates)), item)
    return list(candidates.values())


def openalex_target(
    query: SourceQuery,
    *,
    requester: JsonRequester,
    headers: dict[str, str],
    timeout: int,
) -> tuple[dict[str, object], dict[str, object]]:
    errors: list[str] = []
    if query.title:
        try:
            candidates = openalex_title_candidates(
                query.title,
                requester=requester,
                headers=headers,
                timeout=timeout,
            )
            raw = exact_title(candidates, query.title)
            return raw, openalex_paper(raw)
        except CitationLookupError as error:
            errors.append(str(error))
    dois = [query.doi] if query.doi else []
    if query.arxiv_id:
        # arXiv registers a DataCite DOI for every preprint.
        dois.append(f"10.48550/arxiv.{unversioned_arxiv(query.arxiv_id)}")
    for doi in dois:
        encoded = quote(f"https://doi.org/{doi}", safe=":/")
        try:
            raw = requester(
                openalex_url(f"/works/{encoded}", {"select": OPENALEX_SELECT}),
                headers,
                timeout,
            )
            return raw, openalex_paper(raw)
        except CitationLookupError as error:
            errors.append(f"doi:{doi}: {error}")
    if errors:
        raise CitationLookupError("; ".join(errors))
    raise CitationLookupError("OpenAlex needs a DOI, an arXiv ID, or an exact title")


def openalex_citations(
    target_raw: dict[str, object],
    *,
    requester: JsonRequester,
    headers: dict[str, str],
    timeout: int,
    max_results: int,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    target_id = str(target_raw.get("id") or "").rsplit("/", 1)[-1]
    if not re.fullmatch(r"W\d+", target_id):
        raise CitationLookupError(f"invalid OpenAlex work ID: {target_id!r}")
    cursor = "*"
    citations: list[dict[str, object]] = []
    pages = 0
    reported_count: object = target_raw.get("cited_by_count")
    complete = True
    while True:
        remaining = max_results - len(citations) if max_results else 100
        if max_results and remaining <= 0:
            complete = False
            break
        batch = min(100, remaining) if max_results else 100
        payload = requester(
            openalex_url(
                "/works",
                {
                    "filter": f"cites:{target_id}",
                    "per_page": batch,
                    "cursor": cursor,
                    "select": OPENALEX_SELECT,
                },
            ),
            headers,
            timeout,
        )
        pages += 1
        meta = payload.get("meta")
        if isinstance(meta, dict) and reported_count is None:
            reported_count = meta.get("count")
        data = payload.get("results")
        rows = data if isinstance(data, list) else []
        citations.extend(openalex_paper(row) for row in rows if isinstance(row, dict))
        next_cursor = meta.get("next_cursor") if isinstance(meta, dict) else None
        if not rows or not next_cursor:
            break
        if max_results and len(citations) >= max_results:
            complete = False
            break
        if next_cursor == cursor:
            raise CitationLookupError("OpenAlex pagination did not advance")
        cursor = str(next_cursor)
    return citations, {
        "status": "ok",
        "target_id": target_id,
        "reported_citation_count": reported_count,
        "retrieved": len(citations),
        "pages": pages,
        "complete": complete,
    }


def enrich_query_from_paper(
    query: SourceQuery, paper: dict[str, object]
) -> SourceQuery:
    return replace(
        query,
        arxiv_id=(
            query.arxiv_id
            or (str(paper.get("arxiv_id")) if paper.get("arxiv_id") else None)
        ),
        doi=(query.doi or (str(paper.get("doi")) if paper.get("doi") else None)),
        title=(
            query.title or (str(paper.get("title")) if paper.get("title") else None)
        ),
    )


def paper_keys(paper: dict[str, object]) -> list[str]:
    keys: list[str] = []
    if paper.get("doi"):
        keys.append(f"doi:{str(paper['doi']).casefold()}")
    if paper.get("arxiv_id"):
        keys.append("arxiv:" + unversioned_arxiv(str(paper["arxiv_id"])).casefold())
    title = fold(str(paper.get("title") or ""))
    year = paper.get("year")
    authors = paper.get("authors")
    first_author = (
        fold(str(authors[0])) if isinstance(authors, list) and authors else ""
    )
    if title and (year or first_author):
        keys.append(f"title:{title}|{year or ''}|{first_author}")
    if paper.get("semantic_scholar_id"):
        keys.append(f"s2:{paper['semantic_scholar_id']}")
    if paper.get("openalex_id"):
        keys.append(f"oa:{paper['openalex_id']}")
    return keys


def merge_papers(papers: list[dict[str, object]]) -> list[dict[str, object]]:
    merged: list[dict[str, object]] = []
    key_to_index: dict[str, int] = {}
    for paper in papers:
        indices = {
            key_to_index[key] for key in paper_keys(paper) if key in key_to_index
        }
        if not indices:
            index = len(merged)
            merged.append(
                {
                    **paper,
                    "sources": sorted(set(paper.get("sources") or [])),
                }
            )
        else:
            index = min(indices)
            target = merged[index]
            for field, value in paper.items():
                if field == "sources":
                    target[field] = sorted(
                        set(target.get(field) or []) | set(value or [])
                    )
                elif (
                    field == "authors"
                    and value
                    and len(value) > len(target.get(field) or [])
                ):
                    target[field] = value
                elif not target.get(field) and value:
                    target[field] = value
            target["url"] = preferred_url(target)
        for key in paper_keys(merged[index]):
            key_to_index[key] = index
    return sorted(
        merged,
        key=lambda paper: (
            -(paper.get("year") if isinstance(paper.get("year"), int) else -1),
            fold(str(paper.get("title") or "")),
        ),
    )


def lookup_citations(
    value: str,
    *,
    root: Path = Path("references"),
    providers: tuple[str, ...] = PROVIDERS,
    max_results: int = 0,
    requester: JsonRequester = request_json,
    timeout: int = 60,
    user_agent: str = DEFAULT_USER_AGENT,
) -> dict[str, object]:
    query = enrich_from_catalog(parse_source_query(value), root)
    common_headers = {
        "User-Agent": user_agent,
        "Accept": "application/json",
    }
    query = resolve_hexagon(
        query, requester=requester, headers=common_headers, timeout=timeout
    )
    semantic_headers = dict(common_headers)
    semantic_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
    if semantic_key:
        semantic_headers["x-api-key"] = semantic_key

    reports: dict[str, object] = {}
    targets: dict[str, object] = {}
    papers: list[dict[str, object]] = []
    for provider in PROVIDERS:
        if provider not in providers:
            continue
        try:
            if provider == "semantic-scholar":
                raw, target = semantic_target(
                    query,
                    requester=requester,
                    headers=semantic_headers,
                    timeout=timeout,
                )
                citations, report = semantic_citations(
                    raw,
                    requester=requester,
                    headers=semantic_headers,
                    timeout=timeout,
                    max_results=max_results,
                )
            else:
                raw, target = openalex_target(
                    query,
                    requester=requester,
                    headers=common_headers,
                    timeout=timeout,
                )
                citations, report = openalex_citations(
                    raw,
                    requester=requester,
                    headers=common_headers,
                    timeout=timeout,
                    max_results=max_results,
                )
            targets[provider] = target
            reports[provider] = report
            papers.extend(citations)
            query = enrich_query_from_paper(query, target)
        except CitationLookupError as error:
            reports[provider] = {
                "status": "error",
                "error": str(error),
                "retrieved": 0,
                "complete": False,
            }

    citations = merge_papers(papers)
    complete = bool(reports) and all(
        isinstance(report, dict)
        and report.get("status") == "ok"
        and report.get("complete") is True
        for report in reports.values()
    )
    return {
        "query": asdict(query),
        "providers": list(providers),
        "provider_reports": reports,
        "resolved_targets": targets,
        "citation_count": len(citations),
        "citations": citations,
        "complete": complete,
        "coverage_note": (
            "Complete means every enabled provider paginated "
            "successfully; no scholarly graph guarantees complete "
            "citation coverage."
            + (HEXAGON_COVERAGE_NOTE if query.hexagon_id else "")
        ),
    }


def format_authors(authors: object) -> str:
    if not isinstance(authors, list) or not authors:
        return "(unattributed)"
    shown = ", ".join(str(author) for author in authors[:4])
    return shown + (" et al." if len(authors) > 4 else "")


def print_human(result: dict[str, object]) -> None:
    query = result["query"]
    assert isinstance(query, dict)
    target = (
        query.get("title")
        or query.get("arxiv_id")
        or query.get("doi")
        or query.get("raw")
    )
    print(f"Target: {target}")
    identifiers = []
    if query.get("hexagon_id"):
        identifiers.append(f"hexagon:{query['hexagon_id']}")
    if query.get("arxiv_id"):
        identifiers.append(f"arXiv:{query['arxiv_id']}")
    if query.get("doi"):
        identifiers.append(f"doi:{query['doi']}")
    if identifiers:
        print("Identifiers: " + " | ".join(identifiers))
    print("\nProvider coverage:")
    reports = result["provider_reports"]
    assert isinstance(reports, dict)
    for provider in result["providers"]:
        report = reports.get(provider, {})
        assert isinstance(report, dict)
        if report.get("status") == "ok":
            completeness = "complete" if report.get("complete") else "TRUNCATED"
            reported = report.get("reported_citation_count")
            count_text = (
                f", provider reports {reported}" if reported is not None else ""
            )
            print(
                f"  {provider}: "
                f"{report.get('retrieved', 0)} retrieved"
                f"{count_text}, {completeness}"
            )
        else:
            print(
                f"  {provider}: ERROR: "
                f"{report.get('error', 'unknown provider failure')}"
            )

    citations = result["citations"]
    assert isinstance(citations, list)
    print(f"\nForward citations after deduplication: {len(citations)}")
    for number, paper in enumerate(citations, start=1):
        assert isinstance(paper, dict)
        year = f" ({paper['year']})" if paper.get("year") else ""
        print(
            f"{number}. {format_authors(paper.get('authors'))}"
            f"{year}. {paper.get('title') or '(untitled)'}"
        )
        tags = []
        if paper.get("arxiv_id"):
            tags.append(f"arXiv:{paper['arxiv_id']}")
        if paper.get("doi"):
            tags.append(f"doi:{paper['doi']}")
        tags.append(
            "sources=" + ",".join(str(item) for item in paper.get("sources") or [])
        )
        print("   " + " | ".join(tags))
        if paper.get("url"):
            print(f"   {paper['url']}")
    print(f"\nCoverage warning: {result['coverage_note']}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=("Find forward citations through Semantic Scholar and OpenAlex."),
    )
    parser.add_argument(
        "source",
        help=("arXiv ID, DOI, hexagon:<id>, official identifier URL, or exact title"),
    )
    parser.add_argument("--root", type=Path, default=Path("references"))
    parser.add_argument(
        "--provider",
        action="append",
        choices=PROVIDERS,
        help="provider to query (repeatable; default: both)",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=0,
        help=(
            "cap results per provider and label the run incomplete (default: no cap)"
        ),
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="timeout per HTTP request in seconds",
    )
    parser.add_argument(
        "--user-agent",
        default=DEFAULT_USER_AGENT,
        help=("HTTP User-Agent; may also be set with RESEARCH_HARNESS_USER_AGENT"),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable JSON",
    )
    args = parser.parse_args()
    # Keys already in the environment take precedence over `.env`.
    load_dotenv(DOTENV_PATH)
    if args.max_results < 0:
        parser.error("--max-results must be nonnegative")
    if args.timeout < 1:
        parser.error("--timeout must be positive")
    providers = tuple(dict.fromkeys(args.provider or PROVIDERS))
    try:
        result = lookup_citations(
            args.source,
            root=args.root,
            providers=providers,
            max_results=args.max_results,
            timeout=args.timeout,
            user_agent=args.user_agent,
        )
    except (ValueError, CitationLookupError) as error:
        parser.error(str(error))
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print_human(result)
    if not result["complete"]:
        sys.stdout.flush()
        print(
            "citation lookup incomplete; inspect provider errors or truncation",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
