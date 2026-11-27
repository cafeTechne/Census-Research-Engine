# Round 186 Compatibility Audit — Tier 2 Neural BGE RAG, OpenAlex Polite Pool & EPMC XML Harvester (`v0.181.0`)

- **Date:** 2026-11-27
- **Review status:** author self-review, not independent
- **Summary of changes:**
  - Added `OPENALEX_MAILTO` / `OPENALEX_API_KEY` polite pool parameters and `Retry-After` exponential backoff on HTTP `429`/`5xx` in `layer_b_openscholar/s2_client.py` and `layer_b_openscholar/citation_expander.py`.
  - Added `layer_b_openscholar/fulltext_harvester.py` (Europe PMC open-access JATS XML section parser -> `passages.sqlite`), wired `harvest-fulltext` CLI and `harvest_fulltext` MCP tool (`20` Layer B MCP tools total).
  - Upgraded `layer_b_openscholar/vector_store.py` to composite primary key `(item_id, model_name)` with seamless migration, allowing `BAAI/bge-small-en-v1.5` (384-dim) and `hash_projection_d256` to coexist on the Samsung 850 EVO SSD (`2,631` vectors each, `5,262` total rows).
  - Provisioned isolated Python 3.12 `venv-neural` on the Samsung 850 EVO SSD; zero changes to Layer A `.venv` or `pyproject.toml`, and zero `census/` imports in `layer_b_openscholar/`.
  - Added `layer_b_openscholar/neural_benchmark.py` and `tests/test_round186.py`.
