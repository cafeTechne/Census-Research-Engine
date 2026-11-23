# Round 94 plan: health inequality monitoring (WHO handbook)

**Goal.** Backlog N71 (WHO, *Handbook on Health Inequality Monitoring*, 2013, chapters 3–5; mapping in
`docs/literature/who_health_inequality_monitoring.md`). The engine has the WHO complex measures for ordered groups
(SII, RII, concentration index) and several for non-ordered groups (between-group variance, Theil, MLD, index of
disparity). It lacks the rest of the handbook's monitoring set. Version 0.90.0. Branch `phase94/inequality-monitoring`.
Validation first.

## 1. Methods (frozen core `census/inequality_monitoring_core.py`)

- **M1: mean difference from the overall mean (MDM).** Unweighted and population-weighted:
  Σ w_g |r_g − r̄| / Σ w_g.
- **M2: mean difference from the best subgroup (MDB).** The same measure taken from the best subgroup (or a declared
  reference group).
  - With a declared reference, the reference is fixed.
  - With "best", the reference is chosen from the data. That selection biases the measure, so it is evaluated
    separately.
- **P1: population attributable risk against the best subgroup**, absolute (r̄ − r_best) and relative
  (100·(r̄ − r_best)/r̄), with a declared or data-selected reference.
- **T1: change in an inequality measure between two non-overlapping releases.** Covers SII, RII, BGV, MDM, MDB and
  P1, with intervals from independent replicate draws per release.
- **Intervals for all:** replicate (SDR) or parametric draws from the estimate SEs, percentile 90% intervals.
  Measures with absolute values are near a boundary when groups are close: the result is labelled when the interval
  touches 0.

## 2. Validation (`scripts/inequality_monitoring_validation.py`)

- **Designs:**
  - 4, 6 or 8 groups (race/ethnicity or income-like categories) with county-like or state-like sampling error
    (Round 76 designs);
  - true spreads from none to large;
  - two releases with no change or a change.
- **Draws:** 2,000 per cell.
- **Pass:** 90% coverage ≥ .86 in every cell, separately for M1 and M2 with a declared reference, M2 and P1 with the
  data-selected best, and T1.
- **Expected:** data-selected "best" estimators may fail with small true spreads. They are then reported with the
  declared-reference version only.

## 3. Engine and reporting

- **`disparity_measures`** gains `measures=["mdm", "mdb", "par"]`, `reference=`, and `compare_release=` (T1).
- **Library `double_disaggregation(...)`:** a two-stratifier table (e.g. race × poverty status, or place × income)
  with cell estimates and reliability flags (CV, suppression).
- **Priority quadrant report:** each area or subgroup classified by its level against a benchmark and its inequality
  against the median, with interval-aware "uncertain" labels.
- **Recipe** `health_inequality` sections (absolute and relative together, benchmarking, trends); protocol rule;
  sources registered (WHO 2013).

## 4. Example and acceptance

- **Example (exploratory):** uninsured rate by race/ethnicity across MI counties, 2014–2018 versus 2019–2023, with
  MDM, MDB, PAR and the change in SII.
- STATUS, CHANGELOG, compatibility audit, tests, goldens, suite.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Core, script, criterion | done | tag `criterion-r94` |
| Results | PAR, SII, T1 pass; MDM/MDB fail | `inequality_monitoring_validation.md` |
| Engine, reporting | done | `disparity_measures(who_measures, compare_years)`; double disaggregation; quadrants |
| Example | done | `r94_inequality_monitoring_example.md` |
| Goldens, suite | see audit | `round94_compatibility.md` |
| Exceptions | 3 | see audit |
