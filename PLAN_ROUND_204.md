# Plan — Round 204 (N135): Reusable `side_by_side_choropleth()` Engine Helper (`v0.200.0`)

## 1. Strategic Objective
Add `side_by_side_choropleth()` to `census/web_maps.py` so any study can render a self-contained, zero-CDN, CSP-locked dual-panel interactive HTML map comparing two area columns (e.g., raw SMR vs. BYM2 smoothed RR, or nominal vs. RPP-adjusted income) side-by-side.

## 2. Exact File Contracts
1. `census/web_maps.py`: Add `side_by_side_choropleth(gdf, left_col, right_col, out_path, ...)`.
2. `tests/test_round204.py` & `docs/audits/round204_compatibility.md`.

## 3. Iteration Log
- *2026-11-27:* Plan drafted and implemented from roadmap item `N135`.
