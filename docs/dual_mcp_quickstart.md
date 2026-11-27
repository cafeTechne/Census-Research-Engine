# Dual-MCP Quickstart (Layer A Confirmatory + Layer B Exploratory)

This repository runs two strictly isolated MCP servers so exploratory literature discovery never contaminates confirmatory statistical inference:

- **Layer A (`mcp_server.py`):** Confirmatory ACS/microdata/spatial/epidemiology research engine (`84` tools across `7` profiles, `28` pre-registered manifest methods, `33` task recipes).
- **Layer B (`python -m layer_b_openscholar.mcp_server`):** Exploratory literature mining, Europe PMC full-text XML harvesting, and 3-way Hybrid RAG (`20` tools, strictly zero `census/` imports).

## 1. Verify Your Environment

```bash
.venv/bin/python -m census doctor --json
```

Expected: `"ok": true`, `"bundled_data_ok": true`, and counts for recipes, manifest methods, and MCP profiles. `CENSUS_API_KEY` is reported as a boolean (`has_census_api_key`) and never printed.

## 2. Configure Both MCP Servers

Copy [`examples/mcp/dual_mcp_config.json`](../examples/mcp/dual_mcp_config.json) into your MCP client (Claude Desktop, Cursor, or Antigravity), replacing `${WORKSPACE}` with the repository path:

- Use `--profile publication` or `--profile epidemiology` for focused research workflows, or `--profile full` for all 84 Layer A tools.
- Set `OPENALEX_MAILTO` (optional) to place Layer B literature queries into OpenAlex's polite pool (10 req/s, 100k req/day).

## 3. End-to-End Two-Layer Research Loop

1. **Explore in Layer B (`exploratory_hypothesis_seed`):**
   ```bash
   .venv/bin/python -m layer_b_openscholar rag-query "county mortality spatial autocorrelation BYM2" --top-k 8
   .venv/bin/python -m layer_b_openscholar run-pipeline "county stroke mortality poverty BYM2" --out studies_output/seed_stroke
   ```
2. **Human Pre-Registration Gate:**
   Inspect `studies_output/seed_stroke/bridge_report.json` and `manifest_seed.md`. Layer B never calls `create_manifest` or `run_manifest` automatically.
3. **Confirmatory Execution in Layer A:**
   Use `create_manifest` -> `run_manifest` -> `make_results_bundle`, then verify every SHA-256 digest and LaTeX table:
   ```bash
   .venv/bin/python -m census verify-bundle studies_output/my_study/bundle
   ```

## 4. Optional Tier 2 Neural Embeddings (Isolated `venv-neural`)

Layer A's `.venv` stays lightweight with zero PyTorch dependencies. To enable dense scientific embeddings (`BAAI/bge-small-en-v1.5`) in Layer B without touching Layer A:

```bash
uv venv --python 3.12 /path/to/ssd/layer_b_openscholar/venv-neural
uv pip install --python /path/to/ssd/layer_b_openscholar/venv-neural/bin/python \
  --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple \
  torch sentence-transformers transformers numpy requests
HF_HOME=/path/to/ssd/layer_b_openscholar/hf_cache \
  /path/to/ssd/layer_b_openscholar/venv-neural/bin/python -m layer_b_openscholar sync-vectors --model BAAI/bge-small-en-v1.5
```
