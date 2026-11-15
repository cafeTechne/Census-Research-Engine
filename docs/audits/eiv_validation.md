# fit_eiv simulation validation

Generated 2026-11-15 01:55 UTC by `scripts/eiv_validation.py` (500 simulated data sets per cell, n = 800 units, 1646 s). PLAN_ROUND_20 A2.

Design: y = 1 + 2x + 0.5g + N(0, 4); published estimates x + u, y + v with heteroscedastic sampling errors and corr(u, v) = rho; synthetic replicates whose VRE variance formula reproduces the error variances. Coefficient of x, true value 2. Regression calibration (`rc`) knows the covariate's SE but not the outcome-covariate error correlation.

| Reliability | rho | Naive bias | RC bias | fit_eiv bias | fit_eiv SD | fit_eiv mean SE | fit_eiv 90% coverage | RC 90% coverage |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.95 | +0.0 | -0.0967 | +0.0037 | +0.0041 | 0.0385 | 0.0385 | 0.904 | 0.904 |
| 0.95 | +0.5 | -0.0276 | +0.0761 | +0.0031 | 0.0331 | 0.0328 | 0.906 | 0.244 |
| 0.95 | -0.5 | -0.1664 | -0.0693 | +0.0044 | 0.0431 | 0.0436 | 0.920 | 0.508 |
| 0.8 | +0.0 | -0.3974 | +0.0043 | +0.0065 | 0.0594 | 0.0587 | 0.910 | 0.920 |
| 0.8 | +0.5 | -0.2698 | +0.1601 | +0.0051 | 0.0482 | 0.0471 | 0.888 | 0.044 |
| 0.8 | -0.5 | -0.5254 | -0.1519 | +0.0074 | 0.0693 | 0.0689 | 0.914 | 0.222 |
| 0.6 | +0.0 | -0.7985 | +0.0068 | +0.0129 | 0.1065 | 0.1046 | 0.906 | 0.906 |
| 0.6 | +0.5 | -0.6420 | +0.2552 | +0.0107 | 0.0897 | 0.0876 | 0.904 | 0.080 |
| 0.6 | -0.5 | -0.9552 | -0.2421 | +0.0147 | 0.1218 | 0.1201 | 0.906 | 0.212 |

Monte Carlo 90% band for a true coverage of 0.90 with 500 simulations: +/- 0.022.

**Acceptance** (reliability >= 0.8: fit_eiv |bias| < 10% of the naive bias, coverage 0.87-0.93): **PASSED**.

Reading: naive OLS is biased by attenuation and, when the outcome's and the covariate's sampling errors are correlated, by that correlation too (negative rho adds to the attenuation, positive rho offsets it). Regression calibration removes the attenuation but not the correlated-error term. fit_eiv removes both. At reliability 0.6 the correction still removes the bias but its variance grows.
