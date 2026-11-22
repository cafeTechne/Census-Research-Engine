# Round 80 plan: Fay–Herriot for proportions and temporal Fay–Herriot

**Goal.** Backlog N57. The engine's Fay–Herriot is validated on the linear scale (.891 spatial; Round 16+). Two
gaps remain:
- tract and small-county **proportions near 0 or 1** (uninsured, disability), where linear Fay–Herriot can give
  negative estimates and wrong MSE;
- **borrowing strength over time** across non-overlapping 5-year releases.

Version 0.76.0. Branch `phase80/sae`. Validation first.

## 1. Methods (frozen core `census/sae_extensions_core.py`)

- **P1: arcsine-square-root Fay–Herriot** (Hadam, Würz and Kreutzmann 2020; Casas-Cordero et al. 2016).
  - The direct variance is mapped through the transform with the effective sample size n_eff = p(1−p)/var.
  - EBLUP on the transformed scale, back-transformed with bias correction.
  - MSE from a parametric bootstrap (B = 200).
- **P1b:** the naive back-transform without bias correction, as a comparison.
- **T1: Rao–Yu (1994)** temporal Fay–Herriot. Area random effects plus AR(1) area-time effects across 2–3
  non-overlapping releases; REML; Prasad–Rao-type MSE.
- **Refusals:** overlapping releases (shared sample years violate independent sampling errors), and areas with a
  zero direct variance.

## 2. Validation (`scripts/sae_extensions_validation.py`)

- **P1:**
  - designs: MI and NY tract and county geometries, true proportions .02–.50, and ACS-like sampling variances from
    real S2701/B27010 MOEs;
  - pass: mean per-area coverage of 90% intervals ≥ .86, the lowest decile of areas ≥ .80 (Round 36-style), and
    relative bias of the estimates ≤ 10% for p < .10;
  - P1b is reported only.
- **T1:**
  - designs: 2 and 3 releases, ρ .3 and .8, and the same variance sources;
  - pass: per-area coverage ≥ .86 mean; MSE gain over single-release FH reported.
- **Draws:** 500 per cell (the bootstrap MSE dominates; checkpoints).

## 3. Engine (only what passes)

- **Tools:** `small_area_estimates(..., transform="arcsine")` and `small_area_estimates(..., temporal=True,
  release_column="Year")`, with no new tool.
- **Manifests:** method `fay_herriot` args `transform`, `temporal`.
- **Recipe:** `small_area` gets "proportions near 0" and "several releases" sections.

## 4. Example and acceptance

- **Example:** MI tract uninsured rates from 2014–2018 and 2019–2023, showing direct, arcsine FH and temporal FH,
  with a map of the estimates and their MSE (exploratory).
- STATUS, CHANGELOG, compatibility audit, tests, goldens, suite.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Core, script, criterion | | |
| Results | | |
| Engine, manifest | | |
| Example | | |
| Goldens, suite | | |
| Exceptions | | |
