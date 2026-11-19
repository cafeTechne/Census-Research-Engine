# Round 41 compatibility and acceptance

Author self-review, not independent; implemented by the maintainer agent at the owner's request.
Worktree `/tmp/census-round41`, branch `phase41/causal`, based on defaultBranch `ef0bb90`.

## Frozen validation (criterion `b7464e5`, pushed before the full run; 2,000 draws per cell)

| Procedure | Result |
| :--- | :--- |
| T1–T3 treatment effects (exact / 0.9 confounders) | Passed (.894–.899) |
| T1–T3 at confounder reliability 0.7 | .886–.890, but the design's residual confounding cancels (limitation recorded in the audit) |
| I1 2SLS with a second measurement | Passed in all four cells (.882–.907); naive OLS .30–.82 |
| S1/S2 mediation, exact mediator | Passed (.876 / .891) |
| S1/S2 with mediator reliability 0.8 | .69–.72 (exploratory) |

## Engine

`census/causal.py` (`estimate_effect`, `iv_slope`, `mediation`), MCP tool `estimate_effect` (full
profile; the seventh roadmap tool), recipe `causal`, mirrored rule text. No real-data example (causal
claims need a registered design); the recipe carries a synthetic one. No manifest change.

## Goldens and suite

Both goldens byte-identical to v0.37.0. Suite: 1972 passed, 37 skipped, 63 subtests; 0 failures
(baseline 1967; 5 new tests).
