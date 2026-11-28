# Plan — Round 208: Layer A `doctor --deep` Invariant Self-Check (`v0.204.0`)

## 1. Strategic Objective
Add `deep: bool = False` to `census/workflows_reporting.py:doctor_report()` and `--deep` to `python -m census doctor`, verifying critical engine invariants in < 1 second:
1. 1:1 parity between registered Layer A MCP tools (`mcp_server.mcp.list_tools()`) and `census.references.TOOL_SOURCES`.
2. 1:1 parity between `census.recipes.RECIPES` and `docs/recipes/<name>.md`.
3. Valid bundled `metadata/manifest.json` presence.
4. Bundled crosswalk validation + price-index/RPP SHA-256 integrity.

## 2. Exact File Contracts
1. `census/workflows_reporting.py`: Add `deep: bool = False` to `doctor_report()`.
2. `census/__main__.py`: Add `--deep` flag to `doctor` subcommand.
3. `tests/test_round208.py`, `docs/audits/round208_compatibility.md`, and `0.204.0` version/hygiene sync.

## 3. Iteration Log
- *2026-11-27 (Cron #3):* Plan drafted and implemented strictly inside the sandbox.
