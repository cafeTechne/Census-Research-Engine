# Round 209 Compatibility Audit — Layer B Domain Synonym Expansion & Passage Vector Sync (`v0.205.0`)

- **Date:** 2026-11-27
- **Review status:** author self-review, not independent
- **Summary:** Added `layer_b_openscholar/query_expansion.py` (`expand_domain_query`) wired into `rag.py:query_hybrid_rag(expand_synonyms=True)` and added `sync_passages_to_vectors()` in `vector_store.py`. Strictly zero `census` imports.
