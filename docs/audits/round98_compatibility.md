# Round 98 compatibility and acceptance

Author self-review, not independent. Worktree `/tmp/census-round98`, branch `phase98/rdd`. The criterion commit
(tag `criterion-r98`) is an ancestor of the branch. Version 0.94.0.

## Behaviour changes

- **New full-profile MCP tool `regression_discontinuity`** (79 → 80 tools). README, STATUS, the CLI tool list and
  sources are updated.
- **New modules** `census/rdd.py` and the frozen core `census/rdd_core.py`.
- **Manifests are unchanged,** so goldens are expected byte-identical.

## Exceptions

1. **The engine floors the bandwidth for discrete running variables at 4.** The validation script floored it at 3,
   but every validation fit had an IK bandwidth ≥ 4 (no failures). In the example, IK chose 2 years for Medicare,
   which would leave only two support points below the cutoff for the local quadratic.
2. **The density test jitters ages uniformly within each year when the running variable is discrete.** The validation
   ran the test on continuous data only, and the test is exploratory anyway.
3. **Clustering by running-variable value is not offered.** It failed validation badly.

## Acceptance

- Goldens: run and schema snapshots byte-identical to Round 97.
- Full suite: 2373 passed, 42 skipped, 13 warnings, 72 subtests; 0 failures.
