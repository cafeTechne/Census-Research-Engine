# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 161: OpenAlex 1-hop citation-graph expander for isolated Layer B (zero census imports)."""
from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .local_index import LocalLiteratureIndex, resolve_index_path
from .s2_client import OPENALEX_BASE, USER_AGENT, OpenAlexClient


def expand_seed_citations(
    work_id: str,
    *,
    db_path: Optional[str | Path] = None,
    limit: int = 25,
    http_get: Optional[Callable[[str, Dict[str, Any], Dict[str, str]], Dict[str, Any]]] = None,
    max_retries: int = 3,
) -> Dict[str, Any]:
    """Fetch 1-hop citing works for an OpenAlex work ID (e.g. 'W4408165420') and ingest into FTS5."""
    wid = work_id.strip().rsplit("/", 1)[-1]
    url = f"{OPENALEX_BASE}/works"
    mailto = os.environ.get("OPENALEX_MAILTO", "").strip()
    api_key = os.environ.get("OPENALEX_API_KEY", "").strip()
    params: Dict[str, Any] = {"filter": f"cites:{wid}", "per-page": min(max(int(limit), 1), 100)}
    if mailto:
        params["mailto"] = mailto
    if api_key:
        params["api_key"] = api_key
    ua = f"{USER_AGENT} (mailto:{mailto})" if mailto else USER_AGENT
    headers = {"User-Agent": ua, "Accept": "application/json"}

    if http_get is not None:
        data = http_get(url, params, headers)
    else:
        import requests

        data = None
        for attempt in range(max(int(max_retries), 1)):
            resp = requests.get(url, params=params, headers=headers, timeout=30)
            if resp.status_code in (429, 500, 502, 503, 504) and attempt + 1 < max(int(max_retries), 1):
                retry_after = resp.headers.get("Retry-After")
                try:
                    sleep_s = float(retry_after) if retry_after else 2.0 * (2 ** attempt)
                except ValueError:
                    sleep_s = 2.0 * (2 ** attempt)
                time.sleep(min(max(sleep_s, 0.5), 30.0))
                continue
            resp.raise_for_status()
            data = resp.json()
            break
        if data is None:
            raise RuntimeError(f"OpenAlex citation expansion failed after retries: {wid}")

    papers = [OpenAlexClient.normalize_work(w) for w in (data.get("results") or []) if w.get("title")]
    idx = LocalLiteratureIndex(db_path)
    added = idx.ingest_papers(papers, source=f"citation_expand:{wid}")
    return {
        "ok": True,
        "status": "exploratory_hypothesis_seed",
        "seed_work_id": wid,
        "fetched": len(papers),
        "added": added,
        "stats": idx.stats(),
    }


def top_openalex_seeds(db_path: Optional[str | Path] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """Return top-cited OpenAlex work IDs ('W...') currently stored in index.sqlite."""
    path = resolve_index_path(db_path)
    if not path.exists():
        return []
    with sqlite3.connect(path) as conn:
        rows = conn.execute(
            "SELECT paper_id, title, year, citation_count, doi FROM papers "
            "WHERE paper_id LIKE 'W%' ORDER BY citation_count DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
    return [
        {"paperId": r[0], "title": r[1], "year": r[2], "citationCount": r[3], "doi": r[4]}
        for r in rows
    ]
