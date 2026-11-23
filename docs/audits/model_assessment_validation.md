# Round 97: spatial block cross-validation and MAUP sensitivity

Criterion commit: `36671c15485748f60b079898841034af012ab3a1`. 500 draws per cell (CV), 200 (MAUP). Author self-review, not independent.

**V1 (5 spatial blocks): fail.**

| Residual range (km) | True RMSE (new region) | V1 RMSE ratio | V1-10 ratio | V0 random ratio | True coverage | V1 coverage | V0 coverage |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 1.223 | 1.000 | 0.999 | 1.000 | 0.898 | 0.899 | 0.899 |
| 20 | 1.086 | 0.775 | 0.706 | 0.568 | 0.657 | 0.778 | 0.898 |
| 50 | 0.866 | 0.809 | 0.755 | 0.668 | 0.733 | 0.826 | 0.899 |

## MAUP: zone-level slope / tract-level slope (random contiguous zonings of about 10 tracts)

| Residual range (km) | Mean ratio | SD across zonings | 5th-95th percentile |
| ---: | ---: | ---: | :--- |
| 0 | 0.980 | 0.064 | 0.783-1.167 |
| 20 | 0.872 | 0.066 | -0.211-1.449 |
| 50 | 0.929 | 0.051 | 0.231-1.334 |
