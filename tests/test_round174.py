# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 174 tests: Layer B Multi-Domain Evidence Velocity & Trend Analyzer + 17-tool MCP."""
from pathlib import Path

from layer_b_openscholar.local_index import LocalLiteratureIndex
from layer_b_openscholar.mcp_server import domain_trends, list_tool_names
from layer_b_openscholar.trends import analyze_domain_trends


def test_r174_domain_trends_and_17_mcp_tools(tmp_path: Path):
    db = tmp_path / "index.sqlite"
    LocalLiteratureIndex(db).ingest_papers([
        {"paperId": "W1", "title": "A", "abstract": "x", "year": 2025, "citationCount": 10, "openAccessPdf": "https://a.pdf"},
        {"paperId": "W2", "title": "B", "abstract": "y", "year": 2024, "citationCount": 20, "openAccessPdf": ""},
        {"paperId": "W3", "title": "C", "abstract": "z", "year": 2018, "citationCount": 50, "openAccessPdf": "https://c.pdf"},
    ], source="miner:bym2_disease_mapping:p1")

    rep = analyze_domain_trends(db_path=db, top_n=5)
    assert rep["ok"] is True
    assert rep["total_papers"] == 3
    assert rep["top_fastest_growing"][0]["domain"] == "bym2_disease_mapping"
    assert rep["top_fastest_growing"][0]["y2024_plus"] == 2
    assert rep["top_fastest_growing"][0]["median_citations"] == 20.0
    assert len(rep["trends_sha256"]) == 64

    assert len(list_tool_names()) >= 17
    assert domain_trends(db_path=str(db), top_n=5)["ok"] is True
