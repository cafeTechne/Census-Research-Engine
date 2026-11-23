# Round 97 compatibility and acceptance

Author self-review, not independent. Worktree `/tmp/census-round97`, branch `phase97/cv-maup` (Round 96 merged in).
The criterion commit (tag `criterion-r97`) is an ancestor of the branch. Version 0.93.0.

## Behaviour changes

- **`spatial_model`** gains `kind="cv"` and `kind="maup"`.
- **New modules** `census/model_assessment.py` and the frozen core `census/model_assessment_core.py`.
- **No new tool.** Manifests are unchanged, so goldens are expected byte-identical.

## Exceptions

1. **The plan's `assess="spatial_cv"` option on `fit_model`, `small_area_estimates` and disease mapping was not
   added.** Cross-validation is a `spatial_model` kind for OLS-type models. Extending it to the other models would
   need their own fit/predict functions, and block CV failed validation anyway.
2. **The validated model is OLS with neighbour residual smoothing** (the case where random CV leaks information).
   Plain OLS is reported beside it.
3. **MAUP is descriptive, with tract-level zonings only.** Block-group and county scales are a recipe walkthrough,
   not a tool option.

## Acceptance

- Goldens: run and schema snapshots byte-identical to Round 96.
- Full suite: 2368 passed, 42 skipped, 13 warnings, 72 subtests; 0 failures.
