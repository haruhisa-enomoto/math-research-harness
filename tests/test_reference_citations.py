from __future__ import annotations

import io
import os
import tempfile
import unittest
from email.message import Message
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

from tools.reference_citations import (
    CitationLookupError,
    enrich_from_catalog,
    exact_title,
    lookup_citations,
    merge_papers,
    openalex_paper,
    parse_source_query,
    request_json,
    resolve_hexagon,
    retry_delay,
    search_text,
    semantic_citations,
    semantic_paper,
    wait_for_turn,
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
    def setUp(self) -> None:
        # Keep any provider keys from the calling shell out of every test.
        environment = patch.dict(os.environ)
        environment.start()
        self.addCleanup(environment.stop)
        os.environ.pop("SEMANTIC_SCHOLAR_API_KEY", None)
        os.environ.pop("OPENALEX_API_KEY", None)

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

    def test_hexagon_queries_need_an_explicit_prefix_or_url(self) -> None:
        self.assertEqual(
            parse_source_query("hexagon:2099.00392v2").hexagon_id,
            "2099.00392v2",
        )
        self.assertEqual(
            parse_source_query("https://hexagonmath.org/2099.00392v2").hexagon_id,
            "2099.00392v2",
        )
        # The shared identifier shape stays arXiv unless Hexagon is named.
        bare = parse_source_query("2099.00392v2")
        self.assertEqual(bare.arxiv_id, "2099.00392v2")
        self.assertIsNone(bare.hexagon_id)

    def test_catalog_enriches_hexagon_query_by_persistent_identifier(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_raw:
            root = Path(temporary_raw)
            (root / "CATALOG.json").write_text(
                """
                {
                  "items": [{
                    "id": "arxiv:2099.00392v2",
                    "bibliographic_identity": {
                      "arxiv_id": "2099.00392v2",
                      "title": "An unrelated arXiv paper"
                    }
                  }, {
                    "id": "hexagon:2099.00392v2",
                    "bibliographic_identity": {
                      "persistent_identifier": "hexagon:2099.00392v2",
                      "title": "Determinants over finite fields"
                    }
                  }],
                  "external_sources": []
                }
                """,
                encoding="utf-8",
            )
            query = enrich_from_catalog(parse_source_query("hexagon:2099.00392v1"), root)
            self.assertEqual(query.title, "Determinants over finite fields")
            self.assertIsNone(query.arxiv_id)

    def test_hexagon_record_supplies_title_and_declared_identifiers(self) -> None:
        calls: list[str] = []

        def requester(url: str, _headers: dict[str, str], _timeout: int) -> dict[str, object]:
            calls.append(url)
            return {
                "work": {
                    "title": "Determinants over finite fields",
                    "arxivId": "2099.11111v1",
                    "doi": None,
                }
            }

        query = resolve_hexagon(
            parse_source_query("hexagon:2099.00392v2"),
            requester=requester,
            headers={},
            timeout=5,
        )
        self.assertEqual(calls, ["https://hexagonmath.org/api/v1/works/2099.00392v2"])
        self.assertEqual(query.title, "Determinants over finite fields")
        self.assertEqual(query.arxiv_id, "2099.11111v1")

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
                "search=on+non+counital+frobenius+algebras" in call
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

    def test_semantic_scholar_requests_are_spaced(self) -> None:
        clock = iter([100.0, 100.2, 101.3, 101.4])
        with (
            patch.dict(
                "tools.reference_citations._last_request",
                {},
                clear=True,
            ),
            patch("tools.reference_citations.time.monotonic", lambda: next(clock)),
            patch("tools.reference_citations.time.sleep") as sleep,
        ):
            wait_for_turn("api.semanticscholar.org")
            wait_for_turn("api.semanticscholar.org")
            wait_for_turn("api.openalex.org")
        self.assertEqual(len(sleep.call_args_list), 1)
        self.assertAlmostEqual(sleep.call_args.args[0], 0.9)

    def test_retry_delay_backs_off_and_honours_provider_hints(self) -> None:
        self.assertEqual([retry_delay(n) for n in range(5)], [2, 4, 8, 16, 32])
        self.assertEqual(retry_delay(0, "7"), 7)
        self.assertEqual(retry_delay(0, "Wed, 21 Oct 2026 07:28:00 GMT"), 2)
        self.assertEqual(
            retry_delay(
                0, None, "Anonymous search is rate-limited. Please retry in 38s"
            ),
            38,
        )
        self.assertEqual(retry_delay(9), 60)

    def test_request_json_waits_through_rate_limits(self) -> None:
        def rate_limited() -> HTTPError:
            return HTTPError(
                "https://api.semanticscholar.org/x",
                429,
                "Too Many Requests",
                Message(),
                io.BytesIO(b'{"message": "Too Many Requests"}'),
            )

        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"ok": 1}'
        with (
            patch(
                "tools.reference_citations.urlopen",
                side_effect=[rate_limited(), rate_limited(), response],
            ),
            patch("tools.reference_citations.wait_for_turn"),
            patch("tools.reference_citations.time.sleep") as sleep,
            patch("sys.stderr", new_callable=io.StringIO),
        ):
            payload = request_json("https://api.semanticscholar.org/x", {}, 1)
        self.assertEqual(payload, {"ok": 1})
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [2, 4])

    def test_title_match_ignores_tex_greek_markup_and_punctuation(self) -> None:
        cases = {
            "Zeros of the zeta-function on the critical line": (
                "Zeros of the $$\\zeta $$-function on the critical line"
            ),
            "zeta-functions, L-functions and modular forms": (
                "$\\boldsymbol{\\zeta}$ -Functions, $\\boldsymbol{L}$-Functions, "
                "and Modular Forms"
            ),
            "n-dimensional subvarieties of P^n(Λ)": (
                "$n$-dimensional subvarieties of $P^n(\\Lambda)$"
            ),
            "Bounds for zeta-functions of curves over finite fields": (
                "Bounds for 𝜁-functions of curves over finite fields"
            ),
            "When is a polynomial irreducible": (
                "When is a polynomial irreducible?"
            ),
            "Primes for <i>π</i>": "Primes for π",
        }
        for query, provider_title in cases.items():
            with self.subTest(query=query):
                candidates = [
                    {"title": "zeta-function theory"},
                    {"title": provider_title},
                ]
                self.assertIs(exact_title(candidates, query), candidates[1])
        with self.assertRaises(CitationLookupError):
            exact_title([{"title": "-function theory"}], "zeta-function theory")

    def test_search_text_drops_provider_syntax(self) -> None:
        self.assertEqual(
            search_text("When are Sophie Germain primes non-isolated?"),
            "when are sophie germain primes non isolated",
        )
        self.assertEqual(search_text("Primes, *gaps* | $\\zeta$"), "primes gaps")
        self.assertEqual(
            search_text("n-dimensional subvarieties of P^n(Λ)"),
            "n dimensional subvarieties of p n",
        )

    def test_openalex_falls_back_to_arxiv_doi(self) -> None:
        target = oa_paper("W4225308505", "On non-counital Frobenius algebras")
        citing = oa_paper("W1", "A citing paper", year=2026)
        seen: list[str] = []

        def requester(
            url: str, _headers: dict[str, str], _timeout: int
        ) -> dict[str, object]:
            parsed = urlparse(url)
            if parsed.netloc == "api.semanticscholar.org":
                raise CitationLookupError("HTTP 429 from provider")
            seen.append(parsed.path)
            if parsed.path == "/works/https://doi.org/10.48550/arxiv.2204.14182":
                return target
            if parse_qs(parsed.query).get("filter") == ["cites:W4225308505"]:
                return {"meta": {"count": 1}, "results": [citing]}
            raise AssertionError(f"unexpected URL: {url}")

        with tempfile.TemporaryDirectory() as temporary_raw:
            result = lookup_citations(
                "arxiv:2204.14182v3",
                root=Path(temporary_raw),
                requester=requester,
            )
        self.assertEqual(result["provider_reports"]["openalex"]["status"], "ok")
        self.assertEqual(result["citation_count"], 1)
        self.assertFalse(result["complete"])
        self.assertIn("/works/https://doi.org/10.48550/arxiv.2204.14182", seen)


if __name__ == "__main__":
    unittest.main()
