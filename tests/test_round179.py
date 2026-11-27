# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 179 tests: Layer B corpus integrity auditor, orphan-vector pruner & 18-tool MCP."""
from pathlib import Path

from layer_b_openscholar.local_index import LocalLiteratureIndex
from layer_b_openscholar.maintenance import audit_and_compact_corpus
from layer_b_openscholar.mcp_server import compact_corpus, list_tool_names
from layer_b_openscholar.vector_store import LocalVectorStore


def test_r179_corpus_maintenance_prunes_orphans_and_18_mcp_tools(tmp_path: Path):
    db = tmp_path / "index.sqlite"
    vdb = tmp_path / "vectors.sqlite"
    LocalLiteratureIndex(db).ingest_papers([
        {"paperId": "W1", "title": "Valid paper", "abstract": "Text", "year": 2025, "doi": "10.1000/ok"},
    ], source="test")
    vstore = LocalVectorStore(db_path=vdb)
    vstore.upsert_papers([
        {"paperId": "W1", "title": "Valid paper", "abstract": "Text", "year": 2025, "doi": "10.1000/ok"},
        {"paperId": "ORPHAN_999", "title": "Deleted paper", "abstract": "Gone", "year": 2020, "doi": "10.1000/gone"},
    ])

    rep = audit_and_compact_corpus(db_path=db, vector_db_path=vdb, vacuum=True)
    assert rep["ok"] is True
    assert rep["fts5_integrity_ok"] is True
    assert rep["orphan_vectors_removed"] == 1
    assert rep["vector_count"] == 1

    assert len(list_tool_names()) >= 18
    assert compact_corpus(db_path=str(db), vector_db_path=str(vdb), vacuum=False)["ok"] is True
