# Round 58 exploratory example: OH/PA county child poverty with SCPC spatial intervals

**Status: exploratory example, not a registered study. Author self-review, not independent.**

**Inputs.** `scripts/r58_scpc_example.py` uses Round 54's frame: cached 2024 county B17001, B19013 and B23025 for
Ohio and Pennsylvania, 155 counties, ACS only. Coordinates are Round 44's OH/PA representative points. Outputs
are archived at `/tmp/r58_example_outputs.tar.gz` (sha256 `84ea7afe…a6d5d4be`).

**Model.** OLS of the county child poverty rate (percent) on log median income and the unemployment rate
(percent). The target is the slope on the estimates as observed. Round 54 showed IM-8 is not validated on OH/PA;
SCPC is (Round 58).

## Results (90% intervals)

| Method | Log income | Unemployment (per point) | Validated on OH/PA |
| :--- | :--- | :--- | :--- |
| SCPC, ρ̄ .05 (q 5) | −19.2 (−22.0 to −16.5) | 1.23 (0.26 to 2.21) | yes |
| SCPC, ρ̄ .10 (q 4) | −19.2 (−22.2 to −16.3) | 1.23 (0.06 to 2.41) | yes |
| IM-8 (Round 54) | −18.6 (−21.4 to −15.8) | 1.22 (0.47 to 1.97) | no |
| OLS HC3 with a PA term (Round 54) | −18.5 (−21.6 to −15.5) | 1.41 (0.82 to 1.99) | ignores spatial dependence |

## Findings

- The validated SCPC interval for unemployment is about 60% wider than HC3's and still excludes zero. Round
  54's question (does the unemployment association survive spatial dependence on OH/PA?) now has a validated
  answer: yes, at the 90% level.
- SCPC's point estimate is the full-sample OLS slope (without a PA term). IM-8 averages within-state cluster slopes,
  in which the state term is absorbed. The estimates differ slightly for that reason.
- The more conservative benchmark (ρ̄ .10) widens the interval further; ρ̄ .05 is the validated default for OLS.

## Limits

Cross-sectional and descriptive; the slopes are attenuated by sampling error in income and unemployment (use
the corrected-slope estimators for error-free slopes).
