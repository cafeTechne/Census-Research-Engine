# Round 84 criterion: marginal risk ratios and differences, prevalence ratios, attributable fractions, dose-response

Committed before the full run. Author self-review, not independent. Frozen with `validate_pins`:
- `scripts/epi_measures_validation.py`;
- `census/epi_measures_core.py` (new);
- Round 32's `scripts/pums_tests_validation.py` and `census/pums_tests.py`;
- Round 80's design file `docs/audits/sae_extensions_neff.csv.gz` (unchanged);
- this file.

**Seen before this commit:**
- one smoke run (4 draws per cell), which only checked that the script runs;
- one large-sample check: a single noiseless-binomial tract draw recovers RR 1.797 (target 1.800), RD .084 and PAF
  .298;
- the reference targets for one PUMS design;
- one timing probe (0.2 s per PUMS draw).

## Methods (`census/epi_measures_core.py`)

- **G1: marginal RR and RD by g-computation from a weighted logistic model.**
  - Area version (G1a): HC3 delta-method SEs (population target).
  - PUMS version (G1p): SDR replicate SEs.
- **F1: PAF = 1 − r(reference) / r(observed).** The interval is computed on log(1 − PAF).
- **P1: prevalence ratio from a weighted modified-Poisson fit**, with SDR SEs.
  - P1b: the design-blind robust SE, reported only.
- **D1: dose-response.** A linear-contrast trend test on the marginal risks of ordered levels, plus a
  departure-from-linearity Wald test.

## Designs (2,000 draws per cell)

- **Area (18 cells).**
  - MI+NY counties or 1,000 MI tracts, with real effective sample sizes as trials.
  - Prevalence .05, .15 or .35 × marginal RR 1.0, 1.3 or 1.8.
  - A correlated confounder; beta-binomial overdispersion (ICC .01).
- **PUMS (24 cells).**
  - Round 32's sampling. Prevalence .05, .15 or .35 × 1,000 or 5,000 records.
  - Designs: binary exposure with or without an effect, and a three-level exposure null or linear.
  - Targets: the same estimators on a 300,000-household reference population.

## Pass rules

- **Coverage:** 90% coverage ≥ .86 in every cell for G1a RR, G1a RD, F1a PAF, G1p RR, G1p RD, F1p PAF and P1 PR.
- **Size:** D1 trend size at .10 within [.07, .13] in every null cell, judged separately for area and PUMS.
- **Gate:** a PUMS quantity that fails only at 1,000 records is validated from 5,000.
- **Reported only:** P1b and D1 power.

Seeds: `[20282401 + cell, draw]` for area; `[20282451 + cell, draw]` for PUMS; `[20282499, …]` for reference
populations.

## Engine (only what passes)

New options on existing tools:
- `fit_model(model="binomial", marginal=...)`, which also gives the attributable fraction;
- `pums_regression(report="marginal")` and `pums_regression(prevalence_ratio=True)`;
- `trend_test(kind="dose_response")`.

The common-outcome OR note is added. Manifest statistics follow if the area quantities pass.
