# Round 94 WHO inequality monitoring measures: pre-set criterion

Frozen with `scripts/inequality_monitoring_validation.py` and `census/inequality_monitoring_core.py` before the full
run (tag `criterion-r94`). Author self-review, not independent.

## Design

This is the Round 76 ACS disparity design (`scripts/disparity_validation.py`), extended to 8 groups.

- **Rates.** R = (.10, .22, .30, .16, .35, .26, .12, .20)[:G], shares P = (.55, .15, .10, .07, .05, .04, .02, .02)[:G]
  normalised, with G ∈ {4, 6, 8}.
- **Spread.** "Large" uses R as given; "small" uses .2 + (R − .2)/4. Group 0 has the lowest rate in both, so it is the
  true best group.
- **Sampling error.** Rate CV_g = max(.05, c·√(min P / P_g)), with group 0 at .05 and c ∈ {.10, .30, .50}. Population
  CVs are half the rate CV.
- **Draws.** Gaussian-copula gamma draws with the Round 76 error correlations; 80 replicates from `make_replicates`.
- **Cross-sectional cells:** 18 (G × c × spread); 2,000 draws each.
- **Trend cells:** 8 (G ∈ {4, 8} × c ∈ {.10, .30} × change ∈ {0, .3}), large spread.
  - Release 2 rates are r̄ + (1 − change)(r_g − r̄).
  - The releases are independent draws; 2,000 draws each.
- **Target:** each measure on the true rates and shares, with the true best group (group 0).

## Families

Each has 90% replicate intervals.

| Family | Measures |
| :--- | :--- |
| MDM | mdm_u, mdm_w |
| MDB-declared | mdb_u, mdb_w with the declared reference group 0 |
| PAR-declared | par, par_pct with the declared reference group 0 |
| MDB-best | mdb_u, mdb_w with the data-selected best group, re-selected in each replicate |
| PAR-best | par, par_pct with the data-selected best group, re-selected in each replicate |
| SII | sii (informational; validated in Round 24) |
| T1 | Change between releases in mdm_w, mdb_w (declared), par (declared) and sii |

## Acceptance

- A family passes if every member's coverage is ≥ .86 in every cell of its design.
- **Range gate** (stated before the run): a family that fails only at c = .50 is validated for c ≤ .30.
- Failing families stay exploratory. The data-selected best is expected to suffer from selection bias when the
  spread is small.
