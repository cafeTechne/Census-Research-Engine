# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 164 / 186: Pluggable SQLite + NumPy Multi-Model Vector Store for Layer B Hybrid RAG (N127).

Provides:
- ``HashProjectionEmbedder``: deterministic zero-dependency NumPy token/trigram projection
  (works immediately in ``.venv`` with no PyTorch/Transformers required).
- ``SentenceTransformerEmbedder``: Tier 2 neural embedder adapter for isolated ``venv-neural``
  (e.g. ``BAAI/bge-small-en-v1.5``, ``BAAI/bge-base-en-v1.5``, or ``allenai/specter2``).
- ``LocalVectorStore``: SQLite-backed float32 multi-model vector store with composite primary
  key ``(item_id, model_name)``, seamless schema migration, and exact NumPy cosine similarity.
"""
from __future__ import annotations

import hashlib
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Sequence

import numpy as np

from .local_index import resolve_index_path

DEFAULT_NEURAL_MODEL = "BAAI/bge-small-en-v1.5"


class Embedder(Protocol):
    dim: int
    model_name: str

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        ...


class HashProjectionEmbedder:
    """Deterministic zero-dependency word + character-trigram hashed L2-normalized embedding."""

    def __init__(self, dim: int = 256) -> None:
        self.dim = int(dim)
        self.model_name = f"hash_projection_d{self.dim}"

    def _encode_one(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        tokens = re.findall(r"[a-z0-9]{2,}", (text or "").lower())
        feats: List[str] = list(tokens)
        for tok in tokens:
            if len(tok) >= 4:
                for i in range(len(tok) - 2):
                    feats.append(f"3:{tok[i:i+3]}")
        for f in feats:
            h = hashlib.blake2b(f.encode("utf-8"), digest_size=8).digest()
            idx = int.from_bytes(h[:4], "little") % self.dim
            sign = 1.0 if (h[4] & 1) == 0 else -1.0
            vec[idx] += sign
        norm = float(np.linalg.norm(vec))
        return vec / norm if norm > 0 else vec

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        return np.vstack([self._encode_one(t) for t in texts]).astype(np.float32)


class SentenceTransformerEmbedder:
    """Tier 2 neural embedder adapter (requires sentence-transformers in isolated venv-neural)."""

    def __init__(self, model_name: str = DEFAULT_NEURAL_MODEL, batch_size: int = 64) -> None:
        from sentence_transformers import SentenceTransformer  # type: ignore

        self.model_name = model_name
        self.batch_size = int(batch_size)
        self._model = SentenceTransformer(model_name, device="cpu")
        dim_fn = getattr(self._model, "get_embedding_dimension", None) or self._model.get_sentence_embedding_dimension
        self.dim = int(dim_fn())

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        arr = self._model.encode(
            list(texts),
            batch_size=self.batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return np.asarray(arr, dtype=np.float32)


def resolve_vector_path(db_path: Optional[str | Path] = None) -> Path:
    if db_path is not None:
        return Path(db_path)
    return resolve_index_path(None).with_name("vectors.sqlite")


class LocalVectorStore:
    """SQLite-backed float32 multi-model embedding store with exact NumPy cosine similarity search."""

    def __init__(
        self,
        db_path: Optional[str | Path] = None,
        embedder: Optional[Embedder] = None,
    ) -> None:
        self.db_path = resolve_vector_path(db_path)
        self.embedder: Embedder = embedder or HashProjectionEmbedder(dim=256)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            tbl = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='embeddings'"
            ).fetchone()
            if tbl is None:
                conn.execute(
                    """
                    CREATE TABLE embeddings (
                        item_id TEXT NOT NULL,
                        title TEXT,
                        doi TEXT,
                        year INTEGER,
                        model_name TEXT NOT NULL,
                        dim INTEGER NOT NULL,
                        vec BLOB NOT NULL,
                        PRIMARY KEY (item_id, model_name)
                    )
                    """
                )
            elif "PRIMARY KEY (item_id, model_name)" not in (tbl[0] or ""):
                # Seamless schema migration from single-column PK (item_id) to composite PK
                conn.execute(
                    """
                    CREATE TABLE embeddings_v2 (
                        item_id TEXT NOT NULL,
                        title TEXT,
                        doi TEXT,
                        year INTEGER,
                        model_name TEXT NOT NULL,
                        dim INTEGER NOT NULL,
                        vec BLOB NOT NULL,
                        PRIMARY KEY (item_id, model_name)
                    )
                    """
                )
                conn.execute(
                    """
                    INSERT OR REPLACE INTO embeddings_v2 (item_id, title, doi, year, model_name, dim, vec)
                    SELECT item_id, title, doi, year, COALESCE(model_name, 'hash_projection_d256'), dim, vec
                    FROM embeddings
                    """
                )
                conn.execute("DROP TABLE embeddings")
                conn.execute("ALTER TABLE embeddings_v2 RENAME TO embeddings")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_embeddings_model ON embeddings(model_name, dim)"
            )

    def model_counts(self) -> Dict[str, int]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT model_name, COUNT(*) FROM embeddings GROUP BY model_name ORDER BY COUNT(*) DESC"
            ).fetchall()
        return {str(r[0]): int(r[1]) for r in rows}

    def existing_item_ids(self) -> set[str]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT item_id FROM embeddings WHERE model_name = ? AND dim = ?",
                (self.embedder.model_name, self.embedder.dim),
            ).fetchall()
        return {str(r[0]) for r in rows}

    def upsert_papers(
        self,
        papers: Sequence[Dict[str, Any]],
        *,
        incremental: bool = False,
        batch_size: int = 128,
    ) -> int:
        valid = [p for p in papers if p.get("title")]
        if not valid:
            return 0
        if incremental:
            have = self.existing_item_ids()
            valid = [
                p for p in valid
                if str(p.get("paperId") or p.get("doi") or p["title"]) not in have
            ]
            if not valid:
                return 0
        total = 0
        bsize = max(int(batch_size), 1)
        for off in range(0, len(valid), bsize):
            batch = valid[off : off + bsize]
            texts = [f"{p.get('title', '')}\n{p.get('abstract', '')}" for p in batch]
            vecs = self.embedder.embed(texts)
            rows = []
            for p, v in zip(batch, vecs):
                item_id = str(p.get("paperId") or p.get("doi") or p["title"])
                rows.append((
                    item_id,
                    str(p.get("title") or ""),
                    str(p.get("doi") or ""),
                    p.get("year"),
                    self.embedder.model_name,
                    self.embedder.dim,
                    np.asarray(v, dtype=np.float32).tobytes(),
                ))
            with sqlite3.connect(self.db_path) as conn:
                conn.executemany(
                    "INSERT OR REPLACE INTO embeddings (item_id, title, doi, year, model_name, dim, vec) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    rows,
                )
            total += len(rows)
        return total

    def search(self, query: str, top_k: int = 10, min_year: Optional[int] = None) -> List[Dict[str, Any]]:
        qvec = self.embedder.embed([query])[0]
        with self._connect() as conn:
            if min_year is not None:
                rows = conn.execute(
                    "SELECT item_id, title, doi, year, vec FROM embeddings "
                    "WHERE model_name = ? AND dim = ? AND year IS NOT NULL AND year >= ?",
                    (self.embedder.model_name, self.embedder.dim, int(min_year)),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT item_id, title, doi, year, vec FROM embeddings WHERE model_name = ? AND dim = ?",
                    (self.embedder.model_name, self.embedder.dim),
                ).fetchall()
        if not rows:
            return []
        mat = np.vstack([np.frombuffer(r[4], dtype=np.float32) for r in rows])
        scores = mat @ qvec
        order = np.argsort(-scores)[:top_k]
        return [
            {
                "paperId": rows[i][0],
                "title": rows[i][1],
                "doi": rows[i][2],
                "year": rows[i][3],
                "cosine_score": round(float(scores[i]), 6),
                "vector_model": self.embedder.model_name,
            }
            for i in order
        ]

    def stats(self) -> Dict[str, Any]:
        models = self.model_counts()
        active_cnt = models.get(self.embedder.model_name, 0)
        return {
            "db_path": str(self.db_path),
            "vector_count": int(active_cnt),
            "total_rows": int(sum(models.values())),
            "models": models,
            "model_name": self.embedder.model_name,
            "dim": self.embedder.dim,
        }


def sync_from_literature_index(
    db_path: Optional[str | Path] = None,
    vector_db_path: Optional[str | Path] = None,
    embedder: Optional[Embedder] = None,
    model_name: Optional[str] = None,
    incremental: bool = True,
) -> Dict[str, Any]:
    """Incrementally embed all papers in ``index.sqlite`` into ``vectors.sqlite``."""
    lit_path = resolve_index_path(db_path)
    if embedder is None and model_name and model_name != "hash":
        embedder = SentenceTransformerEmbedder(model_name=model_name)
    store = LocalVectorStore(db_path=vector_db_path or lit_path.with_name("vectors.sqlite"), embedder=embedder)
    if not lit_path.exists():
        return {"ok": True, "status": "exploratory_hypothesis_seed", "synced": 0, "stats": store.stats()}
    with sqlite3.connect(lit_path) as conn:
        rows = conn.execute("SELECT paper_id, title, abstract, year, doi FROM papers").fetchall()
    papers = [
        {"paperId": r[0], "title": r[1], "abstract": r[2] or "", "year": r[3], "doi": r[4] or ""}
        for r in rows
    ]
    synced = store.upsert_papers(papers, incremental=incremental)
    return {"ok": True, "status": "exploratory_hypothesis_seed", "synced": synced, "stats": store.stats()}


def sync_passages_to_vectors(
    passages_db_path: Optional[str | Path] = None,
    vector_db_path: Optional[str | Path] = None,
    embedder: Optional[Embedder] = None,
    incremental: bool = True,
) -> Dict[str, Any]:
    """Incrementally embed local study/XML passages from ``passages.sqlite`` into ``vectors.sqlite``."""
    from .pdf_indexer import resolve_passages_path

    ppath = resolve_passages_path(passages_db_path)
    store = LocalVectorStore(db_path=vector_db_path or ppath.with_name("vectors.sqlite"), embedder=embedder)
    if not ppath.exists():
        return {"ok": True, "status": "exploratory_hypothesis_seed", "synced": 0, "stats": store.stats()}
    with sqlite3.connect(ppath) as conn:
        rows = conn.execute("SELECT passage_id, doc_name, text FROM passages").fetchall()
    items = [
        {"paperId": f"psg:{r[0]}", "title": str(r[1] or "passage"), "abstract": str(r[2] or ""), "year": None, "doi": ""}
        for r in rows
    ]
    synced = store.upsert_papers(items, incremental=incremental)
    return {"ok": True, "status": "exploratory_hypothesis_seed", "synced": synced, "stats": store.stats()}
