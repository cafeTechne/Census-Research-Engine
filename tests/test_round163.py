# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 163 tests: systemd --user unit generator & corpus health telemetry."""
from pathlib import Path

from layer_b_openscholar.daemon_ops import corpus_health_report, render_systemd_unit
from layer_b_openscholar.local_index import LocalLiteratureIndex


def test_r163_systemd_unit_and_corpus_health(tmp_path: Path):
    unit = render_systemd_unit(workdir=tmp_path, db_path=tmp_path / "index.sqlite")
    assert "[Unit]" in unit and "[Service]" in unit and "mine-corpus --daemon" in unit
    assert "Restart=on-failure" in unit

    db = tmp_path / "index.sqlite"
    LocalLiteratureIndex(db).ingest_papers([
        {"paperId": "W1", "title": "Paper 1", "abstract": "A" * 60, "year": 2024, "doi": "10.1000/p1"},
        {"paperId": "W2", "title": "Paper 2", "abstract": "", "year": 2018, "doi": ""},
    ], source="miner:test")

    rep = corpus_health_report(db_path=db, passages_db_path=tmp_path / "passages.sqlite", state_path=tmp_path / "state.json")
    assert rep["ok"] is True
    assert rep["domain_topics_configured"] == 36
    assert rep["literature_index"]["paper_count"] == 2
    assert rep["literature_index"]["doi_coverage_pct"] == 50.0
    assert rep["literature_index"]["abstract_coverage_pct"] == 50.0
    assert rep["literature_index"]["recent_2020_plus_pct"] == 50.0
