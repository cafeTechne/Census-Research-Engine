# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 196 tests: SubprocessNeuralEmbedder bridge for querying neural vectors without torch in caller."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from layer_b_openscholar.local_index import LocalLiteratureIndex
from layer_b_openscholar.neural_bridge import SubprocessNeuralEmbedder
from layer_b_openscholar.rag import query_hybrid_rag
from layer_b_openscholar.vector_store import LocalVectorStore


def test_subprocess_neural_embedder_with_rag(tmp_path: Path):
    def fake_runner(cmd, env):
        texts = json.loads(cmd[-1])
        vecs = []
        for t in texts:
            v = np.zeros(8, dtype=np.float32)
            v[0] = 1.0 if "bym2" in t.lower() else 0.1
            v[1] = 1.0 if "scpc" in t.lower() else 0.1
            v = v / np.linalg.norm(v)
            vecs.append(v.tolist())
        return json.dumps(vecs)

    emb = SubprocessNeuralEmbedder(
        model_name="BAAI/bge-small-en-v1.5",
        dim=8,
        venv_python=tmp_path / "fake_python",
        hf_home=tmp_path / "hf",
        runner=fake_runner,
    )
    lit_db = tmp_path / "index.sqlite"
    vec_db = tmp_path / "vectors.sqlite"
    pas_db = tmp_path / "passages.sqlite"
    LocalLiteratureIndex(lit_db).ingest_papers([
        {"paperId": "W1", "title": "BYM2 Spatial County Mortality", "abstract": "Disease mapping", "year": 2025},
        {"paperId": "W2", "title": "SCPC Spatial Correlation Inference", "abstract": "Econometrics", "year": 2024},
    ])
    store = LocalVectorStore(db_path=vec_db, embedder=emb)
    assert store.upsert_papers([
        {"paperId": "W1", "title": "BYM2 Spatial County Mortality", "abstract": "Disease mapping", "year": 2025},
        {"paperId": "W2", "title": "SCPC Spatial Correlation Inference", "abstract": "Econometrics", "year": 2024},
    ]) == 2

    rag = query_hybrid_rag("BYM2 county mortality", db_path=lit_db, passages_db_path=pas_db, vector_db_path=vec_db, embedder=emb)
    assert rag["ok"] is True
    assert rag["vector_model"] == "BAAI/bge-small-en-v1.5"
    assert rag["citations"][0]["paperId"] == "W1"
