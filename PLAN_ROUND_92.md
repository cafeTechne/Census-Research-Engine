# Round 92 plan: GWR, geodemographic classification, regionalization and diversity with ACS uncertainty

**Goal.** Backlog N69 (Walker chapter 8).
- **Geographically weighted regression (GWR):** explores whether relationships vary over space. Walker stresses
  that it is exploratory: local collinearity and edge effects.
- **Geodemographic classification** (k-means on principal components) and **regionalization** (SKATER,
  contiguity-constrained clustering): label neighbourhood types and build regions.
- **The entropy diversity index:** describes group mix.

None of these accounts for ACS sampling error today. Version 0.88.0. Branch `phase92/spatial-models`. Validation
first.

## 1. Methods (frozen core `census/spatial_models_core.py`)

- **R1: GWR.**
  - Gaussian kernel; bandwidth by AICc.
  - Local coefficients with replicate-refit SEs (ACS error) plus the local model SE.
  - A Monte Carlo test of spatial non-stationarity, permuting locations (99 permutations).
- **C1: geodemographic classification.**
  - k-means on standardized principal components, with k chosen by the elbow and silhouette, declared before
    looking.
  - Stability: each replicate refits the classification; per-area assignment stability is reported (share of
    replicates agreeing, after label matching).
- **C2: SKATER regionalization**, with the same replicate stability.
- **D1: entropy diversity index** (Theil's E) per area, with replicate SEs.

## 2. Validation (`scripts/spatial_models_validation.py`)

- **R1:**
  - designs: MI/NY tract geometry, with slopes constant or varying smoothly over space, and realistic ACS error;
  - pass: local-coefficient 90% coverage ≥ .86 on average and ≥ .80 for 90% of areas, and the non-stationarity
    test's size ≤ .10 under constant slopes.
  - A failure leaves GWR exploratory (Walker's own recommendation).
- **C1 and C2:**
  - designs: clusters planted in MI tracts with realistic error;
  - reported (no pass rule): the adjusted Rand index against the truth and the calibration of the stability
    measure, i.e. whether areas flagged unstable are the misclassified ones.
- **D1:** coverage ≥ .86 (like segregation, Round 50).
- **Draws:** 500 per cell (GWR refits are costly).

## 3. Engine (only what passes; exploratory tools are labelled)

- **Tools:** `spatial_model(kind="gwr" | "classify" | "regionalize")`, one full-profile tool with flat parameters.
- **Diversity** joins the `segregation` recipe as a descriptive measure.
- **Recipe `spatial_patterns`** sections, with Walker's caveats.

## 4. Example and acceptance

- **Examples (exploratory):** a GWR of tract poverty on unemployment and education in Wayne County; a
  geodemographic classification of MI tracts with stability; SKATER regions in Detroit.
- STATUS, CHANGELOG, compatibility audit, tests, goldens, suite.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Core, script, criterion | | |
| Results | | |
| Engine, tool, recipes | | |
| Examples | | |
| Goldens, suite | | |
| Exceptions | | |
