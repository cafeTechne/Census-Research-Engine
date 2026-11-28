# Plan — Round 210: Modularize `census/workflows_geo.py` → `census/workflows_geo_helpers.py` (`v0.206.0`)

## 1. Strategic Objective
Extract shared geography boundary, spatial-weight, replicate-release, and figure-path helpers (`_LEVELS`, `_MAP_KINDS`, `_GEO_ERRORS`, `_release_replicates`, `_per_state`, `_fetch_boundaries`, `_with_boundaries`, `_weights_for`, `_paths`) from `census/workflows_geo.py` into `census/workflows_geo_helpers.py` with 100% re-export parity and zero monkeypatch regressions.

## 2. Exact File Contracts
1. `census/workflows_geo_helpers.py`: Extracted geography workflow helpers.
2. `census/workflows_geo.py`: Re-export all extracted helpers for 100% backward compatibility.
3. `tests/test_round210.py`, `docs/audits/round210_compatibility.md`, and `0.206.0` version/hygiene sync.

## 3. Iteration Log
- *2026-11-27 (Cron #5):* Plan drafted and implemented strictly inside the sandbox.
