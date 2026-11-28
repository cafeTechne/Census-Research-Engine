# Round 190 Compatibility Audit — Layer B Neural Bridge & EPMC Resilience (`v0.186.0`)

- **Date:** 2026-11-27
- **Review status:** author self-review, not independent
- **Summary of changes:**
  - Fixed `FutureWarning` in `layer_b_openscholar/vector_store.py` (`get_embedding_dimension` with fallback).
  - Created `layer_b_openscholar/neural_bridge.py` (`neural_runtime_status`), exposed as `neural_status` MCP tool (**21** Layer B tools) and `neural-status` CLI subcommand.
  - Added `skip_existing=True` and polite retry logic in `layer_b_openscholar/fulltext_harvester.py`.
- **Isolation:** Strictly zero `census` imports in `layer_b_openscholar/`.
