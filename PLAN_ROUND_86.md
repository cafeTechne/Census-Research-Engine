# Round 86 plan: quantitative bias analysis

**Goal.** Backlog N63. Chapter 6 of *Foundations of Epidemiology* covers bias:
- bias is systematic and cannot be fixed by statistics;
- it can be bounded by sensitivity (bias) analysis.

Chapter 7 adds two points:
- when the causal direction between a covariable and the outcome is unclear, run the analysis both ways;
- residual confounding remains after coarse adjustment.

The engine reports sampling uncertainty only. Version 0.82.0. Branch `phase86/bias-analysis`. Validation first
where an interval is produced.

## 1. Methods (frozen core `census/bias_analysis_core.py`)

- **E1: E-values for unmeasured confounding** (VanderWeele and Ding 2017) for the point estimate and the interval
  limit nearest the null.
  - Inputs: risk ratios; odds ratios (with the common-outcome square-root conversion when prevalence exceeds 10%);
    rate ratios; and standardized differences for continuous outcomes.
  - Deterministic; checked against published worked examples.
- **M1: misclassification bias analysis for 2 × 2 tables** (PUMS `two_by_two` and county count tables).
  - Simple correction, given sensitivity and specificity of exposure or outcome classification, differential or
    not.
  - Probabilistic analysis (Lash, Fox and MacLehose): sensitivity and specificity drawn from trapezoidal or beta
    priors, combined with sampling error, giving a simulation interval.
- **B1: both-directions covariable sensitivity.** For a covariable declared `direction_uncertain`, the analysis runs
  with and without it and reports both estimates and their difference (chapter 7 practice). No new inference.

## 2. Validation (`scripts/bias_analysis_validation.py`)

- **E1:** numeric agreement with VanderWeele and Ding's published examples, and with the EValue R package outputs
  recorded as fixtures, to 1e-6.
- **M1 probabilistic:**
  - simulated 2 × 2 data with known misclassification;
  - priors centred on the true sensitivity and specificity (correct prior) and offset by .05 (misspecified prior);
  - nondifferential and differential cases;
  - 1,000 draws per cell.
  - **Pass:** coverage of the true OR/RR ≥ .86 under the correct prior. Misspecified-prior coverage is reported.

## 3. Engine (only what passes)

- **E-values:** an `e_value` field added to the outputs of fit_model coefficients (ratio scales), two_by_two,
  marginal RR (Round 84) and MH measures (Round 83). Bundles include an E-value table.
- **Tool `bias_analysis(kind="misclassification", table=..., sensitivity=..., specificity=...)`** (full profile).
- **Manifest:** a `sensitivity_analyses` block for pre-registered bias analyses (priors declared before the run).
- **Recipe `reporting` section "Bias and sensitivity analyses".**

## 4. Example and acceptance

- **Example (exploratory):** the Round 79 uninsured comparison.
  - E-value for the Black–White crude RR.
  - Outcome misclassification of self-reported coverage (priors from the published ACS–Medicaid record linkage
    literature, cited in the criterion).
- STATUS, CHANGELOG, compatibility audit, tests, goldens, suite.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Core, script, criterion | | |
| Results | | |
| Engine, tool, manifest, recipe | | |
| Example | | |
| Goldens, suite | | |
| Exceptions | | |
