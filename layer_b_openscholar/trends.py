# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 174: Multi-Domain Publication Velocity & Citation Trend Analyzer (isolated Layer B)."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from statistics import median
from typing import Any, Dict, List, Optional

from .corpus_miner import DOMAIN_TOPICS
from .local_index import resolve_index_path


def analyze_domain_trends(
    *,
    db_path: Optional[str | Path] = None,
    top_n: int = 15,
) -> Dict[str, Any]:
    """Compute per-domain publication velocity (pre-2020, 2020-2023, 2024+), median citations & OA PDF rate."""
    lit_path = resolve_index_path(db_path)
    if not lit_path.exists():
        return {
            "ok": True,
            "status": "exploratory_hypothesis_seed",
            "total_papers": 0,
            "domains": [],
            "trends_sha256": hashlib.sha256(b"empty").hexdigest(),
        }

    with sqlite3.connect(lit_path) as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(papers)").fetchall()}
        oa_expr = "open_access_pdf" if "open_access_pdf" in cols else ("raw_json" if "raw_json" in cols else "''")
        rows = conn.execute(
            f"SELECT source, year, citation_count, {oa_expr} FROM papers"
        ).fetchall()

    by_domain: Dict[str, List[tuple]] = {}
    for src, yr, cites, oa_val in rows:
        src_s = str(src or "unknown")
        if src_s.startswith("miner:"):
            parts = src_s.split(":")
            dom = parts[1] if len(parts) >= 2 else src_s
        else:
            dom = src_s
        has_oa = False
        if oa_val:
            s = str(oa_val).strip()
            if s.startswith("{"):
                try:
                    has_oa = bool((json.loads(s).get("openAccessPdf") or "").strip())
                except Exception:
                    has_oa = False
            else:
                has_oa = bool(s)
        by_domain.setdefault(dom, []).append((yr, int(cites or 0), has_oa))

    summaries: List[Dict[str, Any]] = []
    for dom, items in by_domain.items():
        n = len(items)
        pre20 = sum(1 for y, _, _ in items if isinstance(y, int) and y < 2020)
        y20_23 = sum(1 for y, _, _ in items if isinstance(y, int) and 2020 <= y <= 2023)
        y24p = sum(1 for y, _, _ in items if isinstance(y, int) and y >= 2024)
        cites = [c for _, c, _ in items]
        oa_cnt = sum(1 for _, _, oa in items if oa)
        summaries.append({
            "domain": dom,
            "paper_count": n,
            "pre_2020": pre20,
            "y2020_2023": y20_23,
            "y2024_plus": y24p,
            "recent_share_pct": round(100.0 * y24p / n, 1) if n else 0.0,
            "median_citations": float(median(cites)) if cites else 0.0,
            "oa_pdf_pct": round(100.0 * oa_cnt / n, 1) if n else 0.0,
        })

    summaries.sort(key=lambda d: (-d["y2024_plus"], -d["paper_count"], d["domain"]))
    top_domains = summaries[:top_n]
    sha = hashlib.sha256(
        json.dumps(top_domains, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "ok": True,
        "status": "exploratory_hypothesis_seed",
        "configured_domains": len(DOMAIN_TOPICS),
        "observed_domains": len(summaries),
        "total_papers": len(rows),
        "top_fastest_growing": top_domains,
        "trends_sha256": sha,
    }
