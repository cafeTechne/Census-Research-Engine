# Round 35 compatibility and acceptance

Author self-review, not independent; implemented by the maintainer agent at the owner's request.
Worktree `/tmp/census-round35`, branch `phase35/spatial-eiv`, based on defaultBranch `fa9be75`.

## Frozen validation

`census/spatial_eiv_core.py`, the script and criterion were committed and pushed at `46fab40` before
the full run (one smoke run, 10 draws per cell, no files); 2,000 draws in each of 8 cells.

| Candidate | Coverage of the true slope | Outcome |
| :--- | :--- | :--- |
| G1 pooled-correction IM-8 | .879–.899 | Passed |
| G2 SAR-whitened Fuller | .863–.918 (2 failed fits in 16,000) | Passed |
| C1 naive IM-8 (informational) | .580–.900 | (naive target; not a true-slope procedure) |

## Engine

New `census/spatial_eiv.py` (`fit_spatial_eiv`), MCP `fit_model(method="eiv", spatial=...)`, rule
text mirrored, recipe note. **Deviation from the plan:** manifests are unchanged; `fit_eiv` with
`spatial_clusters` stays refused there (changing manifest routing would change registered-manifest
validation snapshots). Manifest routing is backlog. Post hoc R21b re-check:
`docs/studies/r35_posthoc_spatial_eiv.md`.

## Goldens and suite

Both goldens byte-identical to v0.31.0. Suite: 1940 passed, 37 skipped, 59 subtests; 0 failures
(baseline 1935; 5 new tests).
