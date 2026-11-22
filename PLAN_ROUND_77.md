# Round 77 plan: joinpoint regression and age-adjusted rate ratios

**Goal.** Backlog N54. Annual surveillance series, such as WONDER death rates, the owner's manual exports or
1-year ACS state estimates, are usually summarised in two ways:
- with **joinpoint regression** (NCI Joinpoint; Kim et al. 2000): segments of log-linear trend, the annual percent
  change (APC) per segment and the average APC (AAPC);
- with **rate ratios of age-adjusted rates**, using Tiwari et al. (2006) intervals.

Version 0.73.0. Branch `phase77/joinpoint`. Validation first.

## 1. Methods (frozen core `census/joinpoint_core.py`)

- **J1: number of joinpoints.** Grid search over joinpoint locations, with at least 2 points from the ends and
  between joins. Sequential permutation tests (Kim et al. 2000) choose 0–3 joinpoints, Bonferroni-adjusted, with
  4,999 permutations.
- **J2: APC intervals.**
  - Per segment, with t intervals given the chosen joinpoints.
  - J2b uses the empirical-quantile (bootstrap) method that Joinpoint 5 uses, which accounts for the uncertainty
    in where the joinpoints fall.
- **J3: AAPC over a fixed window.** A delta-method interval, and J3b a bootstrap interval.
- **R1: rate ratio of two directly age-adjusted rates.**
  - Tiwari et al. (2006) F-based interval.
  - R1b: Fay–Feuer gamma per rate with a ratio delta method. The engine's `age_adjusted_interval` is reused for
    each rate.
- **Weighting.** Weighted least squares with Poisson variance on the log scale (heteroscedastic), as Joinpoint
  does for rates with SEs.

## 2. Validation (`scripts/joinpoint_validation.py`)

- **Series:** 15, 20 and 25 annual points. The true model has 0, 1 or 2 joinpoints; slope changes are 0, 2 and 5
  APC points. Poisson counts give expected deaths of 50, 500 and 5,000 per year.
- **J1:**
  - **pass:** the false-joinpoint rate under 0 true joinpoints is ≤ .10 (nominal .05);
  - power is reported.
- **J2/J3:** coverage ≥ .86 per cell, given the correct number of joinpoints (J2) and with model selection
  (J2b/J3b, reported separately).
- **R1:** coverage ≥ .86 with small counts (5–50 per age stratum, 10 strata) and large counts.
- **Draws:** 1,000 per cell (permutation tests dominate the time; use checkpoints).
- **Interaction with Round 63:** interrupted series stay the route for a known policy date. Joinpoint is for
  describing trend changes without a pre-set date, and the result says so.

## 3. Engine (only what passes)

- **Tool:** `joinpoint(values|input_path, years, se|counts+population, max_joinpoints=3)` (full profile).
- **Manifests:** method `joinpoint` (statistic `apc` per segment, `aapc`), and `rate_ratio` for age-adjusted
  rates.
- **Recipe:** `policy_change` points here for trends without a known break date.
- **Refusals:** overlapping ACS 5-year releases (as `interrupted_series`), and WONDER-suppressed counts (1–9
  hidden; complete years only).

## 4. Example and acceptance

- **Example:** US drug-overdose age-adjusted death rates 1999–2022, from the owner's national WONDER export if it
  is present (skipped otherwise), with joinpoints and APCs compared with the published NCHS Data Brief APCs as a
  descriptive check.
- STATUS, CHANGELOG, compatibility audit, tests, goldens, suite.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Core, script, criterion | done | `joinpoint_core.py`, `joinpoint_validation.py`; criterion `01ad5a4` (tag `criterion-r77`) |
| Results | done | J1 selection passes; J2/J3/J2b/J3b APC and AAPC intervals fail (exploratory); R1, R1b pass |
| Engine, manifest, tool | done (no manifest) | `census/joinpoint.py`; tool `joinpoint` (73 tools); `policy_change` recipe; manifests not applicable |
| Example | skipped | no annual WONDER series among the owner's exports (plan allows skipping) |
| Goldens, suite | done | both goldens byte-identical; 2229 passed, 42 skipped |
| Exceptions | listed | `round77_compatibility.md` |
