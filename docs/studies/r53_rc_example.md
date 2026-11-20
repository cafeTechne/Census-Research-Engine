# Round 53 exploratory example: county child poverty on income and unemployment, corrected slopes

**Status: exploratory example, not a registered study. Author self-review, not independent.**

**Inputs.** `scripts/r53_rc_example.py` reads cached 2024 five-year county API responses for MI and NY
(read-only; the tables were fetched with the owner's key for this round):
- **B17001:** children under 18 below poverty, out of all children with poverty status;
- **B19013:** median household income;
- **B23025:** unemployed share of the civilian labour force (`derived.proportion`).

There are 145 counties. Outputs are archived at `/tmp/r53_example_outputs.tar.gz` (sha256
`fe2df245…2a19a716`).

**Model.** A binomial model of the county child poverty rate. Covariates are log median household income and
the unemployment rate, both carrying ACS sampling error, plus a NY indicator. Weights are the number of
children. Three fits:
- a naive binomial GLM with HC3 SEs;
- regression calibration (RC) with the bootstrap SE: exploratory for binomial since Round 46;
- RC with the delete-one-area jackknife SE: validated for binomial in Round 53.

Round 46 dropped this example because binomial RC had failed.

## Results (90% intervals)

| Fit | Log income | Unemployment (per point) | Validated |
| :--- | :--- | :--- | :--- |
| Naive, HC3 | −1.117 (−1.745 to −0.488) | 0.127 (0.027 to 0.228) | naive (attenuated) |
| RC, bootstrap SE | −1.108 (−1.567 to −0.648) | 0.134 (0.064 to 0.204) | no (Round 46) |
| RC, jackknife SE | −1.108 (−1.764 to −0.451) | 0.134 (0.028 to 0.240) | yes (Round 53) |

Estimated reliability ratios: log income .98, unemployment .78.

## Findings

- **Correction size.** Calibration raises the unemployment slope by 5%, a modest change at reliability .78.
  Income is measured almost without error at county level, and its slope barely moves.
- **SE widths.** On these real counties the jackknife SEs are about 40–50% larger than the bootstrap SEs: .397
  against .280 for income, and .064 against .043 for unemployment. That matches the Round 53 explanation: the
  row bootstrap behaves like HC0 and under-states uncertainty when a few large-trial counties have high leverage.
  The bootstrap interval for unemployment (.064–.204) would overstate precision. The validated jackknife
  interval (.028–.240) is close to the naive HC3 width.
- Both associations keep their sign and exclude zero in the validated fit: higher income goes with lower child
  poverty, and higher unemployment with higher child poverty. This is cross-sectional and descriptive.

## Limits

- Independent areas are assumed. The spatial alternative, calibration with IM-8 clusters, is validated for
  Poisson and NB2 counts only, not binomial.
- Two error-prone covariates; ACS error correlations between them are not modelled, since the calibration uses
  each covariate's own SE.
- Child poverty is the ACS's own measure, so the circularity rule is respected.
