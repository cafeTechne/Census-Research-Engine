# Round 94 compatibility and acceptance

Author self-review, not independent. Worktree `/tmp/census-round94`, branch `phase94/inequality-monitoring`. The
criterion commit (tag `criterion-r94`) is an ancestor of the branch. Version 0.90.0.

## Behaviour changes

- **`disparity_measures`** gains `who_measures` and `compare_years`. `reference="best"` is accepted only with them.
  Calls without the options are unchanged.
- **New modules** `census/inequality_monitoring.py` and the frozen core `census/inequality_monitoring_core.py`.
- **No new tool.** Manifests are unchanged, so goldens are expected byte-identical.

## Exceptions

1. **The plan's example could not be run as written.** It asked for uninsured rates by race across two releases, but
   the 2015–2019 VRE files have no race-iterated tables. The example uses family poverty by race for 2020–2024 and
   age-group poverty (B17001) for the change between releases.
2. **The validated change between releases covers group CVs up to .30.** The trend cells were run at c ≤ .30 only,
   as pre-set.
3. **Count-based (WONDER) group rates are not supported by `who_measures`.** The validation used ACS replicates
   only.
