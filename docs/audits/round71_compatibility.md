# Round 71 compatibility and acceptance

Author self-review, not independent. Worktree `/tmp/census-round71`, branch `phase71/tract-spatial`. Criterion
`f947f64`, committed before the full run and verified in git. The branch was rebased onto defaultBranch `09b2464`
(Round 72, merged first) before the docs were written. Version 0.68.0.

## Results (`tract_spatial_validation.md`)

- SCPC rho_bar .20, .30 and the distance-set benchmark pass every cell of both geometries. The spatial error ML
  interval and HC3 fail.
- **Tract default.** The pre-set rule picks the shortest average median length among the passing procedures:
  rho_bar .20 (mean median length 0.608, against 0.739 for .30 and 0.743 for the distance benchmark).

## Behaviour changes

- `fit_scpc` on tract GEOIDs:
  - the default rho_bar for OLS is .20 (was .05);
  - .20/.30 are validated there, and .05/.10 remain exploratory on tracts;
  - county defaults and flags are unchanged.
- `tests/test_round67.py::test_tract_level_scpc_is_exploratory` now passes rho_bar .05 explicitly. The test still
  checks Round 67's finding, and the tract default changed by design.
- Manifest `spatial_scpc` on a tract-level manifest accepts .20/.30 as confirmatory. Before this round every tract
  SCPC was exploratory, so no registered manifest is affected (none uses tract SCPC).
- `fit_model(method="replicate")` without `spatial` runs the residual check (`spatial_check="auto"`; cached boundary
  files only, never a download) and may add a note and `spatial_dependence`. Intervals are unchanged.
- `spatial_regression(model="error")` on tract GEOIDs adds an exploratory note.

## Plan deviations and exceptions

1. **No binomial cell** (recorded in the criterion before the run).
2. **No `spatial="sem"` route**, because T1 failed.
3. **No `"scpc_distance"` route.** T3 passed, but its intervals were longer than rho_bar .20's, so the pre-set
   default rule does not select it. It remains in the audit.
4. **No separate manifest `args.spatial_tract`.** The existing `spatial_scpc` now applies the tract benchmarks when
   the manifest's geography level is tract, which is the opt-in route the plan described.
5. **The warning is wired into `fit_model` only.** `fit_scpc` already reports a spatial interval. Manifests do not
   run the check, so the run golden is unchanged.

## Acceptance

- Goldens: byte-identical.
- New tests: `tests/test_round71.py` (9). `test_round58`, `test_round62` and `test_round67` were rerun: 23 passed.
- Example: `r71_tract_example.md`.
- Full suite: SUITE_LINE_71.
