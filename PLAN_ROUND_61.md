# Round 61 plan: manifest routing for spatial methods (no new statistics)

**Goal.** Backlog issue N37 (`ROADMAP_BACKLOG.md` Round 61).

Several validated methods are reachable from the library and MCP but not from registered manifests:
- SCPC naive slopes (Round 58);
- calibrated IM-8 slopes for Poisson/NB2 (Round 53) and binomial (Round 58);
- effective-n correlation intervals (Rounds 48 and 59).

Confirmatory studies go through manifests, so these methods cannot yet back a registered hypothesis. This round
routes them as opt-in arguments, as Round 43 did for earlier methods. No new statistics, so there is no
simulation. Registered manifests keep their bytes and outputs: both goldens stay byte-identical.

Version 0.58.0. Baseline: v0.57.0 (2121 passed, 37 skipped). Branch `phase61/manifest-spatial`.

## 1. Changes

- **SCPC p-value.** `census/scpc_core.py` keeps the grid covariances in `setup`. New `p_value(theta, e, S)` gives the
  worst case over the grid of P(|τ| > |t|), from the same Imhof formula as the critical value. It is consistent with
  the interval: p < α exactly when the interval excludes zero. `fit_scpc` reports it.
- **`fit_replicate` `args.spatial_scpc: {"rho_bar": number}`** (or `{}` for the validated default).
  - Models: OLS and Poisson (exposure) are validated; binomial is exploratory and refused in confirmatory manifests.
  - Target population only. No weights, `scale`, `spatial_se` or `spatial_clusters`.
  - External count outcomes are allowed: the influence values are robust, so the "set scale robust" requirement
    does not apply.
  - Results become a `ModelResult` with SCPC intervals and p-values.
- **`regression_calibration` `args.spatial: "clusters"`.**
  - With `model` `poisson` or `negbin` and `exposure`: `fit_count_model(..., spatial="clusters", calibrate=...)`.
  - With `model` `binomial` and `trials`: `regression_calibration_clusters`.
  - Population target, 90% level.
- **`correlation_matrix` `args.spatial: true`** with `interval: "validated"`: effective-n intervals
  (`validated_correlations(coords=...)`), for Spearman, Kendall, Pearson and partial with replicates.
- **Shared steps:**
  - method text describes each option;
  - validation messages for invalid combinations;
  - rule text in the agent protocol, the recipes and the MCP text.
- STATUS, CHANGELOG, version, compatibility audit. Tests run each option through `validate_manifest` and the method
  runners on synthetic frames. Goldens identical.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| SCPC p-value | | |
| Manifest options and checks | | |
| Rule text, tests | | |
| Goldens, final suite | | |
| Exceptions | | |
