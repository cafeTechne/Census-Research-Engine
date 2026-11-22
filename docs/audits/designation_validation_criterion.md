# Round 85 criterion: area designations as screening tests

Committed before the full run. Author self-review, not independent. Frozen with `validate_pins`:
- `scripts/designation_validation.py`;
- `census/designation_core.py` (new);
- Round 80's `census/sae_extensions_core.py` and `docs/audits/sae_extensions_neff.csv.gz` (unchanged);
- this file.

**Seen before this commit:** one smoke run (4 draws per cell), which only checked that the script runs.

## Methods (`census/designation_core.py`)

- **Q1a: flat-prior probability that an area truly exceeds the threshold.** Computed from the direct estimate on
  the arcsine scale, with sampling variance 1/(4 n_eff).
- **Q1b: the Fay–Herriot posterior probability.** Uses the Round 80 arcsine model with a covariate and the
  g1 + g2 MSE.
- **Q2: expected accuracy of a designation rule.** Expected true and false positives, sensitivity, specificity, PPV
  and NPV from the Q1 probabilities, with a normal predictive interval for the realized PPV.
  - Rules: point estimate ≥ t; lower 90% bound ≥ t; probability ≥ .5; probability ≥ .8.
- **Q3: expected overlap of the estimated top k with the true top k.** Reported only.

## Design (9 cells × 1,000 draws)

- **Geometries:** MI tracts (2,868), NY tracts (5,176), MI+NY counties (145), with real effective sample sizes.
- **Truth:** a Fay–Herriot arcsine generator: covariate slope .1, area SD .10, binomial direct estimates.
- **Thresholds:** set so that 10%, 25% or 50% of areas truly qualify.

## Pass rules (judged per probability source)

- **Calibration (Q1a, Q1b):** in every decile bin holding ≥ 200 area-draws, the realized share of truly
  qualifying areas is within ±.05 of the mean predicted probability, in every cell.
- **Accuracy (Q2a, Q2b):** for every rule, in every cell:
  - the mean predicted and mean realized sensitivity, specificity, PPV and NPV agree within ±.05;
  - the 90% predictive interval of the realized PPV covers it in ≥ 86% of draws.

Seeds: `[20282501, cell]` for setup; `[20282511 + cell, draw]` for draws.

## Engine (only what passes)

- **Tool `designation_accuracy`** (full profile). Its default probability source is whichever of Q1a/Q1b passed
  (Q1b preferred).
- **Recipe:** a `small_area` section "Designating areas".
