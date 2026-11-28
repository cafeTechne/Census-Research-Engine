# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 194 tests: Layer B cross-corpus claim grounder and 22 MCP tools."""
from __future__ import annotations

from pathlib import Path

from layer_b_openscholar.claim_grounder import ground_claims, write_grounding_markdown
from layer_b_openscholar.local_index import LocalLiteratureIndex
from layer_b_openscholar.mcp_server import ground_claims as mcp_ground_claims
from layer_b_openscholar.mcp_server import list_tool_names
from layer_b_openscholar.pdf_indexer import LocalPassageIndex
from layer_b_openscholar.vector_store import sync_from_literature_index


def test_claim_grounder_and_22_mcp_tools(tmp_path: Path):
    lit_db = tmp_path / "index.sqlite"
    pas_db = tmp_path / "passages.sqlite"
    vec_db = tmp_path / "vectors.sqlite"
    LocalLiteratureIndex(lit_db).ingest_papers([
        {"paperId": "W1", "title": "BYM2 Spatial Disease Mapping County Mortality", "abstract": "Bayesian smoothing stabilizes SMRs.", "year": 2024, "doi": "10.1000/bym2"},
        {"paperId": "W2", "title": "Spatial Correlation Robust Inference SCPC", "abstract": "SCPC widens confidence intervals under spatial dependence.", "year": 2023, "doi": "10.1000/scpc"},
    ])
    doc = tmp_path / "note.md"
    doc.write_text("Regional price parities narrow nominal inter-state income spreads.", encoding="utf-8")
    LocalPassageIndex(pas_db).index_file(doc)
    sync_from_literature_index(db_path=lit_db, vector_db_path=vec_db)

    rep = ground_claims(
        [
            "BYM2 spatial smoothing stabilizes noisy county mortality SMRs",
            "SCPC widens confidence intervals under spatial autocorrelation",
        ],
        db_path=lit_db,
        passages_db_path=pas_db,
        vector_db_path=vec_db,
    )
    assert rep["ok"] is True
    assert rep["status"] == "exploratory_hypothesis_seed"
    assert rep["claim_count"] == 2
    assert rep["grounded_count"] == 2
    assert rep["grounding_coverage"] == 1.0
    assert rep["unique_doi_count"] >= 2

    md_path = write_grounding_markdown(rep, tmp_path / "grounding.md")
    assert Path(md_path).exists() and "C1:" in Path(md_path).read_text(encoding="utf-8")

    mcp_rep = mcp_ground_claims(["BYM2 county mortality"], db_path=str(lit_db), passages_db_path=str(pas_db))
    assert mcp_rep["ok"] is True and mcp_rep["grounded_count"] == 1
    assert len(list_tool_names()) == 22
    assert "ground_claims" in list_tool_names()
