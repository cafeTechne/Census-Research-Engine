# Round 27: natural splines and joint Wald validation

Nominal .10 conservative joint-Wald size within [.07,.13] in all eight cells; power is informational.

Pre-run criterion: `376ce69`. Passed: **False**.

| Model | Spline df | x CV | Null size | Power | Null failures |
| :-- | :-- | :-- | :-- | :-- | :-- |
| linear | 3 | 0.0 | 0.1370 | 0.6090 | 0 |
| linear | 3 | 0.15 | 0.1245 | 0.5745 | 0 |
| linear | 5 | 0.0 | 0.1510 | 0.5545 | 0 |
| linear | 5 | 0.15 | 0.1055 | 0.4915 | 0 |
| binomial | 3 | 0.0 | 0.1405 | 0.8525 | 0 |
| binomial | 3 | 0.15 | 0.1130 | 0.8095 | 0 |
| binomial | 5 | 0.0 | 0.1825 | 0.8015 | 0 |
| binomial | 5 | 0.15 | 0.1135 | 0.7490 | 0 |

2,000 draws/cell, n=145, nominal .10; centered natural splines with df 3/5, full-sample quantile knots frozen in every replicate. HC3 plus 4/80 times the uncentered replicate-deviation outer products; chi-squared reference. Power is informational at .3 sin(x). Independent areas, fixed binomial trials, constant-scale x sampling SE .15 on the standardized scale; no spatial or reference-rate uncertainty is asserted.

WLS, Poisson, df=4 and categorical multi-column terms are supported computationally but not separately simulation-validated by these cells. See the frozen criterion for the complete DGP and failure convention.
