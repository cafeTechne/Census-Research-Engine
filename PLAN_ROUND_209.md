# Plan — Round 209: Layer B Domain Synonym Query Expansion & Passage Vector Sync (`v0.205.0`)

## 1. Strategic Objective
Improve Layer B Hybrid RAG recall on domain-specific acronyms and statistical methods by adding a curated, deterministic `layer_b_openscholar/query_expansion.py` module (`expand_domain_query()`) wired into `rag.py:query_hybrid_rag(..., expand_synonyms=True)`, and add `sync_passages_to_vectors()` in `vector_store.py` so local study/XML passages can also be indexed in `vectors.sqlite`.

## 2. Exact File Contracts
1. `layer_b_openscholar/query_expansion.py`: `DOMAIN_SYNONYMS` dictionary (`bym2`, `scpc`, `rpp`, `kww`, `pums`, `maup`, `qba`, `sae`, `vre`, `rdd`, `did`, `e-value`, `fay-herriot`) and `expand_domain_query(query)`.
2. `layer_b_openscholar/rag.py`: Optional `expand_synonyms: bool = True` feeding expanded query into `lit_idx.search_fts()` while keeping original query for BM25/vector scoring and reporting `expanded_query` when terms were added.
3. `layer_b_openscholar/vector_store.py`: Add `sync_passages_to_vectors(passages_db_path, vector_db_path, embedder=None)`.
4. `tests/test_round209.py`, `docs/audits/round209_compatibility.md`, and `0.205.0` version/hygiene sync.

## 3. Iteration Log
- *2026-11-27 (Cron #4):* Plan drafted and implemented strictly inside the sandbox.
