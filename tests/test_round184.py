# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 184 tests: Layer B normalized-title deduplication merger & 19-tool MCP."""
from pathlib import Path

from layer_b_openscholar.local_index import LocalLiteratureIndex
from layer_b_openscholar.maintenance import dedupe_title_duplicates
from layer_b_openscholar.mcp_server import dedupe_corpus, list_tool_names


def test_r184_dedupe_title_duplicates_and_19_mcp_tools(tmp_path: Path):
    db = tmp_path / "index.sqlite"
    vdb = tmp_path / "vectors.sqlite"
    LocalLiteratureIndex(db).ingest_papers([
        {"paperId": "W1", "title": "County Spatial Mortality Analysis", "abstract": "Full abstract text here", "year": 2025, "doi": "10.1000/rich", "citationCount": 15},
        {"paperId": "PMID:123", "title": "county  spatial mortality analysis", "abstract": "", "year": 2025, "doi": "", "citationCount": 0},
    ], source="test")

    rep = dedupe_title_duplicates(db_path=db, vector_db_path=vdb)
    assert rep["ok"] is True
    assert rep["duplicate_rows_removed"] == 1
    assert rep["duplicate_title_groups"] == 0
    assert rep["paper_count"] == 1
    assert rep["fts5_integrity_ok"] is True

    assert len(list_tool_names()) >= 19
    assert dedupe_corpus(db_path=str(db), vector_db_path=str(vdb))["ok"] is True
