# Round 98 plan: regression discontinuity (Mixtape)

**Goal.** Backlog N75 (Cunningham, *Causal Inference: The Mixtape*, RDD chapter; mapping in
`docs/literature/cunningham_mixtape.md`). Many census questions have a cutoff: Medicare eligibility at age 65,
program thresholds by income-to-poverty ratio, and age-based policies in PUMS. Version 0.94.0. Branch
`phase98/rdd`. Validation first.

## 1. Methods (frozen core `census/rdd_core.py`)

- **R1: sharp RDD.**
  - Local linear regression on each side of the cutoff, triangular kernel.
  - MSE-optimal bandwidth (Imbens–Kalyanaraman-type plug-in).
  - Robust bias-corrected interval (Calonico, Cattaneo and Titiunik 2014): a local quadratic bias estimate with a
    pilot bandwidth and an adjusted SE.
  - The conventional interval is reported for contrast.
- **R2: fuzzy RDD.** The ratio of outcome and treatment jumps, with the same robust interval by the delta method.
- **Discrete running variables** (age in whole years, as in PUMS): estimation on cell means with cell weights.
  Inference clusters by running-variable value (Lee and Card 2008), and the result is labelled as such.
- **Survey data:** weighted local regressions with SDR replicate weights. The replicate SE is used in place of the
  model SE (the robust bias correction is computed on each replicate).
- **Diagnostics:**
  - D1: density test of the running variable at the cutoff (McCrary-type local linear density difference);
  - D2: placebo cutoffs;
  - D3: covariate jumps;
  - D4: donut estimates excluding the cells next to the cutoff.

## 2. Validation (`scripts/rdd_validation.py`)

- **Designs:**
  - continuous running variable, with smooth outcomes that are linear, quadratic or have curvature changing at the
    cutoff;
  - jumps 0 and 0.2 SD;
  - n of 2,000, 10,000 or 50,000;
  - discrete running variable (40 values, PUMS-age-like) with survey weights and SDR replicates.
- **Draws:** 2,000 per cell.
- **Pass:** robust intervals cover ≥ .86 in every cell (continuous); discrete-with-replicates cover ≥ .86. The density
  test's size is ≤ .10 under no manipulation. Conventional intervals are reported.

## 3. Engine

- **New full-profile tool** `regression_discontinuity(input_path, outcome, running, cutoff, treatment=None,
  weights=None, replicates=..., kind="sharp" | "fuzzy")`. It takes PUMS frames from `pums_tabulate`'s export or a
  frame. 79 → 80 tools: README, STATUS, CLI and sources updated.
- **Recipe** `causal` section; protocol rule; sources (Calonico, Cattaneo and Titiunik 2014; Lee and Lemieux 2010;
  McCrary 2008; Card, Dobkin and Maestas 2008; Cunningham).

## 4. Example and acceptance

- **Example (exploratory):** health insurance coverage and Medicare coverage at age 65 in the MI PUMS 2019–2023
  (Card, Dobkin and Maestas 2008, with ACS data). Fuzzy RDD of any coverage on Medicare at 65, with the density test.
- STATUS, CHANGELOG, compatibility audit, tests, goldens, suite.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Core, script, criterion | done | tag `criterion-r98` |
| Results | discrete with replicates pass; continuous and density test fail | `rdd_validation.md` |
| Engine, tool, recipe | done | tool `regression_discontinuity` (80 tools); recipe `causal`; protocol |
| Example | done | `r98_rdd_example.md` |
| Goldens, suite | see audit | `round98_compatibility.md` |
| Exceptions | 3 | see audit |
