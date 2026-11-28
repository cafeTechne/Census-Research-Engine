# SPDX-License-Identifier: AGPL-3.0-or-later
"""Domain-scoped offline SQLite FTS5 literature index targeting the Samsung 850 EVO SSD."""
from __future__ import annotations

import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

SAMSUNG_EVO_MOUNT = Path("/run/media/hobo/Samsung 850 EVO SSD")
DEFAULT_SSD_INDEX_PATH = SAMSUNG_EVO_MOUNT / "layer_b_openscholar" / "index.sqlite"
FALLBACK_INDEX_PATH = Path(".cache/layer_b_openscholar/index.sqlite")
_FTS_TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")


def resolve_index_path(db_path: Optional[str | Path] = None) -> Path:
    """Resolve the offline SQLite FTS5 index path.

    Priority: explicit ``db_path`` -> ``LAYER_B_INDEX_PATH`` env var ->
    Samsung 850 EVO SSD (when mounted) -> local workspace fallback.
    """
    if db_path is not None:
        return Path(db_path)
    env_p = os.environ.get("LAYER_B_INDEX_PATH", "").strip()
    if env_p:
        return Path(env_p)
    if SAMSUNG_EVO_MOUNT.exists():
        return DEFAULT_SSD_INDEX_PATH
    return FALLBACK_INDEX_PATH


class LocalLiteratureIndex:
    """Offline SQLite FTS5 store for domain-scoped epidemiology/demography/spatial corpora."""

    def __init__(self, db_path: Optional[str | Path] = None) -> None:
        self.db_path = resolve_index_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS papers (
                    paper_id TEXT PRIMARY KEY,
                    doi TEXT,
                    title TEXT NOT NULL,
                    abstract TEXT NOT NULL,
                    year INTEGER,
                    venue TEXT,
                    citation_count INTEGER DEFAULT 0,
                    authors_json TEXT NOT NULL,
                    url TEXT,
                    open_access_pdf TEXT,
                    source TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS papers_fts USING fts5(
                    paper_id UNINDEXED,
                    title,
                    abstract,
                    venue
                )
                """
            )

    def ingest_papers(self, papers: Iterable[Dict[str, Any]], source: str = "local") -> int:
        inserted = 0
        with self._connect() as conn:
            for p in papers:
                pid = (p.get("paperId") or p.get("doi") or "").strip()
                title = (p.get("title") or "").strip()
                if not pid or not title:
                    continue
                abstract = (p.get("abstract") or "").strip()
                venue = (p.get("venue") or "").strip()
                conn.execute(
                    """
                    INSERT OR REPLACE INTO papers
                    (paper_id, doi, title, abstract, year, venue, citation_count, authors_json, url, open_access_pdf, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        pid,
                        p.get("doi") or "",
                        title,
                        abstract,
                        p.get("year"),
                        venue,
                        int(p.get("citationCount") or 0),
                        json.dumps(p.get("authors") or []),
                        p.get("url") or "",
                        p.get("openAccessPdf") or "",
                        source,
                    ),
                )
                conn.execute("DELETE FROM papers_fts WHERE paper_id = ?", (pid,))
                conn.execute(
                    "INSERT INTO papers_fts (paper_id, title, abstract, venue) VALUES (?, ?, ?, ?)",
                    (pid, title, abstract, venue),
                )
                inserted += 1
        return inserted

    def ingest_jsonl(self, jsonl_path: str | Path, source: str = "jsonl") -> int:
        p = Path(jsonl_path)
        papers = [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
        return self.ingest_papers(papers, source=source)

    def search_fts(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        tokens = _FTS_TOKEN_RE.findall(query)
        if not tokens:
            return []
        fts_query = " OR ".join(dict.fromkeys(tokens))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT p.*, bm25(papers_fts) AS fts_rank
                FROM papers_fts
                JOIN papers p ON p.paper_id = papers_fts.paper_id
                WHERE papers_fts MATCH ?
                ORDER BY fts_rank ASC
                LIMIT ?
                """,
                (fts_query, max(int(limit), 1)),
            ).fetchall()
        out: List[Dict[str, Any]] = []
        for r in rows:
            out.append({
                "paperId": r["paper_id"],
                "doi": r["doi"],
                "title": r["title"],
                "abstract": r["abstract"],
                "year": r["year"],
                "venue": r["venue"],
                "citationCount": r["citation_count"],
                "authors": json.loads(r["authors_json"]),
                "url": r["url"],
                "openAccessPdf": r["open_access_pdf"],
            })
        return out

    def stats(self) -> Dict[str, Any]:
        with self._connect() as conn:
            count = int(conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0])
            by_source = {
                row[0]: int(row[1])
                for row in conn.execute("SELECT source, COUNT(*) FROM papers GROUP BY source").fetchall()
            }
        return {"db_path": str(self.db_path), "paper_count": count, "by_source": by_source}
