# Round 102 plan: meta-analysis completeness (Harrer et al.)

**Goal.** Backlog N79 (Harrer, Cuijpers, Furukawa and Ebert, *Doing Meta-Analysis with R*, chapters 4–9; mapping in
`docs/literature/harrer_meta_analysis.md`). `combine_estimates` (Rounds 38, 48) pools with Paule–Mandel and
Hartung–Knapp. It reports a prediction interval that was never validated, and has no I² interval, influence
diagnostics, meta-regression or small-study test. Version 0.98.0. Branch `phase102/meta-analysis`. Validation first.

## 1. Methods (frozen core `census/meta_core.py`)

- **P1: prediction interval** for a new estimate: μ̂ ± t_{k−2} √(τ̂² + SE(μ̂)²) (Higgins, Thompson and Spiegelhalter
  2009), with Paule–Mandel or REML τ².
- **H1: I² and τ² confidence intervals** by the Q-profile method (Viechtbauer 2007).
- **REML τ²** as an option (Harrer's default for continuous outcomes).
- **D1: leave-one-out estimates** and Baujat-style contributions (descriptive).
- **R1: meta-regression** (weighted least squares with τ² by REML) with Knapp–Hartung SEs and permutation p-values
  (1,000 permutations). Refused below 10 estimates per covariate (book guidance), or labelled exploratory there.
- **E1: Egger regression test** for small-study effects, available only with K ≥ 10.

## 2. Validation (`scripts/meta_validation.py`)

- **Designs:** k ∈ {5, 10, 20, 40} estimates; τ² over a range of I² levels (0, 25, 50, 75%); within-study SEs varying
  tenfold.
- **Draws:** 4,000 per cell.
- **Pass:**
  - P1: coverage of a new study's true effect ≥ .86 in every cell with k ≥ 10. A failure below 10 is a gate.
  - H1: coverage ≥ .86 for τ².
  - R1: coefficient coverage ≥ .86 with k ≥ 10, and permutation p size ≤ .10.
  - E1: size ≤ .10 with K ≥ 10 under no small-study effect (power reported for a planted effect).

## 3. Engine

- **`combine_estimates`** gains `tau2="pm" | "reml"`, `moderators=`, `leave_one_out=True` and `small_study_test=True`.
  It reports the I² interval and the prediction interval with validation labels.
- **Recipe** `combine_estimates` sections; protocol rule; sources (Harrer et al. 2021; Viechtbauer 2007; Higgins et
  al. 2009; Egger et al. 1997).

## 4. Example and acceptance

- **Example (exploratory):** pooling the Round 29/44 state-level poverty–mortality associations across MI, NY, OH
  and PA, with a prediction interval for a new state and a meta-regression on state median income.
- STATUS, CHANGELOG, compatibility audit, tests, goldens, suite.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Core, script, criterion | done | tag `criterion-r102` |
| Results | H1 passes; P1, R1, E1 fail | `meta_validation.md` |
| Engine, recipe | done | `combine_estimates(moderators, leave_one_out, small_study_test)`; τ² interval |
| Example | done | `r102_meta_example.md` |
| Goldens, suite | see audit | `round102_compatibility.md` |
| Exceptions | 3 | see audit |
