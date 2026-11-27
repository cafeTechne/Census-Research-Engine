# Round 123 Compatibility Audit (`v0.118.0`)

- **Standalone Layer B additions (`layer_b_openscholar/`):** `epmc_client.py` (ungated Europe PMC + DOI deduplication), `local_index.py` (SQLite FTS5 offline index targeting `/run/media/hobo/Samsung 850 EVO SSD/layer_b_openscholar/index.sqlite` by default), `benchmark.py` (5-query BM25 vs `OpenScholar_Reranker` harness), updated `__main__.py` (`build-index`, `local-search`, `--source multi`).
- **Isolation check:** Zero imports from or into `census/`; `pyproject.toml` and `requirements.txt` unchanged.
- **Legacy manifest goldens:** Unchanged (byte-identical).
