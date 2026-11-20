# Round 56 compatibility and acceptance

Author self-review, not independent; implemented by the maintainer agent at the owner's request.
Worktree `/tmp/census-round56`, branch `phase56/pums-inequality`, based on defaultBranch `0b093ec`.

## Frozen validation (criterion `d91201b`, pushed with the targets before the full run; 2,000 draws per cell, 8 cells)

| Measure | Lowest / highest cell over the incomes judged | Validated |
| :--- | :--- | :--- |
| Gini (I1, I2, I3) | .861 / .908 | yes |
| log P90/P10 (I1, I2) | .888 / .923 | yes |
| log P80/P20 (I1, I2) | .900 / .914 | yes |
| Gini difference A = 2 vs A = 0 (I1) | .873 / .899 | yes |
| Theil T (I1, I2) | .811 / .904 | no (I1 .857, I2 .811) |
| Atkinson .5 (I1, I2) | .845 / .898 | no (I2 .845) |
| Atkinson 1 (I1, I2) | .858 / .902 | no (I2 .858) |
| Top-decile share (I1, I2, I3) | .850 / .906 | no (I1 .858, I2 .850; I3 passed) |

No failed draws; absolute bias at most .0041. The plan's description of the zero share in I3 ("one in seven") was
corrected to 30% in the plan before freezing; the criterion records it.

## Engine

- `census/pums_inequality_core.py` (new, frozen): weighted measures for all 81 weight columns after one sort.
- `census/pums_inequality.py` (new): `pums_inequality(df, var, weight, where, by)` with `VALIDATED`,
  `GINI_DIFFERENCE_VALIDATED`; zero incomes kept for the Gini and top share, excluded from Theil, Atkinson and the
  ratios; negative incomes refused; heaped quantiles (more than 2% of the weight at a quantile used) flagged as
  exploratory, as Round 32 does for medians.
- MCP `test_association(kind="inequality", var=..., by=...)`: no new tool; tool counts unchanged.
- Rule text mirrored: `docs/agent_protocol.md`, `mcp_server.py`, MCP core item 10 and the `test_association`
  description, `docs/recipes/pums_tests.md`.

## Acceptance

- Schema and run goldens: byte-identical to the Round 50–55 snapshots.
- New tests: `tests/test_round56.py` (6).
- Full suite: 2100 passed, 37 skipped; 0 failures.
