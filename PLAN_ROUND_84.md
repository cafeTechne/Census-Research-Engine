# Round 84 plan: epidemiologic measures of association from models

**Goal.** Backlog N61. Chapter 4 of *Foundations of Epidemiology* notes three things:
- prevalence data give odds ratios;
- for common outcomes the OR overstates the risk ratio, and most ACS outcomes are common (poverty, uninsurance,
  disability);
- absolute measures (risk difference, attributable fraction, excess cases) must accompany ratios.

Chapter 10 lists dose-response among Hill's considerations. The engine's binomial and logit fits report coefficients
and ORs only. Version 0.80.0. Branch `phase84/epi-measures`. Validation first.

## 1. Methods (frozen core `census/epi_measures_core.py`)

- **G1: marginal (standardized) risk ratio and risk difference by g-computation.**
  - Applies to an area binomial model (`fit_replicate` binomial, population target) and to a PUMS logit.
  - Predict every unit under exposure set to each level, then average with the population weights.
  - Area models: SEs from the replicate refits (ACS error) plus HC3 (population).
  - PUMS: SEs from SDR replicate refits.
- **P1: prevalence ratio for a binary PUMS outcome** by modified Poisson (log link) with SDR replicate SEs.
  - P1b: the same with model-based robust (sandwich) SEs, as a design-blind comparison.
- **F1: population attributable fraction**, standardized: PAF = 1 − P(Y | observed) / P(Y | exposure removed).
  - Intervals from the replicate refits on the logit scale of the fraction.
  - Reported with the book's caveat that fractions over several causes sum past 100%.
- **D1: dose-response across ordered exposure levels.**
  - Exposure quintiles or a declared ordinal, with a trend test on the level scores (linear contrast of the
    standardized risks).
  - The test is reported together with the departure-from-linearity test.

## 2. Validation (`scripts/epi_measures_validation.py`)

- **Area designs:** MI/NY counties and tracts, outcome prevalence .05, .15 and .35, exposure effect RR 1.0, 1.3 and
  1.8, with ACS-like errors and replicates (Round 46 generator).
- **PUMS designs:** Round 32's generator, prevalence .05–.35, binary and three-level exposures, with 1,000 and
  5,000 records.
- **Targets:** the population marginal RR, RD, PR and PAF.
- **Draws:** 2,000 per cell.
- **Pass:**
  - G1, P1 and F1 coverage ≥ .86 in every cell;
  - D1 trend size at .10 within [.07, .13] under no trend;
  - P1b is reported only.

## 3. Engine (only what passes)

- **New options on existing tools, not new tools:**
  - `fit_model(model="binomial", marginal="exposure_column")`;
  - `pums_regression(..., report="marginal")`;
  - `pums_regression(model="poisson", prevalence_ratio=True)`;
  - `fit_model(..., attributable="exposure_column")`;
  - `trend_test(kind="dose_response", ...)`.
- **Manifest statistics:** `marginal_rr`, `marginal_rd`, `paf`, `dose_trend`.
- **Rule:** when a binomial or logit outcome's prevalence exceeds 10%, the tool output pairs every OR with the
  marginal RR and a note that the OR overstates the RR for common outcomes.

## 4. Example and acceptance

- **Example (exploratory):** MI/NY county disability prevalence (B18101) by poverty quintile.
  - Marginal RR and RD for the top versus bottom quintile, the dose-response trend, and the PAF for poverty above
    20%.
  - An ACS outcome only, per the circularity rule.
- STATUS, CHANGELOG, compatibility audit, tests, goldens, suite.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Core, script, criterion | done | `epi_measures_core.py`; criterion `c5f6266` (tag `criterion-r84`) |
| Results | done | every candidate passes |
| Engine options, manifest statistics | done (no manifest statistics) | `fit_model(marginal=, dose_levels=)`, `pums_regression(marginal=)` |
| Example | done | `r84_marginal_example.md` |
| Goldens, suite | done | both byte-identical; 2269 passed, 42 skipped |
| Exceptions | listed | `round84_compatibility.md` |
