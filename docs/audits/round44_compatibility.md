# Round 44 compatibility and acceptance

Author self-review, not independent; implemented by the maintainer agent at the owner's request.
Worktree `/tmp/census-round44`, branch `phase44/posthoc-replication`, based on defaultBranch `1f2fd1e`.

## Frozen designs (criterion `09ecd91`, pushed before either run)

| Check | Result |
| :--- | :--- |
| B. C1 (IM-8, observed target) on OH/PA, 12 cells | **Failed**: independent cells .8945–.9090; spatially correlated cells .7020–.8600 |
| B. G1 / G2 (corrected slopes) on OH/PA, 8 cells | **Passed**: G1 .8670–.9090; G2 .8630–.9210 |
| A. R29 H1–H3 under NB2-HC3 (MI/NY, OH/PA) | All hold (pre-set reading "holds") |
| A. R29 H2 interval-censored (exploratory) | Slope as complete case; no hidden value output; WONDER audit passed |

## Exception

The first Round 29 post hoc run stopped before writing any output: the NB2 alpha optimizer (BFGS) did not
converge on OH/PA premature deaths. Fix in `census/count_models.py` (Nelder–Mead fallback, same estimator;
equal to the frozen core whenever BFGS converges; tested). The run was then repeated with the unchanged
script. `census/manova_counts_core.py` (frozen in Round 39) is not modified.

## Engine

`census.spatial_clusters.geography_notes` (IM-8 outside MI/NY; clusters crossing state borders), used by
`fit_replicate` IM fits and `fit_spatial_eiv` G1; spatial EIV docstring records the replication; rule text
mirrored; recipe `external_health_outcome`.

## Goldens and suite

See STATUS (Round 44).
