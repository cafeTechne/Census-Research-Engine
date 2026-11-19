# Round 37 example: ACS county population vs Census population estimates (exploratory)

**Exploratory; author self-review, not independent. Not registered.**

Data: 145 MI/NY counties. Source A: ACS 2018–2022 total population (B01003, with replicates; v0.26.0
attachment). Source B: the Census Bureau's population estimates in the owner's WONDER county export,
summed over 2018–2022 and divided by five. Population figures only; no death counts. Compared on the
log scale (differences are proportional). Reproduce:
`scripts/r37_agreement_example.py r29_study_outputs.tar.gz all_causes.tsv OUT_DIR`.

| Quantity | Estimate | 90% interval | Status |
| :--- | ---: | :--- | :--- |
| Bias (estimates − ACS) | −0.53% | −0.76% to −0.31% | validated |
| Kappa, quintile classes | 0.98 | 0.96 to 1.00 | validated |
| Limits of agreement | −3.2% to +2.2% | | interval exploratory |
| Lin's concordance | 0.9999 | | interval exploratory |

- The sources agree closely: ACS county totals are controlled to the population estimates, so their
  replicate SEs are near zero and the "error-free" limits equal the observed ones. The small average
  gap (0.5%) fits the different estimate vintages that WONDER and the ACS weighting use.
- The largest county gaps are where group quarters matter: Hamilton, NY (estimates 8% below the ACS),
  Luce, MI (7% above; prisons), Mecosta and Isabella, MI (5% and 4% above; universities) and
  Jefferson, NY (4% below; Fort Drum).
- For mortality rates in such counties the choice of denominator changes the rate by a few percent.

Limits: exploratory; areas treated as independent.
