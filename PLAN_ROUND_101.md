# Round 101 plan: demographic estimation tools (IUSSP Tools for Demographic Estimation)

**Goal.** Backlog N78 (Moultrie et al., *Tools for Demographic Estimation*, 2013, chapters 1, 31–35; mapping in
`docs/literature/iussp_tools_demographic_estimation.md`). Version 0.97.0. Branch `phase101/demography`. Validation
first for the life-table intervals; the indices are exact computations.

## 1. Methods (frozen core `census/demography_core.py`)

- **Q1: age-data quality.**
  - Whipple's index (ages 23–62, digits 0 and 5) and Myers' blended index from single-year age counts (PUMS
    weighted, decennial counts).
  - Sex ratios by age and the UN age-sex accuracy index (sex-ratio score + 3 × age-ratio scores).
  - Replicate intervals for PUMS (SDR weights). Exact values for decennial counts.
- **L1: abridged life table** from age-band deaths and populations (WONDER bands: <1, 1–4, 5–14, …, 85+):
  - band ₙaₓ: CDC/NCHS conventions, the infant a₀ from the infant mortality level (Coale–Demeny), and the open
    interval by 1/M;
  - ₙqₓ, lₓ, Lₓ, Tₓ, eₓ;
  - Chiang II standard errors of eₓ (Poisson deaths).
- **L2: Arriaga decomposition** of a life-expectancy difference into age-band contributions, and by cause using
  cause-specific death shares within bands.
- **M1: census-survival net migration by age** between two decennial censuses (2010, 2020): expected survivors from
  national survival ratios, with net migration as observed minus expected. Descriptive, exact identities only.

## 2. Validation (`scripts/demography_validation.py`)

- **L1:**
  - designs: life tables with US-like mortality, with populations of 50,000, 500,000 or 5 million (counties to
    states) and Poisson deaths;
  - pass: e₀ and e₆₅ Chiang interval coverage ≥ .86 in every cell.
- **Q1:** exact checks only. Whipple = 100 for uniform ages and 500 when only digits 0 and 5 occur; Myers = 0 for
  uniform ages.
- **L2:** the contributions sum to the life-expectancy difference exactly.

## 3. Engine

- **Library `census.demography`:** `age_quality`, `life_table`, `arriaga`, `census_survival_migration`.
- **Readers** from WONDER national age-group exports (Round 95 reader) and PUMS ages (`pums_tabulate`).
- **Recipe** (new `demography` recipe, 27 recipes); protocol rule; sources (Moultrie et al. 2013; Chiang 1984;
  Arriaga 1984; Myers 1940; Whipple 1919 via Shryock and Siegel).

## 4. Example and acceptance

- **Examples (exploratory):**
  - US life expectancy at birth, 2013–2017 against 2018–2022, from the national WONDER exports, with an Arriaga
    decomposition by age and by the 12 causes on file;
  - Whipple and Myers indices for MI PUMS ages.
- STATUS, CHANGELOG, compatibility audit, tests, goldens, suite.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Core, script, criterion | | |
| Results | | |
| Engine, recipe | | |
| Examples | | |
| Goldens, suite | | |
| Exceptions | | |
