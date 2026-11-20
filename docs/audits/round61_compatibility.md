# Round 61 compatibility and acceptance

Author self-review, not independent; implemented by the maintainer agent at the owner's request.
Worktree `/tmp/census-round61`, branch `phase61/manifest-spatial`, based on defaultBranch `d54cc2a`. No new
statistics, so there is no simulation and no criterion.

## Changes

- `census/scpc_core.py`: `setup` keeps the grid covariances (`V`). New `p_value` gives the worst case over the
  benchmark grid of P(|τ| > |t|), from the same Imhof formula. At the critical value it equals α (.10, tested), so it
  agrees with the interval. `census/scpc.py` reports `p_value`.
- Manifests (`census/manifest/methods.py`):
  - `fit_replicate` `args.spatial_scpc` (`{}` or `{rho_bar}`).
    - Checks: model OLS, Poisson (`exposure`) or binomial (`trials`; refused unless exploratory); only validated
      ρ̄ values (.05/.10 for OLS, .10 for Poisson); no weights, `scale`, `spatial_se` or `spatial_clusters`;
      population target only.
    - External count outcomes do not need `scale: robust` with SCPC.
    - Hypotheses on a non-validated SCPC result are refused.
  - `regression_calibration` `args.spatial: "clusters"`: `model` poisson/negbin with `exposure`, or binomial with
    `trials` (new `_check_regression_calibration`). Results come from `fit_count_model(calibrate=...)` and
    `regression_calibration_clusters`.
  - `correlation_matrix` `args.spatial: true`, with `interval: "validated"` only. Effective-n intervals use the
    run's coordinates, or the GEOIDs' representative points when the run has none.
  - Method text for each option.
- Rule text mirrored: `docs/agent_protocol.md`, `mcp_server.py`, MCP core item 10,
  `docs/recipes/regression_sampling_error.md`, `docs/recipes/rank_methods.md`.

## Compatibility

Registered manifests do not use the new arguments, so their validation, outputs and method text are unchanged.

## Acceptance

- Schema and run goldens: byte-identical.
- New tests: `tests/test_round61.py` (6).
- Full suite: 2127 passed, 37 skipped; 0 failures.
