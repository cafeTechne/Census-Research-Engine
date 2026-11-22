# Round 91 compatibility and acceptance

Author self-review, not independent. Worktree `/tmp/census-round91`, branch `phase91/msm`. The criterion commit (tag
`criterion-r91`) is an ancestor of the branch. Version 0.87.0.

## Behaviour changes

- **`difference_in_differences`** gains `design="msm"`, `time_varying_confounders` and `truncate_weights`.
  - Results without the new design are unchanged. No new tool.
  - Manifests are unchanged, so goldens are expected byte-identical.

## Exceptions

1. **The MSM failed its criterion and ships as exploratory.** It is still the only estimator here that is
   approximately right under treatment-confounder feedback. A later round could test a bias-corrected or
   studentized bootstrap with 51 units.
2. **The plan's design used BLS LAUS unemployment.** The example uses the ACS 1-year unemployment rate (DP03)
   instead: same concept, no new source or access terms.
3. **The outcome model has one indicator per treatment duration** (saturated) instead of a "4+" bucket. A pooled
   bucket would be misspecified and could leak bias into the reported years 1–3. Only years 1–3 are reported.

## Acceptance

- Goldens: run and schema snapshots byte-identical to Round 90.
- Full suite: 2329 passed, 42 skipped, 13 warnings, 72 subtests; 0 failures.
