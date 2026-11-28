# Plan — Round 205 (N129/N130): Layer B Auto-Subprocess Neural Hook, Cross-Encoder Rerank Hook, Routing `R101–R103` & `v0.201.0` Sync

## 1. Strategic Objective
Wire `allow_subprocess_neural: bool = False` and optional second-stage `cross_encoder_rerank: bool = False` into `layer_b_openscholar/rag.py:query_hybrid_rag()`, expand `docs/agent_routing.md` (`R101–R103`, **103** rows), close `N129` (engine hook) and `N135` in `ROADMAP_BACKLOG.md`, extend `scripts/release_hygiene_check.py` through Round 205, and sync version `0.201.0`.

## 2. Exact File Contracts
1. `layer_b_openscholar/rag.py`: Add `allow_subprocess_neural: bool = False` and `rerank_top_k: Optional[int] = None` support.
2. `docs/agent_routing.md`: Append `R101–R103` (103 rows total).
3. `scripts/release_hygiene_check.py`: Extend through Round 205 (`range(126, 206)`).
4. Version sync `0.201.0`: `census/__init__.py`, `census/pipeline.py`, `CITATION.cff`, `CHANGELOG.md`, `STATUS.md`, `ROADMAP_BACKLOG.md`.
5. `tests/test_round205.py` & `docs/audits/round205_compatibility.md`.

## 3. Iteration Log
- *2026-11-27:* Plan drafted and implemented.
