# SPDX-License-Identifier: AGPL-3.0-or-later
"""Offline unit tests for Layer B OpenScholar (Semantic Scholar + reranker + dossier handoff)."""
import json

from layer_b_openscholar.benchmark import BENCHMARK_QUERIES, evaluate_backend
from layer_b_openscholar.epmc_client import EuropePMCClient, merge_and_deduplicate
from layer_b_openscholar.handoff import build_dossier, write_dossier
from layer_b_openscholar.local_index import LocalLiteratureIndex, resolve_index_path
from layer_b_openscholar.reranker import OpenScholarReranker
from layer_b_openscholar.s2_client import OpenAlexClient, SemanticScholarClient

SAMPLE_S2_RESPONSE = {
    "data": [
        {
            "paperId": "s2_appalachia_01",
            "title": "County-level poverty and Appalachian cancer mortality disparities in Ohio and Pennsylvania",
            "abstract": "We examine spatial clustering and county poverty gradients in Appalachian cancer mortality.",
            "year": 2021,
            "authors": [{"name": "Gopal K. Singh"}, {"name": "Ahmedin Jemal"}],
            "venue": "Cancer Epidemiology",
            "citationCount": 142,
            "externalIds": {"DOI": "10.1000/appalachia.2021"},
            "url": "https://www.semanticscholar.org/paper/s2_appalachia_01",
        },
        {
            "paperId": "s2_unrelated_02",
            "title": "Exoplanet atmospheric spectroscopy with infrared interferometry",
            "abstract": "Observations of hot Jupiters using space-based infrared telescopes.",
            "year": 2022,
            "authors": [{"name": "Jane Doe"}],
            "venue": "Astrophysical Journal",
            "citationCount": 300,
            "externalIds": {"DOI": "10.1000/exoplanet.2022"},
            "url": "https://www.semanticscholar.org/paper/s2_unrelated_02",
        },
        {
            "paperId": "s2_nyc_03",
            "title": "Urban health paradox in New York City cancer mortality rates",
            "abstract": "Comparing New York City county cancer mortality against national age-standardized rates.",
            "year": 2023,
            "authors": [{"name": "A. Researcher"}],
            "venue": "American Journal of Public Health",
            "citationCount": 48,
            "externalIds": {"DOI": "10.1000/nyc.2023"},
            "url": "https://www.semanticscholar.org/paper/s2_nyc_03",
        },
    ]
}


def test_s2_client_caching_and_reranking_and_dossier(tmp_path):
    calls = []

    def fake_get(url, params, headers):
        calls.append((url, params, headers))
        return SAMPLE_S2_RESPONSE

    client = SemanticScholarClient(api_key="test-key", cache_dir=tmp_path / "cache", http_get=fake_get)
    papers = client.search_papers("Appalachia county cancer mortality poverty", limit=10)
    assert len(papers) == 3
    assert len(calls) == 1
    assert calls[0][2]["x-api-key"] == "test-key"

    # Second identical call hits disk cache without another HTTP request
    papers_cached = client.search_papers("Appalachia county cancer mortality poverty", limit=10)
    assert papers_cached == papers and len(calls) == 1

    # Reranker puts the Appalachian cancer paper #1 and exoplanet paper last
    reranker = OpenScholarReranker(backend="bm25")
    ranked = reranker.rerank("Appalachia county cancer mortality poverty", papers, top_k=3)
    assert ranked[0]["paperId"] == "s2_appalachia_01"
    assert ranked[-1]["paperId"] == "s2_unrelated_02"

    # Build and write dossier with deterministic SHA-256 and BibTeX
    dossier = build_dossier("Appalachia county cancer mortality poverty", ranked, backend="bm25",
                            created="2026-11-26T00:00:00Z")
    dossier2 = build_dossier("Appalachia county cancer mortality poverty", ranked, backend="bm25",
                             created="2026-11-26T00:00:00Z")
    assert dossier["dossier_sha256"] == dossier2["dossier_sha256"]
    assert dossier["status"] == "exploratory_hypothesis_seed"

    paths = write_dossier(dossier, tmp_path / "out")
    bib = (tmp_path / "out" / "references.bib").read_text(encoding="utf-8")
    md = (tmp_path / "out" / "hypothesis_seeds.md").read_text(encoding="utf-8")
    loaded = json.loads((tmp_path / "out" / "dossier.json").read_text(encoding="utf-8"))
    assert "10.1000/appalachia.2021" in bib and "Singh" in bib
    assert dossier["dossier_sha256"] in md and "exploratory_hypothesis_seed" in md
    assert loaded["paper_count"] == 3 and paths["references_bib"].endswith("references.bib")


