# Round 97 spatial block cross-validation and MAUP sensitivity: pre-set criterion

Frozen with `scripts/model_assessment_validation.py`, `census/model_assessment_core.py`, the Round 93 geometry
script and `docs/audits/mi_tract_geometry.json` before the full run (tag `criterion-r97`). Author self-review, not
independent.

## Design

| Part | Specification |
| :--- | :--- |
| Training region A | Wayne County tracts (625) |
| New region B | Oakland and Macomb tracts (593) |
| Coordinates | km, from the Round 93 representative points |
| Covariate | x = Gaussian field (exponential covariance, 10 km range) + N(0, 0.5), standardized |
| Outcome | y = 1 + 0.5x + e + N(0, 0.5²), where e is a Gaussian field over A ∪ B with variance 1 and exponential range r ∈ {0 (independent), 20, 50} km |
| Model | `ols_knn`: OLS plus the mean residual of the 5 nearest training areas; predictive SD from leave-one-out within training |
| Cells and draws | 3 cells (r); 500 draws per cell; seed [20282971, cell, draw] |

## Target and estimates

- **Truth:** the model fitted on all of A and scored on B (RMSE and 90% coverage).
- **Estimates from A alone:**
  - V1: spatial block CV with k = 5 k-means blocks;
  - V1-10: the same with 10 blocks (reported);
  - V0: random 10-fold CV (reported).

## Acceptance (V1)

In every cell, the mean V1 RMSE across draws is within ±10% of the mean true RMSE, and the mean V1 coverage is
within ±.03 of the mean true coverage.

## S1: MAUP sensitivity (reported, no pass rule)

- Covariates and noise as above, region A only, 200 draws per range.
- For each draw: the tract-level weighted slope of y on x (unit weights), then the zone-level slope over 20 random
  contiguous zonings of about 10 tracts.
- Reported: the mean and SD across zonings of the ratio zone slope / tract slope.
