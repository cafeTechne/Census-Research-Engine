# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 171 tests: CorpusMiner auto_sync_vectors & sync-passages incremental indexing."""
from pathlib import Path

from layer_b_openscholar.corpus_miner import DOMAIN_TOPICS, CorpusMiner
from layer_b_openscholar.epmc_client import EuropePMCClient
from layer_b_openscholar.s2_client import OpenAlexClient
from layer_b_openscholar.vector_store import LocalVectorStore


def test_r171_miner_auto_syncs_vectors(tmp_path: Path):
    db = tmp_path / "index.sqlite"
    state = tmp_path / "miner_state.json"

    def fake_oa(url, params, headers):
        return {
            "results": [
                {
                    "id": "https://openalex.org/W555",
                    "title": "County BYM2 mortality spatial smoothing",
                    "publication_year": 2025,
                    "doi": "https://doi.org/10.1000/auto1",
                    "cited_by_count": 5,
                    "abstract_inverted_index": {"BYM2": [0], "mortality": [1]},
                }
            ]
        }

    def fake_epmc(url, params, headers):
        return {"resultList": {"result": []}}

    miner = CorpusMiner(
        db_path=db,
        state_path=state,
        cache_dir=tmp_path / "cache",
        topics=DOMAIN_TOPICS[:1],
        limit_per_query=5,
        delay_seconds=0.0,
        openalex_client=OpenAlexClient(http_get=fake_oa),
        epmc_client=EuropePMCClient(http_get=fake_epmc),
        sleep_fn=lambda _: None,
        auto_sync_vectors=True,
    )
    rep = miner.run_once()
    assert rep["ok"] is True
    assert rep["vectors_synced"] >= 1
    vstore = LocalVectorStore(db_path=db.with_name("vectors.sqlite"))
    assert vstore.stats()["vector_count"] >= 1
