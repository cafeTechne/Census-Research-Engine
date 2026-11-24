# Plan — Round 117: N39 ACS 2021–2025 Release-Refresh Preflight & Turnkey Tooling (`v0.113.0`)

**Branch:** `phase103/agent-access-hygiene` (uncommitted per owner instruction)  
**Goal:** Prepare turnkey offline preflight & audit tooling for Backlog N39 (the upcoming ACS 2021–2025 5-year release and final 2025 BLS price-index refresh, due ~Dec 2026) so the refresh can be executed and verified in one audited pass when Census publishes the release.

## Deliverables
1. `scripts/acs_release_preflight.py`: offline-safe preflight script that inspects:
   - Bundled metadata archive coverage (`data/metadata/` or archive vintages) and reports missing target years (e.g. `2025`).
   - Bundled price-index and RPP CSV integrity checksums (`census.data_integrity`, provisional-year status for `2025`).
   - Existing crosswalk overrides & rules validity (`validate_crosswalks`).
   - Prints a structured JSON/markdown readiness report and exits cleanly with exact next commands (`scripts/fetch_metadata_archive.py`, `scripts/update_price_indexes.py`, `scripts/update_price_parities.py`).
2. `docs/audits/n39_preflight_checklist.md`: step-by-step release-refresh runbook for N39.
3. `tests/test_round117.py`: offline tests for `scripts/acs_release_preflight.py` (including JSON output schema and zero network calls).
4. Update `docs/audits/round117_compatibility.md`, `STATUS.md`, `CHANGELOG.md`, `ROADMAP_BACKLOG.md`, version `0.113.0`.
