# Round 102 compatibility and acceptance

Author self-review, not independent. Worktree `/tmp/census-round102`, branch `phase102/meta-analysis`. The criterion
commit (tag `criterion-r102`) is an ancestor of the branch. Version 0.98.0.

## Behaviour changes

- **`combine_estimates("pool")`** results gain `heterogeneity.tau2_interval` and a prediction-interval note. The
  new options are `moderators`, `leave_one_out` and `small_study_test`.
- **New core** `census/meta_core.py`.
- **No new tool.** Manifests are unchanged, so goldens are expected byte-identical.

## Exceptions

1. **The plan's `tau2="reml"` tool option was not exposed.** The core has REML. Its prediction intervals failed
   alongside Paule–Mandel's, so pooling keeps the validated Paule–Mandel + Hartung–Knapp route.
2. **The plan's example (pooling four states' poverty–mortality associations) has too few estimates** for
   meta-regression or the Egger test. The example pools 12 states' county-level uninsurance–poverty slopes instead.
3. **The engine uses 999 permutations for meta-regression;** validation used 199. The permutation p-value's size
   held at 199, and more permutations only reduce Monte Carlo error.
