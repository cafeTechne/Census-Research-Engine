# Round 97 plan: spatial block cross-validation and MAUP sensitivity (Moraga)

**Goal.** Backlog N74 (Moraga chapters 11 and 16).
- **Predictive checks are in-sample today.** Random cross-validation overstates skill when nearby areas are alike;
  spatial block cross-validation does not.
- **Area results depend on the units** (the modifiable areal unit problem: scale and zoning effects).

Version 0.93.0. Branch `phase97/cv-maup`. Validation first.

## 1. Methods (frozen core `census/model_assessment_core.py`)

- **V1: spatial block k-fold cross-validation.**
  - Blocks are contiguous groups of areas (k-means on coordinates, or counties for tracts).
  - Scores: MAE, RMSE, 90% interval coverage and CRPS (Gaussian closed form) of held-out predictions.
  - Applies to `fit_model` (OLS/WLS), `small_area_estimates` (Fay–Herriot) and Round 96 disease mapping.
- **V0: random k-fold**, reported for contrast.
- **S1: MAUP sensitivity.**
  - Re-run one declared analysis (a correlation, a regression slope or an inequality measure) at several scales:
    block group, tract and county, where the data exist. Also re-run over R random zonings that aggregate tracts
    into contiguous zones of a target size (SKATER-like random spanning-tree cuts, Round 93 code).
  - Reports the range and distribution of the result across scales and zonings.

## 2. Validation (`scripts/model_assessment_validation.py`)

- **V1 against V0:**
  - designs: MI tracts with spatially correlated residuals (ranges 0, 20, 50 km);
  - targets: the true out-of-sample error for new areas drawn from the same process at held-out locations;
  - pass: the V1 RMSE estimate is within ±10% of the truth on average in every cell, and the V1 coverage estimate is
    within ±.03. V0 is expected to be optimistic when the range > 0.
- **S1** is descriptive: it reports how much a planted area-level slope varies with zoning when the individual-level
  relationship is fixed. No pass rule.

## 3. Engine

- **Option `assess="spatial_cv"`** on `fit_model`, `small_area_estimates` and the disease-mapping path, returning
  the scores and fold map.
- **Library `maup_sensitivity(...)`** plus a CLI and recipe walkthrough.
- **Recipe** `regression_sampling_error` and `spatial_patterns` sections; protocol rule; sources (Moraga 2023;
  Roberts et al. 2017 for block CV; Openshaw 1984 and Gotway and Young 2002 for MAUP).

## 4. Example and acceptance

- **Example (exploratory):**
  - spatial versus random CV of the Round 80 tract Fay–Herriot model in MI;
  - MAUP sensitivity of the poverty–uninsured correlation in Wayne County across block groups, tracts and 100 random
    zonings.
- STATUS, CHANGELOG, compatibility audit, tests, goldens, suite.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Core, script, criterion | done | tag `criterion-r97` |
| Results | fail (V1); MAUP reported | `model_assessment_validation.md` |
| Engine, recipe | done | `spatial_model(kind="cv" \| "maup")`; recipe; protocol |
| Example | done | `r97_model_assessment_example.md` |
| Goldens, suite | pass | goldens byte-identical; 2368 passed, 42 skipped |
| Exceptions | 3 | see audit |
