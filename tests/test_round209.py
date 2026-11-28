# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 209 tests: Layer B domain synonym query expansion and passage vector sync."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from layer_b_openscholar.local_index import LocalLiteratureIndex
from layer_b_openscholar.pdf_indexer import LocalPassageIndex
from layer_b_openscholar.query_expansion import expand_domain_query
from layer_b_openscholar.rag import query_hybrid_rag
from layer_b_openscholar.vector_store import sync_passages_to_vectors

ROOT = Path(__file__).resolve().parents[1]


def test_domain_synonym_expansion_improves_acronym_recall(tmp_path: Path):
    expanded, added = expand_domain_query("BYM2 county mortality")
    assert "Besag York Mollie" in expanded and len(added) >= 2

    lit_db = tmp_path / "index.sqlite"
    pas_db = tmp_path / "passages.sqlite"
    vec_db = tmp_path / "vectors.sqlite"
    # Paper uses full name "Besag York Mollie" without acronym "BYM2"
    LocalLiteratureIndex(lit_db).ingest_papers([
        {"paperId": "W1", "title": "Besag York Mollie disease mapping for rural counties", "abstract": "Spatial smoothing", "year": 2024}
    ])
    rag = query_hybrid_rag("BYM2", db_path=lit_db, passages_db_path=pas_db, vector_db_path=vec_db, expand_synonyms=True)
    assert rag["ok"] is True
    assert rag["paper_hits"] == 1
    assert "Besag York Mollie" in rag["expanded_terms"]

    doc = tmp_path / "study.md"
    doc.write_text("Regional price parities adjust nominal county income across states.", encoding="utf-8")
    LocalPassageIndex(pas_db).index_file(doc)
    rep = sync_passages_to_vectors(passages_db_path=pas_db, vector_db_path=vec_db)
    assert rep["ok"] is True and rep["synced"] >= 1


def test_r209_release_hygiene_passes_at_v0205():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/release_hygiene_check.py")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rep = json.loads(proc.stdout)
    assert rep["ok"] is True and rep["version"] >= "0.205.0"
