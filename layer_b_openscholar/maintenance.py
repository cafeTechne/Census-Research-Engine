# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 179: Layer B Corpus Integrity Auditor, Orphan-Vector Pruner & Compaction Utility."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional

from .local_index import resolve_index_path


def audit_and_compact_corpus(
    *,
    db_path: Optional[str | Path] = None,
    vector_db_path: Optional[str | Path] = None,
    vacuum: bool = True,
) -> Dict[str, Any]:
    """Verify FTS5 integrity, audit duplicate normalized titles, prune orphan vectors, and optionally VACUUM."""
    lit_path = resolve_index_path(db_path)
    vpath = Path(vector_db_path) if vector_db_path is not None else lit_path.with_name("vectors.sqlite")

    fts_ok = True
    paper_count = 0
    duplicate_title_groups = 0
    valid_ids: set[str] = set()
    if lit_path.exists():
        with sqlite3.connect(lit_path) as conn:
            paper_count = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
            rows = conn.execute("SELECT paper_id, doi, title FROM papers").fetchall()
            seen_titles: Dict[str, int] = {}
            for pid, doi, title in rows:
                if pid:
                    valid_ids.add(str(pid))
                if doi:
                    valid_ids.add(str(doi))
                if title:
                    valid_ids.add(str(title))
                    norm = " ".join(str(title).lower().split())
                    seen_titles[norm] = seen_titles.get(norm, 0) + 1
            duplicate_title_groups = sum(1 for c in seen_titles.values() if c > 1)
            try:
                conn.execute("INSERT INTO papers_fts(papers_fts) VALUES('integrity-check')")
            except Exception:
                fts_ok = False
        if vacuum:
            vcon = sqlite3.connect(lit_path, isolation_level=None)
            try:
                vcon.execute("VACUUM")
            finally:
                vcon.close()

    orphan_vectors_removed = 0
    vector_count = 0
    if vpath.exists():
        with sqlite3.connect(vpath) as vconn:
            vrows = vconn.execute("SELECT item_id FROM embeddings").fetchall()
            orphans = [(r[0],) for r in vrows if str(r[0]) not in valid_ids]
            if orphans:
                vconn.executemany("DELETE FROM embeddings WHERE item_id = ?", orphans)
                orphan_vectors_removed = len(orphans)
            vector_count = vconn.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]
        if vacuum:
            vcon2 = sqlite3.connect(vpath, isolation_level=None)
            try:
                vcon2.execute("VACUUM")
            finally:
                vcon2.close()

    return {
        "ok": bool(fts_ok),
        "status": "exploratory_hypothesis_seed",
        "literature_db": str(lit_path),
        "paper_count": int(paper_count),
        "fts5_integrity_ok": bool(fts_ok),
        "duplicate_title_groups": int(duplicate_title_groups),
        "vector_db": str(vpath),
        "vector_count": int(vector_count),
        "orphan_vectors_removed": int(orphan_vectors_removed),
        "vacuumed": bool(vacuum),
    }


def dedupe_title_duplicates(
    *,
    db_path: Optional[str | Path] = None,
    vector_db_path: Optional[str | Path] = None,
) -> Dict[str, Any]:
    """Merge normalized-title duplicates in index.sqlite (keeping richest DOI/abstract/citation row) and prune vectors."""
    lit_path = resolve_index_path(db_path)
    removed = 0
    if lit_path.exists():
        with sqlite3.connect(lit_path) as conn:
            rows = conn.execute(
                "SELECT rowid, paper_id, title, doi, abstract, citation_count FROM papers"
            ).fetchall()
            groups: Dict[str, list] = {}
            for r in rows:
                norm = " ".join(str(r[2] or "").lower().split())
                if norm:
                    groups.setdefault(norm, []).append(r)

            to_delete = []
            for norm, grp in groups.items():
                if len(grp) <= 1:
                    continue
                # Score: has DOI (+1000), abstract length, citation count
                grp_sorted = sorted(
                    grp,
                    key=lambda r: (
                        1 if (r[3] and str(r[3]).strip()) else 0,
                        len(str(r[4] or "").strip()),
                        int(r[5] or 0),
                    ),
                    reverse=True,
                )
                for dup in grp_sorted[1:]:
                    to_delete.append((dup[0],))
            if to_delete:
                conn.executemany("DELETE FROM papers WHERE rowid = ?", to_delete)
                removed = len(to_delete)
                conn.execute("INSERT INTO papers_fts(papers_fts) VALUES('rebuild')")

    compact = audit_and_compact_corpus(db_path=lit_path, vector_db_path=vector_db_path, vacuum=True)
    return {
        **compact,
        "duplicate_rows_removed": int(removed),
    }
