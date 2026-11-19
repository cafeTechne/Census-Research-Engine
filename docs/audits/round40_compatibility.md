# Round 40 compatibility and acceptance

Author self-review, not independent; implemented by the maintainer agent at the owner's request.
Worktree `/tmp/census-round40`, branch `phase40/beta-median`, based on defaultBranch `8d504c3`.

## Frozen validation (criterion `d5c9b02`, pushed before the full run; 1,000 draws per cell)

| Procedure | Coverage | Outcome |
| :--- | :--- | :--- |
| B1 beta, model SEs | .856–.895 | Failed |
| B2 beta, HC0 | .885–.903 | Passed, selected |
| B3 beta, HC0 + replicates | .950–.991 | Passed (over-wide) |
| Q1 median, kernel SE | .912–.917 | Passed, selected |
| Q2 median + replicates | .991–.993 | Passed (over-wide) |

## Engine

`census/regression_families.py` (`fit_beta`, `fit_median`), MCP `fit_model(model="beta"|"median")`,
recipe and rule text. Deferred to the backlog: PUMS ordinal/multinomial/weighted quantile models and
GEE (no survey weights in statsmodels' versions). No manifest change.

## Goldens and suite

See STATUS (Round 40).
