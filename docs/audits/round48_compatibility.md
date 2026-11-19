# Round 48 compatibility and acceptance

Author self-review, not independent; implemented by the maintainer agent at the owner's request.
Worktree `/tmp/census-round48`, branch `phase48/small-samples-spatial`, based on defaultBranch `8954e9e`.

## Frozen validation (criterion `3fb07d3`, pushed before the full run; 2,000 draws per cell)

| Procedure | Coverage | Outcome |
| :--- | :--- | :--- |
| I0 Round 42 GLSAR | .5850–.8145 | comparison |
| I1 REML AR(1), t(n − 4) | .7915–.8800 | Failed at every n |
| I2 AR(1) bootstrap-t | .8460–.8955 | Passed at n = 30 only (.8830–.8955) |
| C1 effective-n, Spearman / Kendall / Pearson | .8750–.9165 / .8620–.9045 / .8640–.9665 | Passed |
| C2 IM-8, Spearman / Kendall / Pearson | .8585–.9080 / .8710–.9065 / .8475–.9115 | Kendall only |
| A3 effective-n Feldt α | .9120–.9255 | Passed |
| A4 IM-8 α | .7485–.9000 | Failed |
| H1 Paule–Mandel + Hartung–Knapp, k 5–10 | .8615–.8890 | Passed (Round 38 failed it at k = 8, τ² = mean s²) |
| H2 H1 truncated | .8740–.9175 | Passed |
| B1r / B2r moment-based limits | .8835–.8985 / .8895–.9355 | Passed (B2r: up to 39 undefined fits, counted as misses) |

**Deviation from the plan.** The plan called the effective-n estimator Dutilleul's. It is the
Clifford–Richardson–Hémon approximation that underlies Dutilleul's test (recorded in the criterion).

**Note on the truncated variant.** With Paule–Mandel, q is exactly 1 whenever τ̂² > 0. H2 therefore
differs from H1 only when τ̂² = 0, where it widens the interval. The engine uses H2 for 5–10 estimates
because plain HKSJ failed at k = 8 in Round 38.

## Engine

New frozen `census/small_spatial_core.py`; `census/small_spatial.py` holds the flags,
`frame_coordinates` and `distance_classes`.

| Function | Change |
| :--- | :--- |
| `interrupted_series` | New methods `bootstrap_t` (validated for n ≥ 30) and `reml` (exploratory) |
| `validated_correlations` | New `coords=` argument (effective n); partial stays exploratory |
| `build_index` | New `coords=` argument for the α interval |
| `combine_estimates` (`hksj`) | k ≤ 4 unchanged; k = 5–10 truncated and validated; k > 10 exploratory |
| `check_agreement` | Moment-based limits, now validated. The point limits are unchanged; only the intervals differ |
| MCP | `correlation_matrix(spatial=True)`, `build_index(spatial=True)` |

Rule text is mirrored in `agent_protocol.md`, the recipes and the MCP core instructions.

Two old tests asserted the previous flags and were updated: `test_round37` (limits now validated) and
`test_round38` (k = 5 is now validated). Manifests are unchanged; the new options are not routed.

## Goldens and suite

Both goldens byte-identical to Round 47 (`schema_r48`/`run_r48`). Suite: 2035 passed, 37 skipped, 63 subtests; 0 failures (8 new tests in `tests/test_round48.py`).
