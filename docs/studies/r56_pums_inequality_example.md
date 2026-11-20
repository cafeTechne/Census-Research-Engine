# Round 56 exploratory example: earnings and income inequality by disability, Michigan PUMS 2019–2023

**Status: exploratory example, not a registered study. Author self-review, not independent.**

**Inputs.** `scripts/r56_pums_inequality_example.py` reads the cached public 2019–2023 five-year Michigan person
file (no API key; HTTP blocked) and runs `census.pums_inequality.pums_inequality` with person weights and the 80
SDR replicate weights. Only results are written. Outputs are archived at `/tmp/r56_example_outputs.tar.gz` (sha256
`f7a96b2e…c17693fb`).

## Earnings (PERNP) of people aged 25–64 with positive earnings (191,811 records)

| Measure | Estimate (90% interval) | Validated |
| :--- | :--- | :--- |
| Gini | 0.451 (0.449–0.453) | yes |
| Gini, with a disability (DIS = 1; 14,067 records) | 0.501 (0.493–0.509) | yes |
| Gini, without (DIS = 2; 177,744 records) | 0.445 (0.443–0.447) | yes |
| Gini difference, without minus with | −0.056 (−0.064 to −0.048) | yes |
| log P90/P10 | 2.398 (zero replicate spread) | no: heaped dollar amounts |
| Theil T | 0.378 (0.374–0.382) | no (failed validation) |
| Top-decile share | 0.329 (0.327–0.331) | no (failed validation) |

## Personal income (PINCP) of people aged 25+ (369,184 records; 27,511 with zero income)

| Measure | Estimate (90% interval) | Validated |
| :--- | :--- | :--- |
| Gini (zeros included) | 0.522 (0.520–0.524) | yes |
| log P90/P10 (positive incomes) | 2.383 (2.368–2.398) | yes |
| log P80/P20 (positive incomes) | 1.591 (1.577–1.604) | yes |

## Findings

- Earnings are more unequal among working-age Michigan residents with a disability. The validated Gini is .501
  against .445, a difference of .056 (.048–.064). This is descriptive: it mixes differences in hours, occupations
  and part-time work.
- The earnings P90/P10 ratio is exactly ln 11. Earnings are reported in round amounts, so every replicate puts
  the 10th and 90th percentiles on the same values and the replicate SE is zero. The engine flags the ratio as
  exploratory, as it does for heaped medians. The income ratios are less heaped and are validated.
- The validation's sample sizes (800–3,000 households) are far smaller than a state file, so intervals here are
  narrow. The SDR variance still carries the design.

## Limits

Person-level measures (no equivalence scale; household income needs the housing file, which is not cached).
Theil T, Atkinson and the top-decile share are reported but exploratory.
