# Replication E: tract, county and state shares of US life-expectancy variation

**Status: registered headline replication (criterion `110c22e`). Author self-review, not independent.** Audit:
`docs/audits/r68_le_variance_replication.md`.

## Target

Boing, Boing, Cordes, Kim and Subramanian (2020), "Quantifying and explaining variation in life expectancy at
census tract, county, and state levels in the United States", *PNAS* 117(30):17688–17694. The paper is not open
access, so only its published headline is used: of the geographic variation in life expectancy at birth, 70.4%
lies between tracts, 10.7% between counties and 19.0% between states (65,662 tracts, 3,020 counties, 48 states
plus DC).

## Result: replicated

| Level | Published | Ours |
| :--- | ---: | ---: |
| Tract (within county) | 70.4% | 70.0% |
| County (within state) | 10.7% | 10.6% |
| State | 19.0% | 19.4% |

- **Data:** USALEEP 2010–2015, every tract with an estimate, including fully predicted tracts. Its counts match the
  paper exactly (65,662 tracts, 3,020 counties, 48 states plus DC).
- **Model:** a three-level REML random-intercept null model of life expectancy in years, fitted with statsmodels.
- **Log scale:** ln(e0) gives the same split (70.0 / 10.7 / 19.3).

## Assumptions and limits

- The paper's methods section was not read. The data source and the null-model form are inferred from the
  matching counts and the published description. The exact agreement in counts and the near-exact shares support
  both inferences.
- Only the variance decomposition is replicated; the paper's covariate models are not.
- The engine's `multilevel_model` is two-level only, so this used statsmodels directly (backlog N46). No engine
  interval is involved, so there was no coverage simulation.

## What this establishes

The engine's USALEEP handling reproduces a nationally cited result on the full national tract geometry: most
geographic inequality in US life expectancy lies between neighbourhoods within the same county.
