# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 186 tests: OpenAlex polite pool, EPMC JATS XML harvester, multi-model vector store, and neural RAG benchmark."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np

from layer_b_openscholar.fulltext_harvester import (
    harvest_epmc_fulltext,
    ingest_jats_xml_to_passages,
    parse_jats_sections,
)
from layer_b_openscholar.local_index import LocalLiteratureIndex
from layer_b_openscholar.mcp_server import list_tool_names
from layer_b_openscholar.neural_benchmark import run_neural_benchmark
from layer_b_openscholar.pdf_indexer import LocalPassageIndex
from layer_b_openscholar.rag import query_hybrid_rag
from layer_b_openscholar.s2_client import OpenAlexClient
from layer_b_openscholar.vector_store import HashProjectionEmbedder, LocalVectorStore, sync_from_literature_index

_SAMPLE_JATS = """<?xml version="1.0" encoding="UTF-8"?>
<article>
  <front><article-meta><abstract><p>County-level mortality exhibits strong spatial autocorrelation across rural and urban US counties.</p></abstract></article-meta></front>
  <body>
    <sec><title>Introduction</title><p>Small-area estimation using BYM2 spatial smoothing stabilizes noisy county mortality rates from CDC WONDER and ACS poverty estimates.</p></sec>
    <sec><title>Methods</title><p>We fit hierarchical Besag-York-Mollie models with regional price parity adjustments and evaluate rank uncertainty using KWW confidence sets.</p></sec>
    <sec><title>Results</title><p>Accounting for spatial correlation widens standard errors by 1.46x to 1.52x relative to HC3 robust estimators.</p></sec>
  </body>
</article>
"""


class _DummyNeuralEmbedder:
    def __init__(self) -> None:
        self.model_name = "dummy/neural-384"
        self.dim = 16

    def embed(self, texts):
        out = []
        for t in texts:
            v = np.zeros(self.dim, dtype=np.float32)
            for i, ch in enumerate(t.encode("utf-8")):
                v[i % self.dim] += float((ch % 7) - 3)
            n = float(np.linalg.norm(v))
            out.append(v / n if n > 0 else v)
        return np.vstack(out).astype(np.float32)


def test_openalex_polite_pool_mailto_and_cache_key(tmp_path: Path):
    seen = {}

    def fake_get(url, params, headers):
        seen["params"] = dict(params)
        seen["headers"] = dict(headers)
        return {"results": [{"id": "https://openalex.org/W1", "title": "Spatial Mortality", "publication_year": 2024}]}

    client = OpenAlexClient(cache_dir=tmp_path, http_get=fake_get, mailto="research@example.org", api_key="secret-k")
    res = client.search_papers("spatial mortality", limit=5)
    assert len(res) == 1
    assert seen["params"]["mailto"] == "research@example.org"
    assert seen["params"]["api_key"] == "secret-k"
    assert "mailto:research@example.org" in seen["headers"]["User-Agent"]
    # Cache key excludes secrets so a second client without api_key hits the same cache
    client2 = OpenAlexClient(cache_dir=tmp_path, http_get=lambda u, p, h: (_ for _ in ()).throw(AssertionError("should hit cache")))
    res2 = client2.search_papers("spatial mortality", limit=5)
    assert len(res2) == 1


def test_jats_xml_harvester_and_passages_ingest(tmp_path: Path):
    secs = parse_jats_sections(_SAMPLE_JATS)
    titles = [s["section_title"] for s in secs]
    assert "Abstract" in titles and "Methods" in titles and "Results" in titles

    lit_db = tmp_path / "index.sqlite"
    pas_db = tmp_path / "passages.sqlite"
    LocalLiteratureIndex(lit_db).ingest_papers([
        {"paperId": "PMC1234567", "title": "Spatial BYM2 County Mortality", "abstract": "Test", "year": 2025, "doi": "10.1000/pmc1"}
    ])
    rep = harvest_epmc_fulltext(
        db_path=lit_db,
        passages_db_path=pas_db,
        cache_dir=tmp_path / "xml_cache",
        limit=5,
        delay_seconds=0.0,
        http_get_text=lambda url, hdrs: _SAMPLE_JATS,
    )
    assert rep["ok"] is True
    assert rep["harvested_articles"] == 1
    assert rep["passages_added"] >= 4
    hits = LocalPassageIndex(pas_db).search_passages("BYM2 spatial autocorrelation", limit=5)
    assert len(hits) >= 1
    assert any("PMC1234567" in h["text"] for h in hits)


