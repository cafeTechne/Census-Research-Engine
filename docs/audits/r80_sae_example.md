# Round 80 example: small-area uninsured rates in Michigan (exploratory)

Author self-review, not independent. S2701 percent uninsured; covariate S1701 percent below poverty.

**Arcsine Fay-Herriot, 2868 MI tracts (2019-2023; tracts with a published 0% or 100% omitted):** median 90% interval width 4.70 points against 5.60 for the direct estimates; model variance 0.003958 (arcsine scale); median |estimate - direct| 0.51 points; validated.

**Rao-Yu temporal FH, 83 MI counties (2014-2018 and 2019-2023; latest release):** median interval width 1.57 points against 1.80 direct; rho 0.50, area variance 1.36, area-time variance 0.635. Counties have precise direct estimates, so the gain is small; the validation found the largest gains on tracts (10-24% MSE).

| Tract estimate quantile | Direct % | Arcsine FH % |
| :--- | ---: | ---: |
| 10% | 1.4 | 2.1 |
| 50% | 4.5 | 4.5 |
| 90% | 10.0 | 7.3 |
