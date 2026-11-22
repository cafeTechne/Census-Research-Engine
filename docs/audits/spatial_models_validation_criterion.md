# Round 93 GWR, classification, regionalization and diversity: pre-set criterion

Frozen with `scripts/spatial_models_validation.py` and `census/spatial_models_core.py` before the full run (tag
`criterion-r93`). Author self-review, not independent.

## Geometry

- **Tracts.** Wayne County, MI (625 tracts; 2020 representative points from `docs/audits/mi_tract_geometry.json`).
  Coordinates are projected to km around the county centre.
- **Neighbour graph.** Delaunay edges shorter than 5 km, standing in for contiguity.
- **Exposure.** x is a smooth spatial field (Gaussian process with a 5 km range, unit variance) plus iid noise with
  variance 0.5, then standardized.

## R1: geographically weighted regression

| Cell part | Values |
| :--- | :--- |
| Slope | Constant (β₁ = 1) or varying (β₁(u) = 1 + 0.5·standardized east coordinate) |
| Sampling error | "Low": SE_i ~ U(0.3, 1.0). "High": SE_i ~ U(0.6, 2.0) |

- **Outcome.** y = 1 + β₁(u)·x + N(0, 0.5²) + N(0, SE_i²).
- **Bandwidth** by AICc. Robust local 90% intervals.
- **Non-stationarity test:** 99 location permutations, bandwidth fixed.
- **Draws:** 4 cells × 500 draws; seed [20282931, cell, draw].
- **Pass** if, in every cell:
  - the mean local coverage of β₁(u_i) over areas and draws is ≥ .86;
  - at least 90% of areas have coverage ≥ .80;
  - in the constant-slope cells, the non-stationarity test rejects at .10 in ≤ .10 of draws.

  Power in the varying cells is reported.

## C1 and C2: classification and regionalization

These are reported only; there is no pass rule.

- **Groups.** 4 planted groups, with 3 features. Group centres sit 1.5 SD apart. Within-group noise is N(0, 1),
  plus ACS error with SE_i: low ~ U(0.2, 0.5), high ~ U(0.5, 1.0).
  - C1: groups are assigned at random to tracts (aspatial classes).
  - C2: groups are the 4 quadrants (east/west by north/south of the median), as contiguous regions.
- **Stability.** Each fit is repeated on 20 parametric replicate data sets (observed features + N(0, SE_i²)).
- **Reported:** the adjusted Rand index against the truth; mean stability; and calibration, i.e. the
  misclassification rate among areas with stability < .8 against those with stability ≥ .8.
- **Draws:** 4 cells × 200 draws; seed [20282932, cell, draw].

## D1: entropy diversity index

- **Shares.** 4 group shares per tract from Dirichlet(2, 1, 1, 0.5).
- **Observed shares:** Multinomial(n_eff, p)/n_eff with n_eff ∈ {50, 200}.
- **Replicates:** 80 SDR-like replicates, p̂ + (q_r − p̂)/2 with q_r ~ Multinomial(n_eff, p̂)/n_eff.
- **Estimators:** D1 is the plug-in entropy; D1bc is the bias-corrected one. Both have 90% replicate intervals for
  the true entropy.
- **Draws:** 2 cells × 1,000 draws; seed [20282933, cell, draw].
- **Pass** (each of D1 and D1bc), in both cells: mean coverage ≥ .86, and at least 90% of areas with coverage ≥ .80.

Failing families stay exploratory. Walker (2023) already recommends GWR only as exploration.
