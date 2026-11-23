# Round 95 plan: years of potential life lost and surveillance aberration detection (CDC SS1000)

**Goal.** Backlog N72 (CDC, *Principles of Epidemiology in Public Health Practice*, 3rd ed., lessons 3–5; mapping in
`docs/literature/cdc_principles_of_epidemiology.md`). Version 0.91.0. Branch `phase95/ypll-surveillance`. Validation
first. All WONDER data are the owner's manual exports; no sub-national counts 1–9 or values derived from them leave
the engine.

## 1. Methods (frozen core `census/surveillance_core.py`)

- **Y1: YPLL to an end point** (65 or 75, declared).
  - Computed from age-group death counts as Σ deaths_a × (end − midpoint_a) over age groups below the end point.
    This is CDC's grouped-data method.
  - Crude YPLL rate per 100,000 (Census Population Estimates, Round 92, or ACS denominators).
  - Age-adjusted YPLL rate (direct, 2000 US standard).
  - Gamma (Fay–Feuer type) intervals treating the YPLL as a weighted Poisson sum.
- **Suppression.** Age groups with suppressed counts (1–9) are handled with the Round 29 bounds: the result is an
  interval of YPLL values, never an imputed count. Outputs are refused when a published value would let a suppressed
  count be recovered.
- **A1: historical-limits flag.** The latest annual rate is compared with the mean ± 2 SD of the previous k years
  (k = 5, declared). This adapts the MMWR historical-limits method to annual data, with the current year's Poisson
  variance added.
- **A2: EARS-style C2 flag** on annual counts: a baseline of the previous 7 years with a 2-year guard band, flagged
  at 3 SD.

## 2. Validation (`scripts/surveillance_validation.py`)

- **Y1:**
  - designs: counties and states with realistic death counts by age (WONDER-like rates times PEP populations), with
    and without suppression;
  - pass: 90% coverage of the age-adjusted YPLL rate ≥ .86 in every cell (unsuppressed), and bounds that contain the
    truth in every suppressed draw.
- **A1 and A2:**
  - designs: annual Poisson series with trends and overdispersion (negative binomial, Round 39 levels), with and
    without a planted aberration of 1.5× or 2× in the last year;
  - pass: false-alarm rate ≤ .05 without an aberration, in series with no trend and no overdispersion;
  - reported: false-alarm rates under trend and overdispersion, and detection power.
  - A flag that fails is labelled descriptive.

## 3. Engine

- **Library `census.surveillance`:** `ypll(...)` and `aberration(...)`.
- **Tool options:** `joinpoint(..., aberration="historical_limits" | "ears_c2")` adds a flag for the last period.
  The WONDER-reading path computes YPLL from age-group exports.
- **Figure:** a deviation chart against historical limits (CDC lesson 4, Figure 4.25 style).
- **Recipe** `external_health_outcome` and a new recipe section; protocol rule; sources registered (CDC 2012).

## 4. Example and acceptance

- **Example (exploratory):** state-level YPLL-75 for drug overdose and all causes, MI/NY/OH/PA, from the owner's
  national and state WONDER exports already on file. Historical-limits flags for the latest year. No county counts
  1–9 are output.
- STATUS, CHANGELOG, compatibility audit, tests, goldens, suite.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Core, script, criterion | done | tag `criterion-r95` |
| Results | all pass | `surveillance_validation.md` |
| Engine, figure, recipe | done | `census/surveillance.py`; `joinpoint(aberration=)`; deviation chart |
| Example | done | `r95_surveillance_example.md` |
| Goldens, suite | see audit | `round95_compatibility.md` |
| Exceptions | 3 | see audit |
