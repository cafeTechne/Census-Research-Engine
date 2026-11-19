# Round 49 exploratory example: disability, poverty, insurance and earnings with survey-weighted PUMS models

**Status: exploratory example, not a registered study. Author self-review, not independent.**

**Inputs.** `scripts/r49_pums_models_example.py` reads the cached Michigan 2019–2023 five-year PUMS
person file (`census.pums.fetch_pums`, public, no API key) with HTTP blocked. The universe is adults
aged 25–64. Only coefficients are written (no microdata). The outputs are archived at
`/tmp/r49_example_outputs.tar.gz` (sha256 `035837b8…59c44656`).

**Variables.**
- Disabled: `DIS = 1`.
- Age in decades from 45: `(AGEP − 45) / 10`.
- Poverty band from `POVPIP`: 0 = below 100%, 1 = 100–199%, 2 = 200–399%, 3 = 400% or more. People
  with no poverty status, mainly those in group quarters, are left out.
- Uninsured: `HICOV = 2`.
- Log earnings: `log(PERNP)`, for people with positive earnings only.

Every interval is a 90% interval from the 80 replicate-weight refits, the method validated in Round 49.

| Model | Records (weighted) | Disabled | Age (per decade) |
| :--- | :--- | :--- | :--- |
| Poverty band, ordered logit | 244,125 (5.09 M) | −1.303 (−1.331, −1.275) | 0.210 (0.201, 0.218) |
| Poverty band, ordered probit | 244,125 (5.09 M) | −0.767 (−0.783, −0.751) | 0.122 (0.117, 0.127) |
| Uninsured, probit | 249,427 (5.15 M) | −0.060 (−0.084, −0.035) | −0.124 (−0.132, −0.115) |
| Log earnings, median regression | 191,811 (4.06 M) | −0.445 (−0.470, −0.421) | 0.092 (0.086, 0.097) |

**Reading the results.**
- **Poverty band.** Disability shifts working-age adults toward lower income-to-poverty bands. In the
  logit, the odds of being above any band cut-off are 0.27 times as large with a disability
  (exp(−1.303)). The probit gives the same ordering, and the ratio of its slopes to the logit's (0.59)
  is the usual ratio of the two scales.
- **Insurance.** Disabled adults are slightly *less* often uninsured. This is consistent with
  disability-linked Medicaid and Medicare coverage, but the model cannot establish that cause.
- **Earnings.** Among earners, the median of earnings is about 36% lower with a disability
  (exp(−0.445) = 0.64), holding age fixed.

**Limits.**
- These are cross-sectional associations, adjusted only for age; they are not causal effects.
- The intervals reflect ACS sampling only.
- Disability status in the ACS is self-reported over six functional domains.

The validation (`docs/audits/pums_models_validation.md`) shows why the replicate intervals matter.
Model-based SEs, which ignore household clustering and unequal weights, covered only .62–.887 where the
replicate intervals covered .875–.915.
