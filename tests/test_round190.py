# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 190 tests: Layer B neural_bridge diagnostics, EPMC skip_existing/retry, and 21 MCP tools."""
from __future__ import annotations

from pathlib import Path

from layer_b_openscholar.fulltext_harvester import harvest_epmc_fulltext
from layer_b_openscholar.local_index import LocalLiteratureIndex
from layer_b_openscholar.mcp_server import list_tool_names, neural_status
from layer_b_openscholar.neural_bridge import neural_runtime_status
from layer_b_openscholar.vector_store import LocalVectorStore

_XML = "<article><body><sec><title>Results</title><p>Spatial BYM2 smoothing stabilizes county mortality rates across rural counties.</p></sec></body></article>"


def test_neural_runtime_status_and_21_mcp_tools(tmp_path: Path):
    vdb = tmp_path / "vectors.sqlite"
    LocalVectorStore(db_path=vdb).upsert_papers([{"paperId": "W1", "title": "Spatial BYM2", "abstract": "Test", "year": 2025}])
    rep = neural_runtime_status(vector_db_path=vdb)
    assert rep["ok"] is True
    assert rep["status"] == "exploratory_hypothesis_seed"
    assert rep["vector_store"]["models"]["hash_projection_d256"] == 1
    assert neural_status(vector_db_path=str(vdb))["ok"] is True
    assert len(list_tool_names()) >= 21
    assert "neural_status" in list_tool_names()


def test_harvest_skip_existing_advances_to_new_pmcids(tmp_path: Path):
    lit_db = tmp_path / "index.sqlite"
    pas_db = tmp_path / "passages.sqlite"
    LocalLiteratureIndex(lit_db).ingest_papers([
        {"paperId": "PMC1001", "title": "First OA Paper", "abstract": "A", "year": 2025},
        {"paperId": "PMC1002", "title": "Second OA Paper", "abstract": "B", "year": 2025},
    ])
    seen = []

    def fake_get(url, headers):
        seen.append(url)
        return _XML

    r1 = harvest_epmc_fulltext(db_path=lit_db, passages_db_path=pas_db, cache_dir=tmp_path / "c", limit=1, delay_seconds=0.0, http_get_text=fake_get)
    r2 = harvest_epmc_fulltext(db_path=lit_db, passages_db_path=pas_db, cache_dir=tmp_path / "c", limit=1, delay_seconds=0.0, http_get_text=fake_get)
    assert r1["harvested_articles"] == 1
    assert r2["harvested_articles"] == 1
    assert len(seen) == 2 and seen[0] != seen[1]
