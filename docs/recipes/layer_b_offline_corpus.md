# Recipe: Managing the Offline Layer B SSD Literature & Passage Index

Use this workflow to seed, query, and maintain the standalone Layer B (`layer_b_openscholar/`) SQLite FTS5 literature and PDF passage index stored on the external SSD (`/run/media/hobo/Samsung 850 EVO SSD/layer_b_openscholar/`).

## Strict Isolation Rule
- `layer_b_openscholar/` never imports `census`. All outputs are exploratory (`status: "exploratory_hypothesis_seed"`) and require human pre-registration before entering Layer A.

## Steps

1. **Seed the 5 core epidemiology/demography topics (requires network):**
   - `python -m layer_b_openscholar seed-domain --limit-per-query 20`
2. **Run the one-command offline exploratory pipeline:**
   - `python -m layer_b_openscholar run-pipeline "<topic>" --geography county --method spatial_bym2 --out studies_output/layer_b_pipeline`
   - Emits `dossier.json`, `references.bib`, `hypothesis_seeds.md`, `gap_matrix.json`, `manifest_seed.json`, `manifest_seed.md`, and `bridge_report.json`.
3. **Or drive via Layer B MCP (9 tools):**
   - `local_search_literature`, `search_passages`, `build_gap_matrix`, `draft_manifest_seed`, `validate_handoff_seed`, `run_exploratory_pipeline`.
4. **Hand off to Layer A:**
   - Follow `get_recipe("literature_to_preregistration")` to review `bridge_report.json`, verify a validated method via Layer A `list_manifest_methods`, and register a frozen Layer A manifest.
