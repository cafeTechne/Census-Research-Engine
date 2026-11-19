# Round 38 compatibility and acceptance

Author self-review, not independent; implemented by the maintainer agent at the owner's request.
Worktree `/tmp/census-round38`, branch `phase38/evidence`, based on defaultBranch `a8aceaf`.

## Frozen validation (criterion `3edd5f4`, pushed before the full run)

| Procedure | Result |
| :--- | :--- |
| Fixed effect | Valid without heterogeneity (.884–.898); .44–.72 with it |
| DerSimonian–Laird | Failed with heterogeneity (.818–.841) |
| Paule–Mandel + HKSJ | Passed k = 2 and 4 (.885–.911); k = 8 with heterogeneity .855 (failed) |
| TOST | Size .046 and .000 at the margin (nominal .05) |
| z-test power | Within .008 of simulation |

## Engine

`census/evidence.py`, MCP tool `combine_estimates` (full profile), recipe `combine_estimates`, mirrored
rule text. No manifest change.

## Goldens and suite

Both goldens byte-identical to v0.34.0. Suite: 1957 passed, 37 skipped, 62 subtests; 0 failures
(baseline 1951; 6 new tests).