def test_vector_store_composite_pk_migration_and_coexistence(tmp_path: Path):
    vdb = tmp_path / "vectors.sqlite"
    # Create legacy single-column PK schema
    with sqlite3.connect(vdb) as conn:
        conn.execute(
            "CREATE TABLE embeddings (item_id TEXT PRIMARY KEY, title TEXT, doi TEXT, year INTEGER, "
            "model_name TEXT, dim INTEGER, vec BLOB)"
        )
        vec = HashProjectionEmbedder(dim=256).embed(["Legacy spatial paper"])[0]
        conn.execute(
            "INSERT INTO embeddings VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("W1", "Legacy spatial paper", "10.1/legacy", 2023, "hash_projection_d256", 256, vec.tobytes()),
        )

    # Opening LocalVectorStore migrates seamlessly and preserves legacy rows
    hstore = LocalVectorStore(db_path=vdb)
    assert hstore.stats()["vector_count"] == 1

    # Upsert second model for the SAME item_id without overwriting hash_projection_d256
    nstore = LocalVectorStore(db_path=vdb, embedder=_DummyNeuralEmbedder())
    added = nstore.upsert_papers([{"paperId": "W1", "title": "Legacy spatial paper", "abstract": "BYM2 spatial", "year": 2023}])
    assert added == 1
    st = nstore.stats()
    assert st["models"]["hash_projection_d256"] == 1
    assert st["models"]["dummy/neural-384"] == 1
    assert st["total_rows"] == 2
    # Incremental upsert skips already-embedded item
    assert nstore.upsert_papers([{"paperId": "W1", "title": "Legacy spatial paper", "abstract": "BYM2"}], incremental=True) == 0


def test_rag_custom_embedder_and_benchmark_and_mcp_20_tools(tmp_path: Path):
    lit_db = tmp_path / "index.sqlite"
    pas_db = tmp_path / "passages.sqlite"
    vec_db = tmp_path / "vectors.sqlite"
    LocalLiteratureIndex(lit_db).ingest_papers([
        {"paperId": "W10", "title": "County Mortality Spatial Autocorrelation BYM2", "abstract": "Small area estimation", "year": 2024},
        {"paperId": "W11", "title": "PUMA Ecologic Fallacy Microdata ACS", "abstract": "Aggregation bias", "year": 2023},
        {"paperId": "W12", "title": "BEA Regional Price Parity Poverty", "abstract": "Cost of living adjustment", "year": 2025},
    ])
    ingest_jats_xml_to_passages("PMC999", _SAMPLE_JATS, passages_db_path=pas_db)
    sync_from_literature_index(db_path=lit_db, vector_db_path=vec_db)
    emb = _DummyNeuralEmbedder()
    sync_from_literature_index(db_path=lit_db, vector_db_path=vec_db, embedder=emb)

    rag = query_hybrid_rag(
        "county mortality BYM2 spatial",
        db_path=lit_db,
        passages_db_path=pas_db,
        vector_db_path=vec_db,
        embedder=emb,
    )
    assert rag["ok"] is True
    assert rag["vector_model"] == "dummy/neural-384"
    assert "dummy/neural-384" in rag["backend"]

    out_md = tmp_path / "bench.md"
    bench = run_neural_benchmark(
        db_path=lit_db,
        passages_db_path=pas_db,
        vector_db_path=vec_db,
        neural_model="nonexistent-offline-model-for-fallback-test",
        out_md_path=out_md,
    )
    assert bench["ok"] is True
    assert out_md.exists()
    assert len(list_tool_names()) == 20
    assert "harvest_fulltext" in list_tool_names()
