# Round 99 plan: matching estimators and triple differences (Mixtape)

**Goal.** Backlog N76 (Mixtape: matching and subclassification; difference-in-differences). The engine weights
(IPW/AIPW) but does not match, and its DiD tools cannot use a within-unit comparison group (triple differences, as
in Gruber 1994). Version 0.95.0. Branch `phase99/matching-ddd`. Validation first.

## 1. Methods (frozen core `census/matching_core.py`)

- **M1: nearest-neighbour matching** on covariates (Mahalanobis distance; 1 or 4 matches, with replacement) for the
  ATT and the ATE:
  - the Abadie–Imbens (2011) regression bias correction;
  - the Abadie–Imbens (2006) variance (matching-based conditional variance).
- **M2: coarsened exact matching** (Iacus, King and Porro 2012):
  - declared coarsenings; strata weights; the effect by weighted regression on the matched sample;
  - reports the share of treated units matched (the estimand changes when units are dropped).
- **M3: propensity-score matching** (1:1 caliper 0.2 SD of the logit). The interval is a matched-pairs bootstrap,
  which is known to be invalid; the result is reported, and validation decides.
- **T3: triple differences.** The DiD of the treated-group difference minus the DiD of the within-unit untreated
  group. For area panels: state × group × period, with group-specific outcomes (e.g. adults 19–64 against 65+). The
  interval comes from replicate or cluster (state) variance.

## 2. Validation (`scripts/matching_validation.py`)

- **M1–M3:**
  - designs: Round 90 confounding designs (145 and 600 areas; overlap good and limited; constant and heterogeneous
    effects);
  - pass: coverage ≥ .86 in every cell for M1 (bias-corrected) and M2 (against its stated estimand). M3 is expected
    to fail.
- **T3:**
  - designs: Round 78-style 51-unit panels with two groups per unit, where a group-specific shock violates simple
    parallel trends but not the triple-difference assumption;
  - pass: coverage ≥ .86. Simple DiD bias is reported.
- **Draws:** 2,000 per cell.

## 3. Engine

- **`estimate_effect(kind="matching", method="nn" | "cem" | "ps")`**, with balance tables before and after matching.
- **`difference_in_differences(design="triple", group=...)`.**
- **Recipe** `causal` and `policy_change` sections; protocol rule; sources (Abadie and Imbens 2006, 2011; Iacus,
  King and Porro 2012; Gruber 1994; Cunningham).

## 4. Example and acceptance

- **Example (exploratory):** Medicaid expansion and uninsured adults 19–64 against adults 65+ (who are unaffected),
  by state, as a triple difference on the Round 78 panel (ACS 1-year S2701 by age). Matching on the Round 90 county
  example.
- STATUS, CHANGELOG, compatibility audit, tests, goldens, suite.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Core, script, criterion | | |
| Results | | |
| Engine, recipe | | |
| Example | | |
| Goldens, suite | | |
| Exceptions | | |
