# Area-inequality validation

Conservative nominal 90% coverage >= 0.86 for all three statistics in all four cells with rank CV <= 0.15. CV 0.30 is informational.

Criterion commit: `60330e3`.

Result: **PASS**.

Invalid/undefined draws count as non-coverage. No seeds, designs or criteria were changed.

| n | Rank CV | Statistic | Conservative coverage | Population coverage | Bias | Mean total SE / SD | Mean model SE / SD |
|---:|---:|:---|---:|---:|---:|---:|---:|
| 145 | 5% | sii | 0.905 | 0.905 | -7.50038e-05 | 1.026 | 1.019 |
| 145 | 5% | log_rii | 0.900 | 0.898 | -0.00072066 | 1.024 | 1.017 |
| 145 | 5% | concentration_index | 0.903 | 0.899 | -0.000158151 | 1.034 | 1.027 |
| 145 | 15% | sii | 0.887 | 0.851 | -0.00168167 | 1.072 | 0.988 |
| 145 | 15% | log_rii | 0.888 | 0.858 | -0.019991 | 1.078 | 0.993 |
| 145 | 15% | concentration_index | 0.891 | 0.862 | -0.00327636 | 1.087 | 1.003 |
| 145 | 30% | sii | 0.823 | 0.673 | -0.00616878 | 1.324 | 1.007 |
| 145 | 30% | log_rii | 0.821 | 0.672 | -0.0743214 | 1.330 | 1.014 |
| 145 | 30% | concentration_index | 0.824 | 0.672 | -0.0121082 | 1.328 | 1.010 |
| 1000 | 5% | sii | 0.902 | 0.898 | -0.000321072 | 1.001 | 0.993 |
| 1000 | 5% | log_rii | 0.900 | 0.898 | -0.00369587 | 0.995 | 0.988 |
| 1000 | 5% | concentration_index | 0.902 | 0.898 | -0.000615531 | 0.999 | 0.992 |
| 1000 | 15% | sii | 0.876 | 0.848 | -0.00168542 | 1.069 | 0.979 |
| 1000 | 15% | log_rii | 0.876 | 0.843 | -0.0203575 | 1.073 | 0.981 |
| 1000 | 15% | concentration_index | 0.877 | 0.848 | -0.00331259 | 1.075 | 0.984 |
| 1000 | 30% | sii | 0.644 | 0.425 | -0.00586134 | 1.364 | 1.013 |
| 1000 | 30% | log_rii | 0.638 | 0.421 | -0.0705843 | 1.360 | 1.011 |
| 1000 | 30% | concentration_index | 0.641 | 0.421 | -0.011481 | 1.359 | 1.009 |

Design: 1,000 draws per cell, fixed area weights and true ranks, independent areas; all invalid-draw counts are in the JSON.
Validated range, if passed: median rank CV <=15%. CV 30% is informational; HC3/conservative intervals do not correct rank-error attenuation.
Positive indices mean higher outcomes among more deprived areas. Concentration has the reverse sign of the usual income-ranked convention.
