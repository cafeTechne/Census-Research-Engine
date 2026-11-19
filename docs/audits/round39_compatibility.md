# Round 39 compatibility and acceptance

Author self-review, not independent; implemented by the maintainer agent at the owner's request.
Worktree `/tmp/census-round39`, branch `phase39/manova-counts`, based on defaultBranch `394daf3`.

## Frozen validation

Procedures, script, criterion and targets committed and pushed at `0686bc0` before the full run.
Pre-freeze changes (recorded in the criterion): the ANCOVA covariate's error scaling fixed; the ZIP
optimiser set to Newton and ZIP judged only at median expected count 10, after statsmodels' ZIP
returned NaN SEs at median 100 (an earlier WIP commit, `0ec608f`, preceded the freeze).

| Procedure | Result |
| :--- | :--- |
| V1 multivariate wild score bootstrap | Passed: size .090–.101 |
| V0 Pillai (iid) | .090–.096 (comparison) |
| N0 Poisson HC3 | Failed: .808–.867 (strong overdispersion) |
| N1 NB2 HC3 | Passed: .885–.901 in all 8 cells |
| N2 zero-inflated Poisson | Failed: .78–.84 at median 10; numerical failures at 100 |

## Engine

`census/count_models.py` (`fit_count_model`, `compare_groups_multivariate`); MCP `compare_groups(outcomes=...)`
and `fit_model(model="negbin", method="replicate")` now use the validated NB2-HC3 path (the earlier
`fit_replicate` negbin SEs are no longer used by that MCP call); recipes and rule text updated. No
manifest change.

## Goldens and suite

See STATUS (Round 39).
