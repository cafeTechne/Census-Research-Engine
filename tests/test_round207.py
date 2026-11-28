# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 207 tests: Layer B SQLite WAL concurrency mode and vectorized min_year SQL pre-filter."""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

from layer_b_openscholar.local_index import LocalLiteratureIndex
from layer_b_openscholar.pdf_indexer import LocalPassageIndex
from layer_b_openscholar.vector_store import LocalVectorStore

ROOT = Path(__file__).resolve().parents[1]


def test_layer_b_sqlite_wal_mode_and_vector_min_year_prefilter(tmp_path: Path):
    lit_db = tmp_path / "index.sqlite"
    pas_db = tmp_path / "passages.sqlite"
    vec_db = tmp_path / "vectors.sqlite"

    lit = LocalLiteratureIndex(lit_db)
    pas = LocalPassageIndex(pas_db)
    vec = LocalVectorStore(vec_db)

    for db in (lit_db, pas_db, vec_db):
        with sqlite3.connect(db) as conn:
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert str(mode).lower() == "wal", f"{db} journal_mode={mode}"

    vec.upsert_papers([
        {"paperId": "W_OLD", "title": "Spatial mortality analysis", "abstract": "Classic paper", "year": 2015},
        {"paperId": "W_NEW", "title": "Spatial mortality analysis BYM2", "abstract": "Recent paper", "year": 2025},
    ])
    hits_all = vec.search("spatial mortality", top_k=5)
    hits_recent = vec.search("spatial mortality", top_k=5, min_year=2022)
    assert len(hits_all) == 2
    assert len(hits_recent) == 1 and hits_recent[0]["paperId"] == "W_NEW"


def test_r207_release_hygiene_passes_at_v0203():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/release_hygiene_check.py")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rep = json.loads(proc.stdout)
    assert rep["ok"] is True and rep["version"] >= "0.203.0"
