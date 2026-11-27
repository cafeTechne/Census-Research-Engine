# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 138 tests: Evidence & Hypothesis-Gap Matrix builder and MCP handler."""
from layer_b_openscholar.gap_matrix import build_gap_matrix
from layer_b_openscholar.mcp_server import build_gap_matrix as mcp_gap_matrix
from layer_b_openscholar.mcp_server import index_literature


def test_gap_matrix_extracts_coverage_and_proposals(tmp_path):
    papers = [
        {
            "paperId": "W1",
            "doi": "10.1000/a",
            "year": 2023,
            "title": "County-level BYM2 disease mapping of cancer mortality",
            "abstract": "We use BYM2 spatial smoothing across US counties.",
        },
        {
            "paperId": "W2",
            "doi": "10.1000/b",
            "year": 2018,
            "title": "Regression discontinuity at age 65 in ACS PUMS microdata",
            "abstract": "Sharp RDD at the Medicare eligibility cutoff.",
        },
    ]
    mat = build_gap_matrix(papers, query="cancer mortality")
    assert mat["status"] == "exploratory_hypothesis_seed"
    assert mat["recency"] == {"pre_2020": 1, "2020_plus": 1, "unknown": 0}
    assert mat["covered_cells"]["county::spatial_disease_map"] == 1
    assert mat["covered_cells"]["pums_microdata::rdd"] == 1
    assert len(mat["gap_proposals"]) > 0
    assert len(mat["matrix_sha256"]) == 64

    db = str(tmp_path / "gap.sqlite")
    index_literature(papers, db_path=db)
    res = mcp_gap_matrix("county cancer BYM2", db_path=db)
    assert res["ok"] is True and res["paper_count"] >= 1
