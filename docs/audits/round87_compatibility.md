# Round 87 compatibility and acceptance

Author self-review, not independent. Worktree `/tmp/census-round87`, branch `phase87/ecologic`; defaultBranch
(Rounds 84–86) merged in, so the criterion commit (tag `criterion-r87`) stays an ancestor. Version 0.83.0.

## Behaviour changes

- `pums_regression` gains `ecologic_check` (adds an `ecologic` block; it fetches the PUMA column when needed).
  Without it nothing changes. No new tool (78); goldens expected byte-identical.
- `pums_tests` recipe section; protocol rule text.

## Exceptions

1. **Option, not a new tool**, as the plan allowed (the parameters fit `pums_regression`).
2. **The within-area slope** covered in every cell, but the criterion judged the C1 family as a whole, so the
   identity-scale within slope is also labelled exploratory. A later round could validate an area-size gate (records
   per area) for the identity-scale decomposition.
3. **Ecologic slope with no covariates equals the between slope** (a known identity); the gap then equals the
   contextual effect.
