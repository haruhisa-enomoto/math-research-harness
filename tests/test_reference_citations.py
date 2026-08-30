from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from tools.reference_citations import (
    CitationLookupError,
    enrich_from_catalog,
    lookup_citations,
    merge_papers,
    openalex_paper,
    parse_source_query,
    semantic_citations,
    semantic_paper,
)


def s2_paper(
    paper_id: str,
    title: str,
    *,
    arxiv: str | None = None,
    doi: str | None = None,
    year: int = 2025,
    author: str = "An Author",
    citation_count: int = 0,
) -> dict[str, object]:
    external = {}
    if arxiv:
        external["ArXiv"] = arxiv
    if doi:
        external["DOI"] = doi
    return {
        "paperId": paper_id,
        "title": title,
        "authors": [{"authorId": "1", "name": author}],
        "year": year,
        "publicationDate": f"{year}-01-01",
        "externalIds": external,
        "url": f"https://www.semanticscholar.org/paper/{paper_id}",
        "venue": "",
        "citationCount": citation_count,
    }


def oa_paper(
    work_id: str,
    title: str,
    *,
    doi: str | None = None,
    year: int = 2025,
    author: str = "An Author",
    cited_by_count: int = 0,
) -> dict[str, object]:
    return {
        "id": f"https://openalex.org/{work_id}",
        "display_name": title,
        "title": title,
        "doi": f"https://doi.org/{doi}" if doi else None,
        "ids": {"openalex": f"https://openalex.org/{work_id}"},
        "publication_year": year,
        "publication_date": f"{year}-01-01",
        "authorships": [
            {
                "author": {
                    "id": "https://openalex.org/A1",
                    "display_name": author,
                }
            }
        ],
        "primary_location": None,
        "cited_by_count": cited_by_count,
    }


class MissedCitationRouter:
    """Mock the real coverage split seen for arXiv:2204.14182."""

    target = s2_paper(
        "original-s2",
        "On non-counital Frobenius algebras",
        arxiv="2204.14182",
        doi="10.1142/S0219498825500185",
        year=2022,
        author="Amanda Hernandez",
        citation_count=1,
    )
    citing = s2_paper(
        "chirvasitu-s2",
        "Coassociative structures on self-injective algebras",
        arxiv="2509.21435",
        year=2025,
        author="Alexandru Chirvasitu",
    )
    openalex_target = oa_paper(
        "W4385606191",
        "On non-counital Frobenius algebras",
        doi="10.1142/S0219498825500185",
        year=2025,
        author="Amanda Hernandez",
        cited_by_count=0,
    )

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.headers_seen: list[tuple[str, dict[str, str]]] = []

    def __call__(
        self, url: str, headers: dict[str, str], _timeout: int
    ) -> dict[str, object]:
        self.calls.append(url)
        parsed = urlparse(url)
        self.headers_seen.append((parsed.netloc, dict(headers)))
        query = parse_qs(parsed.query)
        if parsed.netloc == "api.semanticscholar.org":
            if parsed.path.endswith("/citations"):
                self.assert_query(query, "offset", "0")
                return {
                    "offset": 0,
                    "data": [{"citingPaper": self.citing}],
                }
            return self.target
        if parsed.netloc == "api.openalex.org":
            if query.get("filter") == ["cites:W4385606191"]:
                return {
                    "meta": {
                        "count": 0,
                        "next_cursor": None,
                    },
                    "results": [],
                }
            if query.get("search"):
                return {
                    "meta": {"count": 1},
                    "results": [self.openalex_target],
                }
            return self.openalex_target
        raise AssertionError(f"unexpected URL: {url}")

    @staticmethod
    def assert_query(query: dict[str, list[str]], name: str, value: str) -> None:
        if query.get(name) != [value]:
            raise AssertionError(f"expected {name}={value}, got {query.get(name)}")


