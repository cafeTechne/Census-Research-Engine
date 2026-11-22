# Round 91 plan: IP-weighted marginal structural models for annual policy panels

**Goal.** Backlog N67 (Hernán and Robins chapters 19–21).
- In annual state panels, policies (treatments) and confounders vary over time.
- Confounders such as unemployment can be affected by past policy (**treatment-confounder feedback**). Adjusting
  for them by regression is then biased, and not adjusting is confounded.
- IP-weighted marginal structural models (MSMs) are the standard g-method.

Round 78's staggered DiD adjusts for nothing time-varying. Version 0.87.0. Branch `phase91/msm`. Validation first.

## 1. Methods (frozen core `census/msm_core.py`)

- **M1: MSM for the effect of cumulative or current treatment** on an annual outcome.
  - Stabilized time-varying IP weights: the product over years of P(A_t | past A) / P(A_t | past A, past L).
  - Weights are fitted with pooled logistic models; the outcome model is weighted least squares.
  - Interval: a state-cluster bootstrap (states resampled).
- **M2: the same with weights truncated at the 1st and 99th percentiles.**
- **Comparison (reported only):** naive regression adjusting for current L (biased under feedback), and no
  adjustment.
- **Time zero and eligibility** follow Round 89's target-trial block. Treatment "start and stay on" strategies only
  (no dynamic regimes).

## 2. Validation (`scripts/msm_validation.py`)

- **Panels:** 51 units, 12 or 18 years; AR(1) state-year errors; a time-varying confounder L_t affected by past
  treatment and affecting future treatment and the outcome (the book's Figure 20.3 structure).
- **Effects:** treatment effect 0 or −2; feedback strength 0, .5 and 1.
- **ACS-like error:** as in Round 78.
- **Draws:** 1,000 per cell.
- **Pass:** M1 (and M2) coverage ≥ .86 in every cell. Naive-regression bias and coverage are reported as the
  motivating contrast.

## 3. Engine (only what passes)

- Option `difference_in_differences(design="msm", time_varying_confounders=[...])` for annual panels (refusals as
  in Round 78), or a separate function if the parameters do not fit.
- Recipe `policy_change` step for time-varying confounding.

## 4. Example and acceptance

- **Example (exploratory):** Medicaid expansion and the state uninsured rate (Round 78's panel) with state
  unemployment as a time-varying confounder (BLS LAUS annual averages; the source is added if not present, after
  checking access terms).
- STATUS, CHANGELOG, compatibility audit, tests, goldens, suite.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Core, script, criterion | done | tag `criterion-r91` |
| Results | fail | M1 .805–.881, M2 .799–.885; exploratory |
| Engine, recipe | done | `difference_in_differences(design="msm")`; recipe, protocol |
| Example | done | `r91_msm_example.md` |
| Goldens, suite | see audit | `round91_compatibility.md` |
| Exceptions | 3 | see audit |
