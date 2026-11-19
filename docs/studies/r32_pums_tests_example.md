# Round 32 example: disability, insurance, poverty and earnings in Michigan PUMS (exploratory)

**Exploratory; author self-review, not independent. Not registered.** The example shows that the
Round 32 PUMS procedures work as intended on real microdata; it is not a confirmatory finding.

## Data

- Michigan ACS 2019–2023 5-year PUMS person file (503,042 records; public file
  `csv_pmi.zip`, SHA-256 `d15e7caf…166b`), with the person weight and its 80 replicate weights.
  2019–2023 is used instead of 2018–2022 because it codes every record to the 2020 PUMAs (the
  2018–2022 file splits PUMA10/PUMA20).
- Disability: `DIS`. Insurance type from `PRIVCOV`/`PUBCOV`: private only, public only, both,
  none. Poverty: `POVPIP` < 100. Earnings: `PERNP`.
- Reproduce: `scripts/r32_pums_tests_example.py CACHE_DIR OUT_DIR`. Outputs (results only, no
  microdata): `r32_example_outputs.tar.gz`, key-scanned, attached to the release.

## Results (adults 19–64 unless stated; 90% intervals)

**Insurance type by disability** (282,432 records; first-order Rao–Scott, validated):

| | With a disability | Without |
| :--- | ---: | ---: |
| Public only | 49.4% | 14.9% |
| Private only | 32.5% | 74.1% |
| Both | 11.8% | 3.2% |
| None (uninsured) | 6.3% | 7.9% |

Rao–Scott X²/δ̄ = 10,416 on 3 df, p < 10⁻¹⁵. The mean design effect is 3.15: the design-blind
Pearson statistic overstates the evidence about threefold, which matters for smaller samples.

**Poverty by disability** (validated): 16.5 percentage points higher with a disability
(15.9 to 17.2); odds ratio 3.15 (3.04–3.26); relative risk 2.57 (2.50–2.64).

**Earnings by disability**, ages 25–64 with earnings:

- Means (validated): $40,356 with a disability vs $59,948 without; difference $19,592
  ($18,689–$20,494); z = 35.7.
- Medians: difference $15,000, but its replicate standard error is exactly 0. Reported earnings are
  heaped at round numbers (3.5% of one group's weight sits exactly at its median), so every
  replicate median is the same value. The engine labels this **exploratory**: the validation used
  continuous values. Use bracket-interpolated medians or compare means instead. This limitation
  was found by this example and is now detected automatically (`heaping_share`).

**Uninsured among disabled adults in a small PUMA** (PUMA 02702; 218 records):

| Interval | Estimate | 90% interval |
| :--- | ---: | :--- |
| Korn–Graubard (validated) | 4.5% | 1.9%–8.8% |
| Wald (failed validation; exploratory) | 4.5% | 1.5%–7.5% |

The Wald interval is narrower and symmetric; for rare outcomes in small domains it under-covered
in validation, and Korn–Graubard did not.

## Limits

- Exploratory and descriptive: no adjustment for age or other differences between groups.
- PUMS records are a sample of persons; these are population-level associations, not causal
  effects. Disability, insurance and income are self- or household-reported.
- Medians of heaped dollar amounts need bracket interpolation (above).
