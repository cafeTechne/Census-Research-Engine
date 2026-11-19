# Round 42 plan: missing data, censored counts and interrupted time series

**Goal.** The last roadmap round (`ROADMAP_STATISTICS.md`):

- **missing covariates**: complete-case analysis vs multiple imputation (statsmodels `MICE`, Rubin's rules)
  when a covariate is missing at random for some areas;
- **censored counts**: WONDER hides county death counts of 1–9; Round 29 dropped those counties
  (complete case). A Poisson likelihood that treats a hidden count as "between 1 and 9" uses them
  without imputing or publishing any value;
- **interrupted time series** for state or national annual series (segmented regression with
  autocorrelated errors).

Version 0.39.0. Baseline: 1972 passed, 37 skipped. Ground rules as Round 31 (branch
`phase42/missing-censored-its`; validation first; the maintainer agent implements and merges;
releases wait).

## 1. Procedures (90% intervals)

| ID | Problem | Procedure |
| :--- | :--- | :--- |
| D0 / D1 | slope of x with covariate w missing for 20% of areas | complete case / MICE (20 imputations, Rubin's rules) |
| C0 / C1 | Poisson slope with counts 1–9 hidden | complete case (HC3) / interval-censored Poisson likelihood with sandwich SE |
| A0 / A1 / A2 | level and slope change after an interruption, 20 annual points, AR(1) errors | OLS / Newey–West HAC (lag 2) / AR(1) GLS (statsmodels `GLSAR`, iterated) |

## 2. Validation (`scripts/missing_censored_its_validation.py` → `docs/audits/missing_censored_its_validation.md`/`.json`)

- Missing: 145 areas; y = 1 + 0.5x + 0.5w + e; corr(x, w) = 0.5; w missing with probability depending
  on the observed outcome (MAR: logistic, ≈20%) or completely at random (MCAR). 2 cells; target 0.5 (x's slope).
- Censored: 145 counties, expected counts lognormal with median 10 or 30; log-rate 0.3x; gamma
  overdispersion (shape 4); counts 1–9 censored. 2 cells; target 0.3.
- ITS: 20 years, interruption at year 11; level change 1, slope change 0.2, AR(1) φ ∈ {0.3, 0.6},
  noise SD 1. 2 cells; targets 1 and 0.2 (both judged).
- 2,000 draws per cell; seed `20270304 + cell`.
- **Acceptance:** coverage ≥ .86 in every cell of the problem, per procedure; failures count as
  non-coverage; the "0" procedures are comparisons (reported).

## 3. Engine and docs

`census/missing_data.py` (`impute_and_fit`), `census/censored_counts.py` (`fit_censored_poisson`, with the
WONDER rule: never output a hidden county's value), `census/time_series.py` (`interrupted_series`);
MCP: `fit_model(missing="mice")`, `fit_model(model="censored_poisson", censored_column=...)` and
`trend_test(..., interruption=year)` where validated; recipe updates; mirrored rule text. Tests;
flags against the audit; goldens unchanged; full suite; STATUS, CHANGELOG, version 0.39.0.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Criterion commit | `5f81de2` | Pushed before the full run. |
| D / C / A results | Mixed | D1 passed; C1 failed narrowly; A0–A2 failed. |
| Engine, tests | Done | missing_censored_its; fit_model(impute); 5 tests. |
| Goldens, final suite | | |
| Exceptions | Recorded | Pre-freeze: direct MI implementation; missingness on y. |
