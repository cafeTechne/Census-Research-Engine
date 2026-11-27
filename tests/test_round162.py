# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 162 tests: Hybrid RAG v2 JATS/HTML cleaning, filters, BibTeX export & Evidence Briefs."""
from pathlib import Path

from layer_b_openscholar.local_index import LocalLiteratureIndex
from layer_b_openscholar.rag import build_evidence_brief, query_hybrid_rag, strip_jats_html


def test_r162_jats_strip_filters_bibtex_and_evidence_brief(tmp_path: Path):
    assert strip_jats_html("<h4>Intro</h4>Hello &amp; <i>world</i>") == "Intro Hello & world"

    db = tmp_path / "idx.sqlite"
    pdb = tmp_path / "pas.sqlite"
    LocalLiteratureIndex(db).ingest_papers([
        {
            "paperId": "W1",
            "title": "County poverty spatial BYM2",
            "abstract": "<h4>Objective</h4>BYM2 county mortality analysis.",
            "year": 2024,
            "venue": "Spatial Epidemiology",
            "doi": "10.1000/a2024",
        },
        {
            "paperId": "W2",
            "title": "Older county poverty study",
            "abstract": "County mortality in 2012.",
            "year": 2012,
            "venue": "Old Journal",
            "doi": "10.1000/a2012",
        },
    ], source="miner:bym2")

    bib_out = tmp_path / "out.bib"
    rag = query_hybrid_rag("county poverty", db_path=db, passages_db_path=pdb, min_year=2020, export_bib_path=bib_out)
    assert rag["paper_hits"] == 1
    assert "<h4>" not in rag["context_markdown"]
    assert bib_out.exists() and "10.1000/a2024" in bib_out.read_text(encoding="utf-8")

    brief = build_evidence_brief("county poverty", db_path=db, passages_db_path=pdb, min_year=2020)
    assert brief["ok"] is True
    assert brief["year_range"] == [2024, 2024]
    assert brief["recent_2022_plus_count"] == 1
    assert brief["dois"] == ["10.1000/a2024"]
