# Indirect SMR validation

Combined nominal 90% interval coverage >= 0.86 in all six cells. O=0 and invalid draws count as non-coverage.

Criterion commit: `680707e`.

Result: **PASS**.

| Expected | Band CV | Combined coverage | Fixed-E exact coverage | O=0 | Invalid |
|---:|---:|---:|---:|---:|---:|
| 10 | 5% | 0.909 | 0.925 | 0 | 0 |
| 10 | 20% | 0.903 | 0.881 | 0 | 0 |
| 50 | 5% | 0.893 | 0.890 | 0 | 0 |
| 50 | 20% | 0.906 | 0.735 | 0 | 1 |
| 500 | 5% | 0.897 | 0.776 | 0 | 0 |
| 500 | 20% | 0.905 | 0.335 | 0 | 0 |

2,000 draws per cell; true SMR 1.2, five equally populated bands scaled to the target expected count.
Gaussian population errors are not clipped/redrawn. Nonpositive/invalid populations or expected counts count as non-coverage.
Reference-rate uncertainty, correlated band errors and spatial dependence were not simulated; rates are treated as fixed.
