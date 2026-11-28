# Plan — Round 207: Layer B SQLite WAL Concurrency Hardening & Vector `min_year` SQL Pre-Filter (`v0.203.0`)

## 1. Strategic Objective
Harden Layer B's three SQLite stores (`local_index.py`, `vector_store.py`, `pdf_indexer.py`) for safe concurrent background daemon mining + live MCP/CLI queries via `PRAGMA journal_mode=WAL`, `PRAGMA busy_timeout=5000`, and `PRAGMA synchronous=NORMAL`, and push `min_year` filtering directly into SQLite inside `LocalVectorStore.search()` (wired through `rag.py`).

## 2. Exact File Contracts
1. `layer_b_openscholar/local_index.py`: Apply WAL + `busy_timeout=5000` + `synchronous=NORMAL` in `_connect()`.
2. `layer_b_openscholar/pdf_indexer.py`: Apply WAL + `busy_timeout=5000` + `synchronous=NORMAL` in `_connect()`.
3. `layer_b_openscholar/vector_store.py`: Add `_connect()` with WAL + `busy_timeout=5000` + `synchronous=NORMAL`, and add `min_year: Optional[int] = None` SQL pre-filter to `LocalVectorStore.search()`.
4. `layer_b_openscholar/rag.py`: Pass `min_year=min_year` directly to `vstore.search(...)`.
5. `tests/test_round207.py`, `docs/audits/round207_compatibility.md`, and `0.203.0` version/hygiene sync.

## 3. Iteration Log
- *2026-11-27 (Cron #2):* Plan drafted and implemented strictly inside the sandbox.
