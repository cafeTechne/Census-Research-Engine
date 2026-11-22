# Round 78 criterion: staggered-adoption DiD and synthetic control

Committed before the full run. Author self-review, not independent. Frozen with `validate_pins`:
- `scripts/policy_validation.py`;
- `census/policy_core.py` (new);
- this file.

**Seen before this commit:**
- one smoke run (4 draws per cell), which only checked that the script runs;
- noiseless checks: Callaway–Sant'Anna and Sun–Abraham recover constant and growing effects exactly (overall
  −2 and −2.133); synthetic control recovers a −2 effect with zero pre-period error.

## Methods (`census/policy_core.py`)

- **S1: Callaway–Sant'Anna.**
  - No covariates (outcome regression and doubly robust coincide). Never-treated controls, universal base period
    g − 1.
  - Aggregates: event-time effects, and an overall ATT (the cohort-size weighted mean of post-treatment cells).
  - Interval: Rademacher multiplier bootstrap over unit influence functions (B = 999), IQR-based SE, normal
    pointwise intervals and a sup-t uniform band.
- **S1r:** S1, with the ACS sampling variance of the linear estimator added in quadrature.
- **S2: Sun–Abraham.** Interaction-weighted event study with never-treated controls, a CR1 state-cluster
  covariance and t(N − 1) intervals.
- **C1: synthetic control.** Simplex weights fitted on pre-period outcomes. Inference is a placebo-in-space test of
  the post/pre RMSPE ratio. Pre-fit diagnostic: the treated pre-RMSPE over the median placebo pre-RMSPE.
- **C2: conformal per-period intervals** (Chernozhukov, Wüthrich and Zhu 2021), from cyclic-shift permutations of
  the T0 + 1 residuals and inversion over a grid.

## Designs (1,000 draws per cell)

- **Panel.**
  - 51 units; T = 12 or 18 annual periods.
  - Unit effects N(10, 3²), a common trend of .1 per period, and AR(1) errors with marginal SD 1 (ρ = .3 or .7).
  - ACS-like sampling error with a state CV that is log-uniform on [.01, .08].
  - **Deviation from the plan, made before any run:** the CVs come from this stated range, not from real 2010–2023
    1-year state files. The range covers typical state rates such as the uninsured rate.
- **Staggered design (8 cells).** Three cohorts of ten units (first treated in periods 5, 7, 9 or 7, 10, 13) and 21
  never-treated units. The effect is constant (−2) or growing (−1 − .5e).
- **Synthetic control (12 cells).**
  - One treated unit at the median level, with 50 never-treated donors.
  - Treatment at T − 3, so there are three post periods.
  - The effect is none, constant or growing.
- **Deviation from the plan, made before any run:**
  - S1 uses never-treated controls only (the not-yet-treated option is not run);
  - doubly robust covariates are not simulated, because no covariates enter the design.

## Pass rules

- **S1, S1r and S2** (judged separately): coverage ≥ .86 for the overall ATT and for every event time (e ≠ −1,
  pre-periods included) in every cell. Uniform-band coverage is reported.
- **C1:** placebo rejection rate at .10 ≤ .10 in every no-effect cell. Power is reported.
- **C2:** coverage ≥ .86 for every post period in every cell.
- **Pre-fit threshold:** a treated pre-RMSPE above twice the median placebo pre-RMSPE makes a synthetic-control
  result exploratory in the engine. The share of draws flagged is reported.

Seeds: `[20281801 + cell, draw]` for the staggered design; `[20281851 + cell, draw]` for synthetic control.

## Engine (only what passes)

- `difference_in_differences(design="staggered")` reports the passing staggered estimator.
- `synthetic_control` reports C1 and C2 if they pass. Results flagged for poor pre-fit are exploratory.
- **Refused:**
  - overlapping five-year releases;
  - 2020 ACS 1-year values.
