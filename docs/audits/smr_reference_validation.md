# Round 28 SMR reference-rate uncertainty validation

Combined nominal 90% true-SMR coverage >= .86 in all six cells with the Poisson reference term. Zeros and invalid draws count as noncoverage; no-reference coverage informational.

Criterion commit: `134bf7f`. Passed: **True**.

| Reference deaths/band | E | With reference uncertainty | Without reference uncertainty | Invalid | O=0 |
| :-- | :-- | :-- | :-- | :-- | :-- |
| 50 | 10 | 0.9105 | 0.8830 | 0 | 0 |
| 50 | 100 | 0.9010 | 0.7240 | 0 | 0 |
| 500 | 10 | 0.9090 | 0.9070 | 0 | 0 |
| 500 | 100 | 0.8995 | 0.8830 | 0 | 0 |
| 5000 | 10 | 0.9050 | 0.9050 | 0 | 0 |
| 5000 | 100 | 0.9020 | 0.9000 | 0 | 0 |

2,000 draws/cell; true SMR 1.2, five independent bands; fixed true rates (.0005,.001,.003,.01,.04) per person-year; five-year study period. Each band has known reference person-years D/rate; its observed reference deaths are Poisson(D). Observed rates use those deaths divided by those known person-years. The delta term uses the observed reference deaths.

Gaussian ACS band errors CV .05 and 80 replicates, without clipping/redraws. Both coverage denominators include all draws. Reference denominators, spatial dependence and covariance with an internal reference were not simulated. Internal-standardization warnings are conditional because membership cannot be inferred from rates/counts alone. See the frozen criterion.
