# Plan — Round 186 (Track 3): True Semantic Neural Tier 2 RAG (N127), OpenAlex Polite Pool & Europe PMC Full-Text XML Harvester (`v0.181.0`)

## 1. Strategic Objective
Upgrade isolated Layer B (`layer_b_openscholar/`) from lexical-hybrid retrieval (`FTS5 + BM25 + hashed projection`) to **true semantic neural retrieval** on the Samsung 850 EVO SSD (`/run/media/hobo/Samsung 850 EVO SSD/layer_b_openscholar/`), while resolving OpenAlex anonymous rate limits (`429`) and harvesting open-access full-text sections from Europe PMC JATS XML into `passages.sqlite`.

## 2. Architectural & Hardware Constraints
- **Strict Layer B Isolation:** Zero imports from or into `census/`; `pyproject.toml`, `requirements.txt`, and Layer A's `.venv` remain 100% untouched.
- **Hardware Reality (probed 2026-11-27):**
  - No NVIDIA GPU (`NO_NVIDIA_GPU`); CPU-only PyTorch wheels (`https://download.pytorch.org/whl/cpu`) must be used.
  - Samsung 850 EVO SSD has **233 GB free** (`1%` used).
  - Isolated neural runtime placed at `/run/media/hobo/Samsung 850 EVO SSD/layer_b_openscholar/venv-neural` (Python 3.12 via `uv`, avoiding Python 3.14 PyTorch wheel gaps), with `HF_HOME=/run/media/hobo/Samsung 850 EVO SSD/layer_b_openscholar/hf_cache`.
- **Epistemic Boundary:** Every neural retrieval, full-text passage, and benchmark artifact remains tagged `status: "exploratory_hypothesis_seed"`.

## 3. Detailed Workstreams & Exact File Contracts

### Workstream A — OpenAlex Polite Pool & Retry Hardening (`layer_b_openscholar/s2_client.py`)
1. Support optional `OPENALEX_MAILTO` and `OPENALEX_API_KEY` environment variables in `OpenAlexClient.search_papers()` (and `citation_expander.py`):
   - Include `mailto=<OPENALEX_MAILTO>` in query params (and User-Agent) when set, placing requests in OpenAlex's polite pool (10 req/s, 100k req/day).
   - Add polite `Retry-After` / exponential backoff retry loop (up to 3 attempts) on HTTP `429` and `5xx` responses so background mining does not drop pages unnecessarily.

### Workstream B — Europe PMC Full-Text JATS XML Section Harvester (`layer_b_openscholar/fulltext_harvester.py`)
1. Query `index.sqlite` for open-access PMC papers (`paper_id LIKE 'PMC%'` or `openAccessPdf` containing `PMC`).
2. Fetch JATS XML via ungated `https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML` (with disk cache + polite delay).
3. Parse structured sections (`Introduction`, `Methods`, `Results`, `Discussion`, `Limitations`) using stdlib `xml.etree.ElementTree`, stripping tags cleanly via `strip_jats_html`.
4. Chunk sections (~800–1,200 chars) and ingest directly into `passages.sqlite` with immutable source SHA-256 and section metadata (`pmc_id`, `section_title`).
5. Wire `harvest-fulltext` CLI subcommand into `layer_b_openscholar/__main__.py` and `harvest_fulltext` MCP tool into `layer_b_openscholar/mcp_server.py` (20 Layer B MCP tools total).

### Workstream C — Isolated Neural Runtime & Dense Scientific Embeddings (`layer_b_openscholar/vector_store.py`, `layer_b_openscholar/rag.py`, `layer_b_openscholar/neural_benchmark.py`)
1. Provision `/run/media/hobo/Samsung 850 EVO SSD/layer_b_openscholar/venv-neural` (Python 3.12 via `uv`) with CPU-only `torch`, `sentence-transformers`, `transformers`, `numpy`, `requests`.
2. Upgrade `LocalVectorStore` (`layer_b_openscholar/vector_store.py`):
   - Support multi-model coexistence cleanly in `vectors.sqlite` (primary key `(item_id, model_name)` so `hash_projection_d256` and neural `BAAI/bge-small-en-v1.5` or `BAAI/bge-base-en-v1.5` coexist without overwriting each other!).
   - Auto-select the best available model present in `vectors.sqlite` during `query_hybrid_rag()` (preferring neural dense embeddings when the neural runtime is active, falling back seamlessly to `hash_projection_d256` in Layer A's `.venv`).
3. Embed all **2,631+ papers** in `/run/media/hobo/Samsung 850 EVO SSD/layer_b_openscholar/index.sqlite` using `BAAI/bge-small-en-v1.5` (384-dim, fast & high-accuracy on CPU) via `venv-neural`.
4. Run a head-to-head **5-query + domain benchmark** (`layer_b_openscholar/neural_benchmark.py`) comparing:
   - Lexical `FTS5 + BM25`
   - 3-way `FTS5 + BM25 + HashProjection`
   - 3-way `FTS5 + BM25 + Neural BGE Dense` (+ optional `OpenScholar/OpenScholar_Reranker` cross-encoder)
   Write reproducible benchmark report to `docs/audits/layer_b_neural_rag_benchmark.md`.

## 4. Failure Modes & Mitigations
- **Python 3.14 wheel incompatibility:** Solved by pinning `venv-neural` to Python 3.12 via `uv venv --python 3.12`.
- **Network/HF download latency or memory cap on CPU:** Use `BAAI/bge-small-en-v1.5` (133 MB, ~30–60s to embed 2,631 papers on CPU in batches of 64); test `OpenScholar/OpenScholar_Reranker` on top-10 candidates per query (fast even on CPU).
- **Schema migration on existing `vectors.sqlite`:** Detect old single-column PK `(item_id)` vs. composite PK `(item_id, model_name)` and migrate seamlessly without data loss.

## 5. Acceptance Gates
1. `pytest -q tests/test_round186.py layer_b_openscholar/tests/` passes with 0 failures in Layer A's `.venv` (zero new dependencies in `.venv`).
2. `scripts/release_hygiene_check.py` passes with zero `census` imports in `layer_b_openscholar/`.
3. Live SSD `vectors.sqlite` contains `>= 2,600` neural BGE embeddings and `passages.sqlite` contains harvested EPMC full-text XML sections.
4. `docs/audits/layer_b_neural_rag_benchmark.md` records measured latency & top-k ranking comparison across all 5 benchmark queries.

## 6. Iteration Log
- *2026-11-27:* Plan drafted after probing hardware (`NO_NVIDIA_GPU`, 233 GB free on Samsung 850 EVO SSD, `uv` available).
- *2026-11-27:* Implemented OpenAlex `OPENALEX_MAILTO`/`OPENALEX_API_KEY` + `Retry-After` backoff (`s2_client.py`, `citation_expander.py`), Europe PMC JATS XML full-text harvester (`fulltext_harvester.py`, `harvest-fulltext` CLI, `harvest_fulltext` MCP tool — 20 tools total), composite PK `(item_id, model_name)` migration in `vector_store.py`, and auto-neural selection in `rag.py`. Provisioned isolated Python 3.12 `venv-neural` on Samsung 850 EVO SSD, embedded all `2,631` SSD papers with `BAAI/bge-small-en-v1.5` (384-dim, coexisting with `2,631` `hash_projection_d256` rows = `5,262` total rows), harvested `198` new EPMC full-text XML passages (`1,148` total passages across `67` docs), and generated `docs/audits/layer_b_neural_rag_benchmark.md`. All `16` tests in `tests/test_round186.py layer_b_openscholar/tests/` passed.
