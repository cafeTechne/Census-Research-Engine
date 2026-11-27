# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 133: Page/section-level local document & PDF passage indexer (Architecture v11 Layer B)."""
from __future__ import annotations

import hashlib
import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

SAMSUNG_EVO_MOUNT = Path("/run/media/hobo/Samsung 850 EVO SSD")
DEFAULT_SSD_PASSAGES_PATH = SAMSUNG_EVO_MOUNT / "layer_b_openscholar" / "passages.sqlite"
FALLBACK_PASSAGES_PATH = Path(".cache/layer_b_openscholar/passages.sqlite")
_TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")


def resolve_passages_path(db_path: Optional[str | Path] = None) -> Path:
    if db_path is not None:
        return Path(db_path)
    env_p = os.environ.get("LAYER_B_PASSAGES_PATH", "").strip()
    if env_p:
        return Path(env_p)
    if SAMSUNG_EVO_MOUNT.exists():
        return DEFAULT_SSD_PASSAGES_PATH
    return FALLBACK_PASSAGES_PATH


def _chunk_text(text: str, max_chars: int = 900) -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []
    pos = 0
    for para in re.split(r"\n\s*\n+", text):
        p = para.strip()
        if not p:
            continue
        start = text.find(p, pos)
        if start < 0:
            start = pos
        for off in range(0, len(p), max_chars):
            piece = p[off : off + max_chars].strip()
            if piece:
                chunks.append({"text": piece, "char_start": start + off, "char_end": start + off + len(piece)})
        pos = start + len(p)
    return chunks


def extract_document_passages(path: str | Path, max_chars: int = 900) -> List[Dict[str, Any]]:
    """Extract page/section-numbered passages from a local PDF, Markdown, or text file."""
    p = Path(path)
    raw_bytes = p.read_bytes()
    file_sha = hashlib.sha256(raw_bytes).hexdigest()
    ext = p.suffix.lower()
    passages: List[Dict[str, Any]] = []

    if ext == ".pdf":
        try:
            from pypdf import PdfReader
        except Exception as exc:
            raise RuntimeError("Indexing .pdf files requires optional 'pypdf' package") from exc
        reader = PdfReader(str(p))
        for page_num, page in enumerate(reader.pages, 1):
            txt = (page.extract_text() or "").strip()
            for idx, ch in enumerate(_chunk_text(txt, max_chars=max_chars), 1):
                passages.append({
                    "doc_path": str(p),
                    "doc_name": p.name,
                    "doc_sha256": file_sha,
                    "page": page_num,
                    "chunk_index": idx,
                    "char_start": ch["char_start"],
                    "char_end": ch["char_end"],
                    "text": ch["text"],
                })
    else:
        txt = raw_bytes.decode("utf-8", errors="replace")
        for idx, ch in enumerate(_chunk_text(txt, max_chars=max_chars), 1):
            passages.append({
                "doc_path": str(p),
                "doc_name": p.name,
                "doc_sha256": file_sha,
                "page": 1,
                "chunk_index": idx,
                "char_start": ch["char_start"],
                "char_end": ch["char_end"],
                "text": ch["text"],
            })
    return passages


class LocalPassageIndex:
    """Offline SQLite FTS5 passage index with immutable source SHA-256 and page/span citations."""

    def __init__(self, db_path: Optional[str | Path] = None) -> None:
        self.db_path = resolve_passages_path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS passages (
                    passage_id TEXT PRIMARY KEY,
                    doc_path TEXT NOT NULL,
                    doc_name TEXT NOT NULL,
                    doc_sha256 TEXT NOT NULL,
                    page INTEGER NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    char_start INTEGER NOT NULL,
                    char_end INTEGER NOT NULL,
                    text TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS passages_fts USING fts5(
                    passage_id UNINDEXED,
                    doc_name,
                    text
                )
                """
            )

    def index_file(self, path: str | Path, max_chars: int = 900) -> int:
        rows = extract_document_passages(path, max_chars=max_chars)
        inserted = 0
        with self._connect() as conn:
            for r in rows:
                pid = hashlib.sha256(
                    f"{r['doc_sha256']}:{r['page']}:{r['chunk_index']}".encode("utf-8")
                ).hexdigest()[:24]
                conn.execute(
                    """
                    INSERT OR REPLACE INTO passages
                    (passage_id, doc_path, doc_name, doc_sha256, page, chunk_index, char_start, char_end, text)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (pid, r["doc_path"], r["doc_name"], r["doc_sha256"], r["page"],
                     r["chunk_index"], r["char_start"], r["char_end"], r["text"]),
                )
                conn.execute("DELETE FROM passages_fts WHERE passage_id = ?", (pid,))
                conn.execute("INSERT INTO passages_fts (passage_id, doc_name, text) VALUES (?, ?, ?)",
                             (pid, r["doc_name"], r["text"]))
                inserted += 1
        return inserted

    def search_passages(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        tokens = _TOKEN_RE.findall(query)
        if not tokens:
            return []
        fts_query = " OR ".join(dict.fromkeys(tokens))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT p.*, bm25(passages_fts) AS rank
                FROM passages_fts
                JOIN passages p ON p.passage_id = passages_fts.passage_id
                WHERE passages_fts MATCH ?
                ORDER BY rank ASC
                LIMIT ?
                """,
                (fts_query, max(int(limit), 1)),
            ).fetchall()
        return [
            {
                "passage_id": r["passage_id"],
                "doc_name": r["doc_name"],
                "doc_path": r["doc_path"],
                "doc_sha256": r["doc_sha256"],
                "page": int(r["page"]),
                "char_span": [int(r["char_start"]), int(r["char_end"])],
                "text": r["text"],
                "status": "exploratory_hypothesis_seed",
            }
            for r in rows
        ]

    def stats(self) -> Dict[str, Any]:
        with self._connect() as conn:
            n_passages = int(conn.execute("SELECT COUNT(*) FROM passages").fetchone()[0])
            n_docs = int(conn.execute("SELECT COUNT(DISTINCT doc_sha256) FROM passages").fetchone()[0])
        return {"db_path": str(self.db_path), "passage_count": n_passages, "doc_count": n_docs}