def test_openalex_client_normalizes_inverted_abstract_and_caches(tmp_path):
    sample_oa = {
        "results": [
            {
                "id": "https://openalex.org/W999999",
                "title": "Appalachian county cancer mortality and poverty",
                "publication_year": 2025,
                "cited_by_count": 12,
                "doi": "https://doi.org/10.1097/xcs.0000000000001273",
                "authorships": [{"author": {"display_name": "Todd Burus"}}],
                "primary_location": {"source": {"display_name": "Journal of the American College of Surgeons"}},
                "abstract_inverted_index": {"Appalachia": [0], "cancer": [1], "disparities": [2]},
            }
        ]
    }
    calls = []
    client = OpenAlexClient(cache_dir=tmp_path / "oa_cache", http_get=lambda u, p, h: (calls.append(u), sample_oa)[1])
    out = client.search_papers("Appalachia cancer", limit=5)
    assert len(out) == 1 and out[0]["abstract"] == "Appalachia cancer disparities"
    assert out[0]["doi"] == "10.1097/xcs.0000000000001273" and out[0]["paperId"] == "W999999"
    # Second call uses cache
    assert client.search_papers("Appalachia cancer", limit=5) == out and len(calls) == 1


def test_epmc_deduplication_local_fts5_index_and_benchmark(tmp_path):
    sample_epmc = {
        "resultList": {
            "result": [
                {
                    "pmid": "38000001",
                    "pmcid": "PMC10700001",
                    "doi": "10.1000/appalachia.2021",
                    "title": "County-level poverty and Appalachian cancer mortality disparities.",
                    "abstractText": "Spatial clustering of Appalachian county cancer mortality and poverty.",
                    "pubYear": "2021",
                    "authorString": "Singh GK, Jemal A.",
                    "journalTitle": "Cancer Epidemiology",
                    "citedByCount": 142,
                    "isOpenAccess": "Y",
                },
                {
                    "pmid": "38000002",
                    "doi": "10.1000/medicare.2023",
                    "title": "Medicare age 65 regression discontinuity and uninsurance in ACS PUMS.",
                    "abstractText": "Sharp drop in uninsurance at age 65 Medicare eligibility cutoff.",
                    "pubYear": "2023",
                    "authorString": "Card D, Dobkin C.",
                    "journalTitle": "Health Economics",
                    "citedByCount": 90,
                },
            ]
        }
    }
    epmc = EuropePMCClient(cache_dir=tmp_path / "epmc_cache", http_get=lambda u, p, h: sample_epmc)
    ep_papers = epmc.search_papers("Appalachia cancer", limit=10)
    assert len(ep_papers) == 2 and ep_papers[0]["openAccessPdf"].endswith("pdf=render")

    # Deduplicate overlapping DOI against S2 list
    s2_papers = [SemanticScholarClient.normalize_paper(p) for p in SAMPLE_S2_RESPONSE["data"]]
    merged = merge_and_deduplicate(s2_papers, ep_papers)
    assert len(merged) == 4  # 3 + 2 - 1 duplicate DOI

    # Local SQLite FTS5 index round-trip
    db_file = tmp_path / "test_ssd_index.sqlite"
    assert resolve_index_path(db_file) == db_file
    idx = LocalLiteratureIndex(db_file)
    assert idx.ingest_papers(merged, source="multi") == 4
    assert idx.stats()["paper_count"] == 4
    hits = idx.search_fts("Medicare 65 uninsurance PUMS", limit=5)
    assert hits and hits[0]["doi"] == "10.1000/medicare.2023"

    # Benchmark harness
    by_q = {q["id"]: merged for q in BENCHMARK_QUERIES}
    bm = evaluate_backend(by_q, backend="bm25", top_k=3)
    assert bm["backend"] == "bm25" and len(bm["queries"]) == 5 and bm["mean_mrr"] > 0.0
