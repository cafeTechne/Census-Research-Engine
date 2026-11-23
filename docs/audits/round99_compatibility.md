# Round 99 compatibility and acceptance

Author self-review, not independent. Worktree `/tmp/census-round99`, branch `phase99/matching-ddd`. The criterion
commit (tag `criterion-r99`) is an ancestor of the branch. Version 0.95.0.

## Behaviour changes

- **`estimate_effect`** gains `kind="matching"`.
- **`difference_in_differences`** gains `design="triple"`, `group` and `affected_group`. Other kinds and designs are
  unchanged.
- **No new tool.** Manifests are unchanged, so goldens are expected byte-identical.

## Exceptions

1. **Propensity-score matching with a bootstrap passed,** although the plan expected it to fail. It is marked valid
   for this design only, and the recipe still prefers nearest-neighbour matching.
2. **The plan's balance tables after matching** are given only before matching. CEM balance is exact on the coarsened
   strata by construction.
3. **The example's triple difference uses B27010** (stable lines 2010–2019) rather than S2701, whose rows change
   across years. Its 18–64 label in 2010–2012 against 19–64 later is noted in the example.

## Acceptance

- Goldens: run and schema snapshots byte-identical to Round 98.
- Full suite: 2378 passed, 42 skipped, 13 warnings, 72 subtests; 0 failures.
