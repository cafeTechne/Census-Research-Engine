# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 169 tests: Layer B Multi-Domain Research Agenda Synthesizer & 16-tool MCP."""
from pathlib import Path

from layer_b_openscholar.agenda import build_research_agenda, write_research_agenda
from layer_b_openscholar.local_index import LocalLiteratureIndex
from layer_b_openscholar.mcp_server import list_tool_names


def test_r169_research_agenda_and_16_mcp_tools(tmp_path: Path):
    db = tmp_path / "index.sqlite"
    LocalLiteratureIndex(db).ingest_papers([
        {"paperId": "W1", "title": "County BYM2 mortality spatial disparities", "abstract": "BYM2 spatial smoothing", "year": 2024, "doi": "10.1000/ag1"},
        {"paperId": "W2", "title": "Fay Herriot small area estimation ACS poverty", "abstract": "Temporal SAE", "year": 2025, "doi": "10.1000/ag2"},
    ], source="test")

    ag = build_research_agenda(db_path=db, domain_ids=("D01", "D02", "D05"), top_opportunities=5)
    assert ag["ok"] is True
    assert ag["status"] == "exploratory_hypothesis_seed"
    assert ag["domains_scanned"] == 3
    assert len(ag["top_opportunities"]) >= 1
    assert len(ag["agenda_sha256"]) == 64

    paths = write_research_agenda(ag, tmp_path / "agenda_out")
    assert Path(paths["json"]).exists() and Path(paths["markdown"]).exists()
    assert len(list_tool_names()) >= 16
