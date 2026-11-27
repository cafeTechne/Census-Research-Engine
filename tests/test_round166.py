# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 166 tests: 3-way Hybrid RAG (FTS5 + BM25 + Vector RRF) & sync_from_literature_index."""
from pathlib import Path

from layer_b_openscholar.local_index import LocalLiteratureIndex
from layer_b_openscholar.rag import query_hybrid_rag
from layer_b_openscholar.vector_store import sync_from_literature_index


def test_r166_three_way_hybrid_rag_with_vector_sync(tmp_path: Path):
    db = tmp_path / "index.sqlite"
    vdb = tmp_path / "vectors.sqlite"
    pdb = tmp_path / "passages.sqlite"
    LocalLiteratureIndex(db).ingest_papers([
        {"paperId": "W1", "title": "County BYM2 spatial mortality smoothing", "abstract": "Bayesian disease mapping", "year": 2024, "doi": "10.1000/v1"},
        {"paperId": "W2", "title": "Fay Herriot temporal poverty SAE", "abstract": "Small area estimation", "year": 2025, "doi": "10.1000/v2"},
    ], source="test")

    sync = sync_from_literature_index(db_path=db, vector_db_path=vdb)
    assert sync["ok"] is True and sync["synced"] == 2

    rag = query_hybrid_rag("BYM2 spatial mortality", db_path=db, passages_db_path=pdb, vector_db_path=vdb)
    assert rag["ok"] is True
    assert "+vector" in rag["backend"]
    assert rag["paper_hits"] >= 1
