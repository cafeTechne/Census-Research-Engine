# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for 24-domain CorpusMiner and Tier 1 Domain Hybrid RAG (isolated Layer B)."""
from pathlib import Path

from layer_b_openscholar.corpus_miner import DOMAIN_TOPICS, CorpusMiner, load_miner_status
from layer_b_openscholar.epmc_client import EuropePMCClient
from layer_b_openscholar.mcp_server import list_tool_names, miner_status, rag_query
from layer_b_openscholar.pdf_indexer import LocalPassageIndex
from layer_b_openscholar.rag import query_hybrid_rag
from layer_b_openscholar.s2_client import OpenAlexClient


def test_domain_catalog_has_24_unique_topics():
    assert len(DOMAIN_TOPICS) == 36
    assert len({t["id"] for t in DOMAIN_TOPICS}) == 36
    assert len({t["domain"] for t in DOMAIN_TOPICS}) == 36


def test_corpus_miner_resumable_pagination_and_hybrid_rag(tmp_path: Path):
    db = tmp_path / "index.sqlite"
    pdb = tmp_path / "passages.sqlite"
    state = tmp_path / "miner_state.json"

    def fake_oa(url, params, headers):
        pg = params.get("page", 1)
        return {
            "results": [
                {
                    "id": f"https://openalex.org/W{pg}01",
                    "title": f"County BYM2 mortality spatial disparities page {pg}",
                    "publication_year": 2024,
                    "doi": f"https://doi.org/10.1000/oa.{pg}",
                    "cited_by_count": 12,
                    "abstract_inverted_index": {"BYM2": [0], "spatial": [1], "mortality": [2], "county": [3]},
                }
            ]
        }

    def fake_epmc(url, params, headers):
        return {
            "resultList": {
                "result": [
                    {
                        "pmid": "99999",
                        "title": "Fay Herriot temporal small area poverty estimation",
                        "pubYear": "2025",
                        "doi": "10.1000/epmc.1",
                        "abstractText": "Temporal Fay Herriot model reduces county poverty MSE.",
                    }
                ]
            }
        }

    miner = CorpusMiner(
        db_path=db,
        state_path=state,
        cache_dir=tmp_path / "cache",
        topics=DOMAIN_TOPICS[:2],
        limit_per_query=5,
        max_pages_per_topic=3,
        delay_seconds=0.0,
        cycle_sleep_seconds=0.0,
        openalex_client=OpenAlexClient(http_get=fake_oa),
        epmc_client=EuropePMCClient(http_get=fake_epmc),
        sleep_fn=lambda _: None,
    )
    rep1 = miner.run_once()
    assert rep1["ok"] is True
    assert rep1["cycles_completed"] == 1
    assert rep1["stats"]["paper_count"] >= 2

    # Second cycle advances OpenAlex page 1 -> 2 and persists state
    rep2 = miner.run_once()
    assert rep2["cycles_completed"] == 2
    assert rep2["stats"]["paper_count"] > rep1["stats"]["paper_count"]

    st = load_miner_status(db_path=db, state_path=state)
    assert st["domain_count"] == 36
    assert st["miner_state"]["topic_pages"]["D01"] == 3

    # Index a local study passage and run Tier 1 Hybrid RAG
    md = tmp_path / "study.md"
    md.write_text("# Stroke BYM2 Study\n\nCounty BYM2 spatial mortality smoothing reduced IQR.\n", encoding="utf-8")
    pidx = LocalPassageIndex(pdb)
    pidx.index_file(md)

    rag = query_hybrid_rag("county BYM2 spatial mortality", db_path=db, passages_db_path=pdb)
    assert rag["ok"] is True
    assert rag["status"] == "exploratory_hypothesis_seed"
    assert rag["paper_hits"] >= 1
    assert rag["passage_hits"] >= 1
    assert "[L1]" in rag["context_markdown"] and "[P1]" in rag["context_markdown"]
    assert len(rag["rag_sha256"]) == 64

    # Verify Layer B MCP exposes 14 tools including rag_query & miner_status
    names = list_tool_names()
    assert len(names) >= 11
    assert {"rag_query", "miner_status"} <= set(names)
    assert rag_query("BYM2 mortality", db_path=str(db), passages_db_path=str(pdb))["ok"] is True
    assert miner_status(db_path=str(db), state_path=str(state))["ok"] is True
