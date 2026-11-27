# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 128 tests: standalone Layer B FastMCP handlers (strictly isolated from census/)."""
from layer_b_openscholar.mcp_server import index_literature, index_stats, local_search_literature


def test_layer_b_mcp_handlers_offline_round_trip(tmp_path):
    db = str(tmp_path / "mcp_idx.sqlite")
    papers = [
        {
            "paperId": "W1",
            "doi": "10.1000/test.1",
            "title": "Fay-Herriot small area poverty designation in US counties",
            "abstract": "Positive predictive value of posterior threshold designation rules.",
            "year": 2024,
            "authors": ["A. Author"],
            "venue": "Survey Methodology",
            "citationCount": 15,
        }
    ]
    res_in = index_literature(papers, db_path=db, source="unit_test")
    assert res_in["ok"] is True and res_in["added"] == 1
    assert res_in["status"] == "exploratory_hypothesis_seed"

    st = index_stats(db_path=db)
    assert st["ok"] is True and st["paper_count"] == 1

    res_q = local_search_literature("Fay Herriot county poverty designation", db_path=db, backend="bm25",
                                    out_dir=str(tmp_path / "dossier"))
    assert res_q["ok"] is True and res_q["paper_count"] == 1
    assert res_q["status"] == "exploratory_hypothesis_seed"
    assert res_q["papers"][0]["doi"] == "10.1000/test.1"
