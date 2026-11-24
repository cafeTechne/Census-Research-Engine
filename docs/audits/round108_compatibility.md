# Round 108 Compatibility Audit (`v0.104.0`)

- **Manifest execution golden (`scripts/run_golden.py`):** byte-identical to pre-Round-103 baseline (`/tmp/r103_run_before.json`).
- **Manifest method registry (`census/manifest/methods.py`):** 18 → **20 methods** (added `designation` and `agreement`). Schema golden differs only in supported-method/statistic messages; existing manifests are unaffected.
- **Backward compatibility of library defaults:**
  - `census.msm.marginal_structural_model(..., method="gformula")`: now supports any `p >= 1` time-varying confounders (exact same `p = 1` path as Round 106; vector VAR(1) path for `p >= 2`).
  - `census.spatial_models.diversity_index(...)`: `method="default"` is unchanged; opt-in `method="sdr_bc"` with `sample_sizes` applies Round 108's validated `n >= 150` gate.
- **No new MCP tools (81 total; 16 `core`, 17 `core_spatial`) and no new dependencies.**
