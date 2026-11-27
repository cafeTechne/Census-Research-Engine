# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 163: Persistent daemon operations (systemd --user unit generator & corpus health telemetry)."""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from .corpus_miner import DOMAIN_TOPICS, resolve_state_path
from .local_index import LocalLiteratureIndex, resolve_index_path
from .pdf_indexer import LocalPassageIndex


def render_systemd_unit(
    *,
    workdir: str | Path,
    python_exe: Optional[str | Path] = None,
    db_path: Optional[str | Path] = None,
    limit_per_query: int = 25,
    max_pages: int = 20,
    delay: float = 1.5,
    cycle_sleep: float = 1800.0,
) -> str:
    """Render a reboot-persistent systemd --user service unit for the Layer B background corpus miner."""
    wd = Path(workdir).resolve()
    py = Path(python_exe).resolve() if python_exe else Path(sys.executable).resolve()
    cmd = (
        f"{py} -m layer_b_openscholar mine-corpus --daemon "
        f"--limit-per-query {int(limit_per_query)} --max-pages {int(max_pages)} "
        f"--delay {float(delay)} --cycle-sleep {float(cycle_sleep)}"
    )
    if db_path:
        cmd += f' --db "{Path(db_path)}"'
    return (
        "[Unit]\n"
        "Description=Layer B OpenScholar Domain Corpus Miner (36 Epidemiology/Demography Topics)\n"
        "After=network-online.target\n"
        "Wants=network-online.target\n\n"
        "[Service]\n"
        "Type=simple\n"
        f"WorkingDirectory={wd}\n"
        f"ExecStart={cmd}\n"
        "Restart=on-failure\n"
        "RestartSec=30\n"
        "Nice=10\n\n"
        "[Install]\n"
        "WantedBy=default.target\n"
    )


def corpus_health_report(
    *,
    db_path: Optional[str | Path] = None,
    passages_db_path: Optional[str | Path] = None,
    state_path: Optional[str | Path] = None,
) -> Dict[str, Any]:
    """Compute comprehensive health/coverage telemetry for the Layer B SSD literature & passage indices."""
    idx = LocalLiteratureIndex(db_path)
    pidx = LocalPassageIndex(passages_db_path)
    lit_path = resolve_index_path(db_path)
    spath = resolve_state_path(db_path, state_path)

    total = 0
    with_doi = 0
    with_abstract = 0
    recent_2020 = 0
    top_sources: Dict[str, int] = {}
    if lit_path.exists():
        with sqlite3.connect(lit_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
            with_doi = conn.execute("SELECT COUNT(*) FROM papers WHERE doi IS NOT NULL AND TRIM(doi) != ''").fetchone()[0]
            with_abstract = conn.execute("SELECT COUNT(*) FROM papers WHERE abstract IS NOT NULL AND LENGTH(TRIM(abstract)) >= 40").fetchone()[0]
            recent_2020 = conn.execute("SELECT COUNT(*) FROM papers WHERE year >= 2020").fetchone()[0]
            for src, cnt in conn.execute("SELECT source, COUNT(*) FROM papers GROUP BY source ORDER BY COUNT(*) DESC LIMIT 15"):
                top_sources[str(src)] = int(cnt)

    miner_state: Dict[str, Any] = {}
    if spath.exists():
        try:
            miner_state = json.loads(spath.read_text(encoding="utf-8"))
        except Exception:
            miner_state = {}

    return {
        "ok": True,
        "status": "exploratory_hypothesis_seed",
        "domain_topics_configured": len(DOMAIN_TOPICS),
        "literature_index": {
            "db_path": str(lit_path),
            "paper_count": int(total),
            "doi_coverage_pct": round(100.0 * with_doi / total, 1) if total else 0.0,
            "abstract_coverage_pct": round(100.0 * with_abstract / total, 1) if total else 0.0,
            "recent_2020_plus_pct": round(100.0 * recent_2020 / total, 1) if total else 0.0,
            "top_sources": top_sources,
        },
        "passage_index": pidx.stats(),
        "miner_state_path": str(spath),
        "miner_cycles_completed": int(miner_state.get("cycles_completed", 0)),
        "miner_last_topic": miner_state.get("last_topic_id"),
        "miner_last_run_utc": miner_state.get("last_run_utc"),
        "miner_errors_count": int(miner_state.get("errors_count", 0)),
    }
