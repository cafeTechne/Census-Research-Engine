# Round 37 compatibility and acceptance

Author self-review, not independent; implemented by the maintainer agent at the owner's request.
Worktree `/tmp/census-round37`, branch `phase37/agreement`, based on defaultBranch `6273b9e`.

## Frozen validation

Procedures, script, criterion and targets committed and pushed at `e6d4be6` before the full run. One
pre-freeze design change after the first smoke run: the sources' genuine disagreement δ (SD 0.5) was
added, because with δ = 0 the error-free limits have near-zero width (unrealistic for two sources).

| Procedure | Independent cells | Outcome |
| :--- | :--- | :--- |
| B0 bias | .894–.900 | Passed |
| B1 observed limits of agreement | .838–.892 | Failed |
| B2 error-free limits | .841–.904 | Failed |
| C1 Lin's CCC | .859–.887 | Failed (narrowly) |
| C2 error-corrected CCC | .382–.775 | Failed |
| K1 kappa of quintiles | .883–.912 | Passed |

## Engine

`census/agreement.py` (`check_agreement`), MCP tool `check_agreement` (full profile), recipe
`agreement`, mirrored rule text. Failed procedures are reported with `validated: false`. No manifest change.

## Goldens and suite

Both goldens byte-identical to v0.33.0. Suite: 1951 passed, 37 skipped, 61 subtests; 0 failures
(baseline 1946; 5 new tests).
