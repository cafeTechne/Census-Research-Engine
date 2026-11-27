# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 164 tests: pluggable SQLite+NumPy LocalVectorStore (N127 prep) & domain_hybrid_rag recipe."""
from pathlib import Path

from census import recipes
from layer_b_openscholar.mcp_server import list_tool_names
from layer_b_openscholar.vector_store import HashProjectionEmbedder, LocalVectorStore

ROOT = Path(__file__).resolve().parents[1]


def test_r164_vector_store_and_recipe(tmp_path: Path):
    store = LocalVectorStore(db_path=tmp_path / "vectors.sqlite", embedder=HashProjectionEmbedder(dim=128))
    n = store.upsert_papers([
        {"paperId": "W1", "title": "County BYM2 Bayesian spatial disease mapping", "abstract": "Mortality smoothing", "year": 2024, "doi": "10.1000/1"},
        {"paperId": "W2", "title": "Medicare age 65 regression discontinuity PUMS", "abstract": "Insurance jump", "year": 2023, "doi": "10.1000/2"},
    ])
    assert n == 2
    assert store.stats()["vector_count"] == 2
    hits = store.search("BYM2 Bayesian spatial mortality", top_k=2)
    assert len(hits) == 2
    assert hits[0]["paperId"] == "W1"
    assert hits[0]["cosine_score"] > hits[1]["cosine_score"]

    assert "domain_hybrid_rag" in recipes.RECIPES
    assert len(recipes.RECIPES) >= 33
    assert (ROOT / "docs/recipes/domain_hybrid_rag.md").exists()
    assert len(list_tool_names()) >= 14
