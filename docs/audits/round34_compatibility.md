# Round 34 compatibility and acceptance

Author self-review, not independent; implemented by the maintainer agent at the owner's request.
Worktree `/tmp/census-round34`, branch `phase34/ranking`, based on defaultBranch `1fc60a7`.

## Frozen validation

`census/ranking_core.py`, the script and criterion were committed and pushed at `6286ad9` before the
full run (one smoke run, 10 draws per cell, no files); 2,000 draws in each of 8 cells.

| Procedure | Result |
| :--- | :--- |
| R1 individual rank intervals | Passed: mean per-area coverage ≥ .9994, minimum ≥ .9965 |
| R2 joint rank intervals | Passed: joint coverage ≥ .9985 |
| R3 bootstrap percentile ranks | Failed: mean .70–.89, minimum area .33–.77 (not exposed) |
| V1 Holm versus reference | Passed: FWER .079–.102 |
| V2 simultaneous versus reference | Passed: FWER .082–.109; joint coverage .894–.907 |

## Engine

`census/ranking.py` (API), MCP tool `rank_areas` (full profile only; core unchanged at 16), recipe
`rank_areas`, mirrored rule text. With replicates the reference comparison uses the replicate
covariance of (area − weighted mean) with fixed weights; the validation used the exact formula for
independent errors, which the replicate covariance estimates. No manifest change.

## Goldens and suite

Both goldens byte-identical to v0.30.0. Suite: 1935 passed, 37 skipped, 59 subtests; 0 failures
(baseline 1930; 5 new tests).
