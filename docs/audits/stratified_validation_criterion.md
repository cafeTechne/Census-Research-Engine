# Round 83 criterion: stratified analysis, Mantel–Haenszel pooling and additive interaction

Committed before the full run. Author self-review, not independent. Frozen with `validate_pins`:
- `scripts/stratified_validation.py`;
- `census/stratified_core.py` (new);
- Round 32's `scripts/pums_tests_validation.py` and `census/pums_tests.py` (unchanged);
- this file.

**Seen before this commit:**
- one smoke run (20 draws per cell), which only checked that the script runs;
- an agreement check with statsmodels `StratifiedTable`: the MH OR and its 95% interval, the MH RR, and the
  Breslow–Day–Tarone statistic and p-value are identical on a random four-stratum table;
- one large-sample check (200,000 records) that the PUMS estimators recover their targets: RR 1.502, OR 1.81,
  RD .049, RERI .49.

## Methods (`census/stratified_core.py`)

- **MH1 (counts).**
  - Pooled RR, OR and RD with Greenland–Robins and Robins–Breslow–Greenland variances.
  - The pooled IRR for person-time.
  - Normal intervals, on the log scale for ratios.
- **MH2 (PUMS).** The same estimators on weighted cell totals, with SDR replicate SEs.
- **H1 (homogeneity).**
  - Counts: Breslow–Day with Tarone's correction (OR); a Woolf-type test (RR).
  - PUMS: a replicate Wald test that the stratum measures are equal.
- **A1 (additive interaction).** RERI, AP and S.
  - Counts: delta-method SE (A1), and a parametric binomial bootstrap percentile interval (A1b).
  - PUMS: SDR SE.
- **Classification (descriptive).** Book Table 8-5, with the 10% change rule. Not validated, because it is not a
  test.

## Designs (2,000 draws per cell)

- **Counts.** 3 stratum counts (2, 4, 8) × expected cases per stratum and arm (5, 20, 100) × five designs:
  - homogeneous RR, OR, RD or rate ratio (each with stratum-varying baseline risks);
  - heterogeneous RR (.7–2.5), for power.
- **RERI counts.** RERI 0 or .5 × baseline .05 or .20, with 2,000 persons per cell.
- **PUMS.** Round 32's sampling, with 2 or 4 strata (smallest stratum share .15) and 300 or 3,000 records in the
  smallest stratum, for homogeneous RR, OR and RD.
- **PUMS RERI.** RERI 0 or .5 × 3,000 or 10,000 records.

## Pass rules

- **Coverage:** 90% coverage ≥ .86 in every cell, for each of RR, OR, RD, IRR, RERI-delta, RERI-boot, MH2 RR/OR/RD
  and PUMS RERI.
- **Size:** H1 size at .10 in [.07, .13] in every homogeneous cell, for Woolf (homogeneous-RR cells), Breslow–Day
  (homogeneous-OR cells) and the PUMS Wald test.
- **Gates:**
  - a measure that fails only at E = 5 is validated for E ≥ 20;
  - a PUMS measure that fails only at 300 records is validated from 3,000.

Seeds: `[20282301 + cell, chunk]` for counts (RERI offset 100); `[20282351 + cell, draw]` for PUMS (RERI offset 100).

## Engine (only what passes)

- Tool `stratified_analysis` (full profile), with validated flags per measure and test.
- The classification label is shown with its inputs.
- Recipe `confounding_and_effect_modification`.
- Manifest `covariables` roles (mediators refused in formulas).
