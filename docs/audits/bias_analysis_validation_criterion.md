# Round 86 criterion: quantitative bias analysis

Committed before the full run. Author self-review, not independent. Frozen with `validate_pins`:
- `scripts/bias_analysis_validation.py`;
- `census/bias_analysis_core.py` (new);
- this file.

**Seen before this commit:**
- one smoke run (4 draws per cell), which only checked that the script runs;
- E-values for VanderWeele and Ding's (2017) example (RR 3.9, CI 1.8–8.7): 7.26 and 3.00, as published;
- a check that the simple correction with the true sensitivity and specificity is unbiased: median corrected RR
  2.006, 2.002 and 1.986 for the three kinds over 2,000 draws, true value 2.0.

## Methods (`census/bias_analysis_core.py`)

- **E1: E-values.** Deterministic; checked in tests against the published example. The plan's EValue R-package
  fixtures were not available (R is not installed). The published examples and the formula identities replace them.
- **M1: misclassification correction.**
  - Simple correction for outcome or exposure misclassification, differential or not.
  - Probabilistic analysis (Lash, Fox and MacLehose): beta priors on sensitivity and specificity; impossible
    corrections discarded; conventional random error added; 90% total-error interval.
- **B1: both-directions report.** No inference, so not validated.

## Design (12 cells × 1,000 draws, 5,000 simulations per draw)

- **Kinds:**
  - outcome misclassification, nondifferential (Se .85, Sp .95);
  - outcome misclassification, differential (exposed .90/.97, unexposed .80/.93);
  - exposure misclassification, nondifferential (.85/.95).
- **Crossed with:**
  - true RR 1.0 or 2.0 (unexposed risk .10, 2,000 per group);
  - prior: correct (centred on the truth, SD .02) or offset (Se lowered by .05, Sp by .02).
  - **Deviation from the plan, made before any run:** the offset is applied downward, and by .02 for Sp, because
    Sp + .05 would exceed 1.

## Pass rule

- **P1:** coverage of the true RR and the true OR ≥ .86 in every correct-prior cell.
- **Reported only:** offset-prior coverage, and the coverage of the uncorrected interval.

Seeds: `[20282601 + cell, draw]`.

## Engine (only what passes)

- **Tool `bias_analysis`** (full profile): `kind="e_value"` (always available) and `kind="misclassification"`.
  - The probabilistic interval is validated if P1 passes; the simple correction is a point correction.
- **E-value fields** on the outputs of stratified analysis, marginal RR and PUMS two-by-two.
- **Recipe:** a `reporting` section.