class ReferenceCitationTests(unittest.TestCase):
    def test_parses_arxiv_doi_urls_and_titles(self) -> None:
        self.assertEqual(
            parse_source_query("arXiv:2204.14182v3").arxiv_id,
            "2204.14182v3",
        )
        self.assertEqual(
            parse_source_query("https://arxiv.org/pdf/math/0000000v2.pdf").arxiv_id,
            "math/0000000v2",
        )
        self.assertEqual(
            parse_source_query("https://doi.org/10.1142/S0219498825500185").doi,
            "10.1142/s0219498825500185",
        )
        self.assertEqual(
            parse_source_query("An Exact Paper Title").title,
            "An Exact Paper Title",
        )

    def test_catalog_enriches_arxiv_query_with_title_and_doi(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_raw:
            root = Path(temporary_raw)
            (root / "CATALOG.json").write_text(
                """
                {
                  "items": [{
                    "id": "arxiv:2204.14182v3",
                    "bibliographic_identity": {
                      "arxiv_id": "2204.14182v3",
                      "doi": "10.1142/S0219498825500185",
                      "title": "On non-counital Frobenius algebras"
                    }
                  }],
                  "external_sources": []
                }
                """,
                encoding="utf-8",
            )
            query = enrich_from_catalog(parse_source_query("2204.14182v1"), root)
            self.assertEqual(
                query.title,
                "On non-counital Frobenius algebras",
            )
            self.assertEqual(
                query.doi,
                "10.1142/s0219498825500185",
            )

    def test_semantic_scholar_catches_real_miss_when_openalex_has_zero(self) -> None:
        router = MissedCitationRouter()
        with tempfile.TemporaryDirectory() as temporary_raw:
            result = lookup_citations(
                "arxiv:2204.14182v3",
                root=Path(temporary_raw),
                requester=router,
            )

        self.assertTrue(result["complete"])
        self.assertEqual(result["citation_count"], 1)
        citation = result["citations"][0]
        self.assertEqual(citation["arxiv_id"], "2509.21435")
        self.assertEqual(
            citation["title"],
            "Coassociative structures on self-injective algebras",
        )
        self.assertEqual(
            citation["sources"],
            ["semantic-scholar"],
        )
        reports = result["provider_reports"]
        self.assertEqual(
            reports["semantic-scholar"]["reported_citation_count"],
            1,
        )
        self.assertEqual(
            reports["openalex"]["reported_citation_count"],
            0,
        )
        self.assertTrue(
            any(
                "search=On+non-counital+Frobenius+algebras" in call
                for call in router.calls
                if "api.openalex.org" in call
            )
        )

    def test_deduplicates_provider_records_by_doi(self) -> None:
        s2 = semantic_paper(
            s2_paper(
                "same-s2",
                "The Same Paper",
                doi="10.1000/example",
                author="First Author",
            )
        )
        oa = openalex_paper(
            oa_paper(
                "W123",
                "The Same Paper",
                doi="10.1000/example",
                author="First Author",
            )
        )
        merged = merge_papers([s2, oa])
        self.assertEqual(len(merged), 1)
        self.assertEqual(
            merged[0]["sources"],
            ["openalex", "semantic-scholar"],
        )
        self.assertEqual(
            merged[0]["semantic_scholar_id"],
            "same-s2",
        )
        self.assertEqual(
            merged[0]["openalex_id"],
            "https://openalex.org/W123",
        )

    def test_semantic_scholar_key_is_not_sent_to_openalex(self) -> None:
        router = MissedCitationRouter()
        with (
            tempfile.TemporaryDirectory() as temporary_raw,
            patch.dict(
                "os.environ",
                {"SEMANTIC_SCHOLAR_API_KEY": "s2-secret"},
            ),
        ):
            lookup_citations(
                "arxiv:2204.14182v3",
                root=Path(temporary_raw),
                requester=router,
            )
        semantic_headers = [
            headers
            for host, headers in router.headers_seen
            if host == "api.semanticscholar.org"
        ]
        openalex_headers = [
            headers
            for host, headers in router.headers_seen
            if host == "api.openalex.org"
        ]
        self.assertTrue(semantic_headers)
        self.assertTrue(openalex_headers)
        self.assertTrue(
            all(headers.get("x-api-key") == "s2-secret" for headers in semantic_headers)
        )
        self.assertTrue(all("x-api-key" not in headers for headers in openalex_headers))

    def test_semantic_pagination_and_explicit_cap(self) -> None:
        target = s2_paper(
            "target-s2",
            "Target",
            citation_count=2,
        )

        def requester(
            url: str, _headers: dict[str, str], _timeout: int
        ) -> dict[str, object]:
            query = parse_qs(urlparse(url).query)
            offset = int(query.get("offset", ["0"])[0])
            if offset == 0:
                return {
                    "data": [
                        {
                            "citingPaper": s2_paper(
                                "first",
                                "First Citation",
                                year=2024,
                            )
                        }
                    ],
                    "next": 1,
                }
            return {
                "data": [
                    {
                        "citingPaper": s2_paper(
                            "second",
                            "Second Citation",
                            year=2023,
                        )
                    }
                ]
            }

        citations, report = semantic_citations(
            target,
            requester=requester,
            headers={},
            timeout=1,
            max_results=0,
        )
        self.assertEqual(len(citations), 2)
        self.assertEqual(report["pages"], 2)
        self.assertTrue(report["complete"])

        citations, report = semantic_citations(
            target,
            requester=requester,
            headers={},
            timeout=1,
            max_results=1,
        )
        self.assertEqual(len(citations), 1)
        self.assertFalse(report["complete"])

    def test_provider_failure_is_loud_but_keeps_other_results(self) -> None:
        router = MissedCitationRouter()

        def requester(
            url: str, headers: dict[str, str], timeout: int
        ) -> dict[str, object]:
            if "api.openalex.org" in url:
                raise CitationLookupError("simulated provider outage")
            return router(url, headers, timeout)

        with tempfile.TemporaryDirectory() as temporary_raw:
            result = lookup_citations(
                "arxiv:2204.14182v3",
                root=Path(temporary_raw),
                requester=requester,
            )
        self.assertFalse(result["complete"])
        self.assertEqual(result["citation_count"], 1)
        self.assertEqual(
            result["provider_reports"]["openalex"]["status"],
            "error",
        )


if __name__ == "__main__":
    unittest.main()
