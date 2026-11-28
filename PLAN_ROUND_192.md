# Plan — Round 192: Enhanced `doctor --verbose`, Routing `R89–R91` & `v0.188.0` Hygiene Sync (`v0.188.0`)

## 1. Strategic Objective
Extend `python -m census doctor` with `--verbose` diagnostics (N39 ACS 2021–2025 readiness check, bundled crosswalk validation, and read-only SSD corpus presence check without importing Layer B), expand `docs/agent_routing.md` with `R89–R91` (91 rows total), extend `scripts/release_hygiene_check.py` through Round 192, and sync version `0.188.0`.

## 2. Exact File Contracts
1. `census/workflows_reporting.py` & `census/__main__.py`:
   - Add `verbose: bool = False` to `doctor_report()` and `--verbose` flag to `python -m census doctor`.
   - When `verbose=True`, include `crosswalks_valid`, `acs_2025_archived` (boolean check for `metadata/acs5/2025`), and `ssd_corpus_mounted` (read-only path check, zero Layer B imports).
2. `docs/agent_routing.md`: Append `R89–R91` (91 rows total).
3. `scripts/release_hygiene_check.py`: Extend audit check through Round 192 (`range(126, 193)`).
4. Version sync `0.188.0`: `census/__init__.py`, `census/pipeline.py`, `CITATION.cff`, `CHANGELOG.md`, `STATUS.md`.
5. `tests/test_round192.py` & `docs/audits/round192_compatibility.md`.

## 3. Acceptance Gates
1. `python -m census doctor --verbose --json` exits `0` with `"ok": true`.
2. `scripts/release_hygiene_check.py` exits `0` with `"ok": true`, `"version": "0.188.0"`.
3. `pytest -q tests/test_round185.py tests/test_round186.py tests/test_round187.py tests/test_round188.py tests/test_round189.py tests/test_round190.py tests/test_round191.py tests/test_round192.py tests/test_agent_routing.py layer_b_openscholar/tests/` passes with 0 failures.

## 4. Iteration Log
- *2026-11-27:* Plan drafted after `v0.185.0` local commit & tag.
- *2026-11-27:* Added `doctor --verbose` diagnostics, expanded `docs/agent_routing.md` (`R89–R91`, 91 rows), extended `scripts/release_hygiene_check.py` through Round 192, synced version `0.188.0`, and verified all Round 185–192 + routing + Layer B tests.
