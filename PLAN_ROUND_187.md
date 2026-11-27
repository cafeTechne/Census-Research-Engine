# Plan — Round 187 (Track 4): External User & Agent Polish — Two-Layer README, Dual-MCP Quickstart, `doctor` CLI & Wheel Packaging (`v0.182.0`)

## 1. Strategic Objective
Make the repository immediately intelligible, installable, and operable for external researchers and AI agent clients ahead of the December 2026 ACS 2021–2025 release: refresh `README.md` around the two-layer architecture (Layer A confirmatory engine + Layer B isolated research intelligence), ship ready-to-paste dual-MCP client config templates, add a `python -m census doctor` environment/integrity self-check, and verify clean wheel build & install.

## 2. Exact Deliverables & File Contracts

### Workstream A — `README.md` Two-Layer Architecture Refresh
1. Update the top summary, metrics, and release highlights in `README.md`:
   - Current capabilities (`v0.182.0` working tree; last tagged Zenodo release `v0.115.0` / `v0.77.0` clearly distinguished).
   - Accurate counts: `84+` MCP tools (Layer A) + `20` isolated MCP tools (Layer B), `28` pre-registered manifest methods, `33` workflow recipes (with keyword search), `84+` routing rows, `19+` pre-registered empirical studies.
   - Dedicated **"Two-Layer Architecture (Confirmatory Layer A vs. Exploratory Layer B)"** section with a crisp Mermaid/Markdown diagram showing the strict zero-import isolation boundary and human pre-registration gate.
   - Dedicated **"Dual-MCP Setup (Claude Desktop / Cursor / Antigravity)"** section referencing `examples/mcp/dual_mcp_config.json`.

### Workstream B — Dual-MCP Client Configuration & Operator Guide
1. Create `examples/mcp/dual_mcp_config.json`: ready-to-paste JSON snippet configuring both `census-research-engine` (Layer A, `--profile publication` / `epidemiology` / `core` / `full`) and `layer-b-openscholar` (Layer B isolated server).
2. Create `docs/dual_mcp_quickstart.md`: 5-minute walkthrough covering installation, profile selection, running Layer B `rag-query` / `run-pipeline`, human review of `bridge_report.json`, Layer A `create_manifest` / `run_manifest` / `verify_bundle`, and optional `.venv-layer-b` neural upgrade.

### Workstream C — `python -m census doctor` CLI Self-Check
1. Add `doctor` subcommand in `census/__main__.py` (calling a clean `census.diagnostics.doctor_report()` or `census.workflows_reporting.doctor_report()`):
   - Verifies Python/SciPy/pandas/statsmodels versions, bundled price-index & RPP CSV integrity, metadata archive availability, `CENSUS_API_KEY` presence (boolean only, **never** prints key value!), Layer A MCP profile loading, and recipe/manifest counts.
   - Exits `0` with structured JSON (`{"ok": true, ...}`).

### Workstream D — Packaging & Editable/Wheel Build Verification
1. Run `python -m build --wheel` (or verify `pyproject.toml` + `tests/test_packaging.py`) to confirm zero missing package data or broken imports after our 12 monolith modularizations.

## 3. Acceptance Gates
1. `python -m census doctor` exits `0` with `"ok": true` and never leaks secrets.
2. `examples/mcp/dual_mcp_config.json` parses as valid JSON.
3. `pytest -q tests/test_round187.py tests/test_packaging.py tests/test_mcp_profiles.py` passes with 0 failures.
4. `scripts/release_hygiene_check.py` exits `0` with zero AI-attribution strings in `README.md`.

## 4. Iteration Log
- *2026-11-27:* Plan drafted.
- *2026-11-27:* Implemented `doctor_report()` + `python -m census doctor --json`, created `examples/mcp/dual_mcp_config.json` and `docs/dual_mcp_quickstart.md`, refreshed `README.md` with Two-Layer Mermaid architecture and exact MCP profile tool counts (`full: 84`, `publication: 10`, `epidemiology: 25`, `core: 16`, `core_spatial: 17`, `review: 10`, `verification: 1`). Verified with `tests/test_round187.py`, `tests/test_packaging.py`, and `tests/test_mcp_profiles.py`.
