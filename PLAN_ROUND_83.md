# Round 83 plan: stratified analysis, Mantel–Haenszel and effect modification

**Goal.** Backlog N60. Chapters 7 and 8 of *Foundations of Epidemiology* describe how a covariable is handled:
- compute the crude measure;
- compute the stratum-specific measures;
- decide whether the covariable is a confounder (report an adjusted, pooled measure) or an effect modifier (report
  each stratum);
- the decision uses the 10% crude-versus-adjusted rule and a homogeneity check.

The engine has regression only. Version 0.79.0. Branch `phase83/stratified`. Validation first.

## 1. Methods (frozen core `census/stratified_core.py`)

- **MH1: Mantel–Haenszel pooled measures across strata.**
  - Risk ratio, risk difference and odds ratio, plus the rate ratio for person-time counts.
  - Intervals use Greenland–Robins variances (counts).
- **MH2: the same estimators on PUMS records with SDR replicate weights.** Refit with each of the 80 replicate
  weights; var = 4/80 Σ(θ_r − θ)².
- **H1: homogeneity of stratum measures.**
  - Counts: Breslow–Day–Tarone for the OR and a Woolf-type test for the RR.
  - PUMS: a replicate-based Wald test.
- **A1: additive interaction for two binary factors.**
  - RERI, the attributable proportion and the synergy index from a model with both factors and their product.
  - Intervals by the delta method (A1) and, as A1b, by the replicate or bootstrap percentile method.
- **Classification report (descriptive, not a test):**
  - crude versus adjusted, using the book's 10% rule;
  - whether the stratum measures differ (H1) and whether the crude lies between them;
  - the result is labelled `confounder`, `effect_modifier` or `neither` (book Table 8-5), with the inputs shown.

## 2. Validation (`scripts/stratified_validation.py`)

- **Count designs:**
  - 2, 4 and 8 strata;
  - expected events per stratum and exposure arm of 5, 20 and 100;
  - homogeneous effects (RR 1.5; OR matched) and heterogeneous effects (stratum RRs .7–2.5) for H1 size and power.
- **PUMS designs:** Round 32's generator (weight CV 1, household correlation .25), 2–4 strata, with 300 and 3,000
  records in the smallest stratum.
- **Additive interaction:** RERI 0 and .5, baseline risks .05 and .20, on both count and PUMS designs.
- **Draws:** 2,000 per cell.
- **Pass:**
  - coverage ≥ .86 in every cell for each pooled measure and RERI interval;
  - H1 size at .10 within [.07, .13] in the homogeneous cells;
  - size gates by smallest cell count are allowed when stated in the criterion.

## 3. Engine (only what passes)

- **Tool `stratified_analysis(input_path | state+year, exposure, outcome, strata, measure="rr")`** (full profile),
  for county count tables (cases and denominators by stratum) or PUMS conditions.
- **Recipe `confounding_and_effect_modification`:**
  - declare covariable roles before looking;
  - mediators are not adjusted;
  - report stratum measures for effect modifiers;
  - residual confounding from coarse categories.
- **Manifest:** a `covariables` block with declared roles (`confounder`, `effect_modifier`, `mediator`).
  - Regression analyses refuse a declared mediator in the formula.
  - Effect modifiers produce stratum-specific hypotheses.

## 4. Example and acceptance

- **Example (exploratory):** MI PUMS uninsured by disability status stratified by age band, with crude, MH and
  stratum RRs and the classification; and county deaths by poverty tertile stratified by age (owner's WONDER export,
  following the no-counts-1–9 rule).
- STATUS, CHANGELOG, compatibility audit, tests, goldens, suite.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Core, script, criterion | done | `stratified_core.py`; criterion `b358799` (tag `criterion-r83`) |
| Results | done | MH measures, RERI, Breslow-Day pass; Woolf and PUMS Wald homogeneity fail |
| Engine, manifest, tool, recipe | done | `stratified_analysis` (76 tools); recipe `confounding`; manifest `covariables` |
| Example | done | `r83_stratified_example.md` (PUMS; WONDER county x age not available) |
| Goldens, suite | done | both byte-identical; 2264 passed, 42 skipped |
| Exceptions | listed | `round83_compatibility.md` |
