# Round 166 Compatibility Audit (`v0.161.0`)

- **Scope:** Added `sync_from_literature_index` in `layer_b_openscholar/vector_store.py`, upgraded `layer_b_openscholar/rag.py` to 3-way `FTS5 + BM25 + Vector Cosine` RRF, and wired `sync-vectors` CLI & `sync_vectors` MCP tool.
- **Layer B Isolation:** Zero `census` imports; all outputs tagged `exploratory_hypothesis_seed`.
- **Review Note:** Author self-review, not independent.
