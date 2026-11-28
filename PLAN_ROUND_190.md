# Plan — Round 190: Layer B Neural Bridge, Cross-Encoder Reranker Option & EPMC Full-Text Resilience (`v0.186.0`)

## 1. Strategic Objective
Harden the Tier 2 neural stack introduced in Round 186 so it runs warning-free, exposes clear runtime diagnostics, supports optional cross-encoder reranking on top-k RRF candidates (`OpenScholar/OpenScholar_Reranker` or `BAAI/bge-reranker-base`), and handles Europe PMC `fullTextXML` HTTP 500s gracefully with polite retries and cleaner candidate filtering (`inEPMC=Y` / `isOpenAccess=Y`).

## 2. Exact File Contracts
1. `layer_b_openscholar/vector_store.py`:
   - Fix `FutureWarning` from `sentence-transformers>=6` by preferring `get_embedding_dimension()` with fallback to `get_sentence_embedding_dimension()`.
2. `layer_b_openscholar/neural_bridge.py` (new, strictly zero `census` imports):
   - `neural_runtime_status(vector_db_path=None)`: reports whether `sentence_transformers` / `torch` are importable in the current interpreter, whether the Samsung 850 EVO SSD `venv-neural` exists, and which embedding models + vector counts are stored in `vectors.sqlite`.
3. `layer_b_openscholar/fulltext_harvester.py`:
   - Add polite retry (up to 2 attempts with short backoff) on transient `5xx`/timeouts, skip already-cached/already-indexed `pmcid`s in `passages.sqlite` when `skip_existing=True` so repeated harvests always make forward progress on new PMC articles.
4. `layer_b_openscholar/mcp_server.py` & `layer_b_openscholar/__main__.py`:
   - Expose `neural_status` MCP tool (**21** Layer B MCP tools total) and `neural-status` CLI subcommand.
5. `tests/test_round190.py` & `docs/audits/round190_compatibility.md`.

## 3. Acceptance Gates
1. `pytest -q tests/test_round190.py layer_b_openscholar/tests/` passes with 0 failures and 0 `FutureWarning`s.
2. Strict zero-`census`-import check passes.

## 4. Iteration Log
- *2026-11-27:* Plan drafted after `v0.185.0` local commit & tag.
- *2026-11-27:* Implemented `layer_b_openscholar/neural_bridge.py` (`neural_status` MCP tool — 21 Layer B tools — and `neural-status` CLI), fixed `get_embedding_dimension` `FutureWarning` in `vector_store.py`, and added `skip_existing=True` + polite retry in `fulltext_harvester.py`. Verified via `tests/test_round190.py`.
