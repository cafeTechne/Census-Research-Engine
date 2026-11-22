# Round 90 plan: positivity diagnostics, stabilized and truncated weights, IPW versus g-formula

**Goal.** Backlog N66 (Hernán and Robins chapters 3.3, 12–13, 15).
- Inverse probability weighting needs **positivity**: every confounder pattern must have treated and untreated
  units.
- Near-violations give extreme weights and unstable estimates.
- Agreement between IP weighting and standardization (g-formula) is a model check.

`estimate_effect` (Round 41) notes "check the propensity distribution" but shows nothing. Version 0.86.0. Branch
`phase90/positivity`. Validation first.

## 1. Methods (frozen core `census/positivity_core.py`)

- **Overlap diagnostics.**
  - Propensity-score distributions by treatment group: quantiles, the share outside [.05, .95], and the overlap
    coefficient.
  - Standardized mean differences of confounders, before and after weighting.
  - Weight summaries: maximum, effective sample size.
- **W1: stabilized IP weights** (chapter 12.3).
- **W2: weights truncated at the 1st and 99th percentiles.**
- **W3: overlap weights** (Li, Morgan and Zaslavsky 2018). These change the estimand to the overlap population; the
  result says so.
- **G1: g-formula (standardization) estimate** beside IPW. Disagreement beyond the sum of their SEs is flagged.

## 2. Validation (`scripts/positivity_validation.py`)

- **Designs:** Round 41's area designs (MI/NY counties and tracts, a binary treatment from a logistic propensity),
  with propensity strength set so that 0%, 5% and 15% of units have propensities beyond [.05, .95].
- **Effects:** constant and heterogeneous.
- **Draws:** 2,000 per cell.
- **Pass:** coverage ≥ .86 in every cell for each estimator, against its own estimand (ATE for W1/W2, the
  overlap-population effect for W3). Size of the IPW-versus-g-formula flag under correct models ≤ .10. Coverage of
  plain IPW is reported to show what limited overlap does.

## 3. Engine (only what passes)

- `estimate_effect` returns the diagnostics always.
- `weights="stabilized" | "truncated" | "overlap"` options, used only where validated.
- When more than 5% of units fall outside [.05, .95], a note recommends overlap weights or restriction (chapter 3.3).
- Recipe `causal` section "Check positivity".

## 4. Example and acceptance

- **Example (exploratory):** the Round 41 example re-run with diagnostics.
- STATUS, CHANGELOG, compatibility audit, tests, goldens, suite.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Core, script, criterion | done | tag `criterion-r90` |
| Results | done | W2, W3, G1, flag pass; W1 (stabilized IPW) fails with 5%+ extreme propensities |
| Engine, recipe | done | `estimate_effect` positivity + `weights=`; recipe, protocol rule |
| Example | done | `r90_positivity_example.md` |
| Goldens, suite | see audit | `round90_compatibility.md` |
| Exceptions | 3 | see audit |
