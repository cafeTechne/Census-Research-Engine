# Round 42 compatibility and acceptance

Author self-review, not independent; implemented by the maintainer agent at the owner's request.
Worktree `/tmp/census-round42`, branch `phase42/missing-censored-its`, based on defaultBranch `a5cc7c4`.

## Frozen validation (criterion `5f81de2`, pushed before the full run; 2,000 draws per cell)

Pre-freeze changes (in the criterion): MICE implemented directly as proper Bayesian regression imputation
(one incomplete variable); missingness moved from x to the observed outcome.

| Procedure | Coverage | Outcome |
| :--- | :--- | :--- |
| D0 complete case | .871–.913 | comparison |
| D1 multiple imputation | .907–.919 | Passed |
| C0 complete-case Poisson | .824–.828 | comparison |
| C1 interval-censored Poisson | .839–.856 | Failed (narrowly) |
| A0 / A1 / A2 interrupted series (20 points) | .47–.81 | All failed |

## Engine

`census/mci_core.py` (frozen), `census/missing_censored_its.py`; MCP `fit_model(impute=...)`;
exploratory library functions for censored counts and interrupted series; recipes and rule text. No
manifest change.

## Goldens and suite

See STATUS (Round 42).
