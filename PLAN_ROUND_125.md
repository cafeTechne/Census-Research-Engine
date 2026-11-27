# Plan — Round 125: N39 ACS 2021–2025 Five-Year Release Refresh & Annual Hygiene (`v0.120.0`)

**Goal:** Execute Backlog item **N39** when the U.S. Census Bureau publishes the ACS 2021–2025 5-year estimates (~December 2026) using the Round 117 turnkey preflight runbook (`scripts/acs_release_preflight.py`, `docs/audits/n39_preflight_checklist.md`), and complete annual release/plan housekeeping.

## Ground Rules
- Follow `docs/audits/n39_preflight_checklist.md` step by step; commit no synthetic or placeholder 2025 metadata.
- Live validation against Census-published 2021–2025 values must pass before declaring 2025 supported.
- Never print or commit `.env` or the Census API key; scan any release tarball before upload.
- Merges and releases require explicit owner approval.

## Deliverables
1. **ACS 2021–2025 metadata & concordance (`metadata/acs5/2025/`, `census/concordance.py`):**
   - Run `scripts/acs_release_preflight.py --year 2025` to verify API availability, archive 2025 variable/table metadata, and run the cross-vintage concordance audit (`2024 → 2025`), recording any breaking table/line changes in `docs/audits/concordance_2025.md`.
   - Update `census/errata.py` / `data/acs_errata.json` if Census publishes 2021–2025 errata.
2. **Price indexes & RPP refresh (`data/price_indexes/`, `data/price_parities/`):**
   - Refresh bundled R-CPI-U-RS, CPI-U, C-CPI-U (replacing provisional 2025 annual averages once BLS finalizes them) and BEA Regional Price Parities (`rpp`), regenerating SHA-256 sidecars and verifying via `census.inflation` / `census.rpp` tests.
3. **Live validation (`tests/test_validation_live.py`):**
   - Validate derived estimates and MOEs against Census-published 2021–2025 values and record the audit in `docs/audits/validation_2025.md`.
   - Verify Census VRE 2025 file availability and update `census/replicate.py` registry if needed.
4. **Annual release & plan housekeeping:**
   - Record the minted Zenodo DOI for `v0.115.0` (and any intervening releases) in `STATUS.md` and `ROADMAP_BACKLOG.md`.
   - Archive `PLAN_ROUND_103.md`–`PLAN_ROUND_119.md` (already preserved at tag `v0.115.0`) and update `scripts/release_hygiene_check.py` / `tests/test_round118.py` to check active plans cleanly instead of requiring archived plans in the root.
   - Close Backlog item **N39** in `ROADMAP_BACKLOG.md` and `STATUS.md`; add `docs/audits/round125_compatibility.md` and `tests/test_round125.py`; bump `0.120.0`.

## Fixed Acceptance Checks
- `scripts/acs_release_preflight.py --year 2025 --offline` passes against archived 2025 metadata.
- Full offline suite `OPENBLAS_NUM_THREADS=1 .venv/bin/python -m pytest -q` passes with 0 failures (plus live 2025 validation passing when run with Census API key).
- `scripts/run_golden.py` remains byte-identical.
- `scripts/release_hygiene_check.py` exits 0 (`"ok": true`).
