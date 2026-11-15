# Robust GLM standard-error validation

Fixed design (follows the Round 22 A2 binomial cell at range 0): n=145 independent units, 2,000 simulations per cell, seed 20261115 + cell index. Lognormal denominators drawn once per cell (median 3900, log-SD 1, minimum 50). Linear predictor -2.6 + 0.3x + u, x ~ N(0,1), u ~ N(0, sd_u^2) (between-area variation that does not shrink with the denominator). Binomial: logit link, denominators as trials. Poisson: log link, denominators as exposure. 90% normal Wald intervals.

Estimator under test: the shipped `census.models.glm_robust_covariance` (HC3), used by `fit_replicate(scale='robust')`. Comparators: HC0 with the n/(n-k) factor, Pearson X2.

**Pre-set acceptance** (committed before the first run): HC3 coverage >= 0.86 in all four cells. **PASSED**.

Scope: units independent. Spatial dependence is not covered (Round 22 A2 Conley test failed).

| Model | sd_u | Estimator | Coverage | MC SE | Mean SE / empirical SD | Failed |
| :--- | ---: | :--- | ---: | ---: | ---: | ---: |
| binomial | 0.0 | HC3 | 0.8970 | 0.0068 | 1.0122 | 0 |
| binomial | 0.0 | HC0_nk | 0.8855 | 0.0071 | 0.9662 | 0 |
| binomial | 0.0 | X2 | 0.8990 | 0.0067 | 0.9896 | 0 |
| binomial | 0.15 | HC3 | 0.8925 | 0.0069 | 0.9906 | 0 |
| binomial | 0.15 | HC0_nk | 0.8695 | 0.0075 | 0.9286 | 0 |
| binomial | 0.15 | X2 | 0.7900 | 0.0091 | 0.7556 | 0 |
| binomial | 0.3 | HC3 | 0.8800 | 0.0073 | 0.9718 | 0 |
| binomial | 0.3 | HC0_nk | 0.8465 | 0.0081 | 0.8813 | 0 |
| binomial | 0.3 | X2 | 0.6970 | 0.0103 | 0.6270 | 0 |
| poisson | 0.15 | HC3 | 0.8790 | 0.0073 | 0.9787 | 0 |
| poisson | 0.15 | HC0_nk | 0.8425 | 0.0081 | 0.8738 | 0 |
| poisson | 0.15 | X2 | 0.6890 | 0.0104 | 0.6108 | 0 |

Reproduce: `OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/robust_se_validation.py`.
