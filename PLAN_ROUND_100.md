# Round 100 plan: multiple imputation by fully conditional specification (van Buuren, FIMD)

**Goal.** Backlog N77 (van Buuren, *Flexible Imputation of Missing Data*, chapters 2–7; mapping in
`docs/literature/van_buuren_fimd.md`).
- Area frames have real missing values: ACS jam values for medians in small tracts, suppressed estimates, and CHR
  measures missing for small counties.
- The engine imputes at most two covariates under a normal model (Rounds 42, 47).

Version 0.96.0. Branch `phase100/mice`. Validation first.

## 1. Methods (frozen core `census/mice_core.py`)

- **I1: fully conditional specification for any number of incomplete variables**, outcome included:
  - visit sequence by missingness; 10 cycles;
  - Bayesian linear regression imputation (parameter draws) or **predictive mean matching** (type-1 matching with 5
    donors), chosen per variable.
- **Passive imputation:** derived variables (e.g. a rate from a numerator and denominator, or a log) are recomputed
  after each step, not imputed independently.
- **Analysis and reporting:** Rubin's rules with Barnard–Rubin df. Every result gets the fraction of missing
  information (FMI) and λ. Pooling happens on the analysis scale, with transformed pooling for correlations
  (Fisher z) and ratios (log).
- **S1: δ-adjustment sensitivity** (MNAR). Imputed values of a declared variable are shifted by δ on a grid set in
  advance (e.g. −0.5, −0.25, 0, 0.25, 0.5 SD), and the pooled estimate is reported as a function of δ. It is
  descriptive.

## 2. Validation (`scripts/mice_validation.py`)

- **Designs:**
  - 145 and 600 areas; 3–6 variables with 10–40% MAR missingness in several of them, including the outcome;
  - a skewed, bounded variable (a rate in [0, 100]) where PMM should keep bounds and the normal model need not.
- **Draws:** 1,000 per cell (m = 20).
- **Pass:** 90% coverage of regression coefficients ≥ .86 in every cell for PMM and for the Bayesian linear method.
  Bias is reported for complete-case analysis. The bounded-variable cell also requires PMM imputations within
  bounds (always, by construction) and coefficient coverage ≥ .86.
- **S1:** at δ = 0 the estimate equals the MAR fit (an exact check).

## 3. Engine

- **`impute_and_fit(..., incomplete=[any number], method="pmm" | "norm", passive={...}, delta={...})`.** The fit_model
  route keeps the Round 42/47 behaviour for one or two names unless `method` is given.
- **A reporting block** gives the missingness pattern, the imputation methods, m, cycles, FMI per coefficient and the
  δ curve.
- **Recipe** `regression_sampling_error` section; protocol rule; sources (van Buuren 2012; Rubin 1987; Barnard and
  Rubin 1999; Little 1988 for PMM).

## 4. Example and acceptance

- **Example (exploratory):** an MI tract regression of median household income (jam values missing in small tracts)
  on poverty and education, with PMM, the FMI, and the δ curve for the missing incomes.
- STATUS, CHANGELOG, compatibility audit, tests, goldens, suite.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Core, script, criterion | done | tag `criterion-r100` |
| Results | pass (PMM, norm) | `mice_validation.md` |
| Engine, recipe | done | `fit_model(impute_method=, impute_delta=)`; recipe; protocol |
| Example | done | `r100_mice_example.md` |
| Goldens, suite | see audit | `round100_compatibility.md` |
| Exceptions | 2 | see audit |
