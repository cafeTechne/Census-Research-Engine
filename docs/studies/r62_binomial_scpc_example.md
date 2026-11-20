# Round 62 exploratory example: OH/PA county child poverty as a binomial outcome with SCPC

**Status: exploratory example, not a registered study. Author self-review, not independent.**

**Inputs.** `scripts/r62_binomial_scpc_example.py` reads cached 2024 county B17001, B19013 and B23025 for Ohio and
Pennsylvania (155 counties, ACS only). Outputs are archived at `/tmp/r62_example_outputs.tar.gz` (sha256
`1fbd61a1…6c7a29ce`).

**Model.** The outcome is the share of children in poverty; the binomial trials are the children with poverty
status. Covariates are log median income and the unemployment rate. Intervals and p-values are SCPC: ρ̄ .15, the
binomial setting validated in Round 62. The OLS model of the percentage (SCPC ρ̄ .05, Round 58) is shown for
comparison.

## Results (90% intervals)

| Model | Log income | Unemployment (per point) |
| :--- | :--- | :--- |
| Binomial, log odds (SCPC ρ̄ .15) | −1.74 (−1.89 to −1.60) | 0.121 (0.075 to 0.168), p = .005 |
| OLS, percentage points (SCPC ρ̄ .05) | −19.2 (−22.0 to −16.5) | 1.23 (0.26 to 2.21), p = .051 |

## Findings

- With both models now validated for spatially dependent counties outside MI/NY, the unemployment association
  holds on OH/PA on the log-odds scale and in percentage points.
- The binomial model weights counties by their number of children, so large counties dominate it. The OLS model
  weights counties equally. They answer slightly different questions, so the scales and precision differ.

## Limits

Cross-sectional and descriptive; covariates carry ACS sampling error (attenuated slopes).
