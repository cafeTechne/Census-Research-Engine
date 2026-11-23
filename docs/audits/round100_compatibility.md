# Round 100 compatibility and acceptance

Author self-review, not independent. Worktree `/tmp/census-round100`, branch `phase100/mice`. The criterion commit
(tag `criterion-r100`) is an ancestor of the branch. Version 0.96.0.

## Behaviour changes

- **`fit_model`** gains `impute_method` and `impute_delta_variable` and `impute_delta_shifts`. The new FCS route is used when either is given, when
  more than two variables are listed, or when the outcome is listed. Earlier calls (one or two covariates, no
  method) keep the Round 42/47 routines unchanged.
- **New modules** `census/mice.py` and the frozen core `census/mice_core.py`.
- **No new tool.** Manifests are unchanged, so goldens are expected byte-identical.

## Exceptions

1. **Passive imputation is in the core (`mice_core.mice(passive=...)`) but not exposed through `fit_model`.** Derived
   variables in formulas (e.g. `np.log(x)`) are refused by the FCS route; create the column first.
2. **Pooling on transformed scales** (Fisher z for correlations, log for ratios) is left to the callers that compute
   those quantities. `impute_fcs` pools OLS coefficients.

## Acceptance

- Goldens: run and schema snapshots byte-identical to Round 99.
- Full suite: 2384 passed, 42 skipped, 13 warnings, 72 subtests; 0 failures.
