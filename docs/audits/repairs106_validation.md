# Round 106: third-wave exploratory-measure repairs validation

Elapsed: 62.3s. Frozen SHA-256: `{'census/repairs106_core.py': 'e6ea2508aa22850d', 'scripts/repairs106_validation.py': '424184beee87466a', 'docs/audits/repairs106_criterion.md': '31f61102be45222b'}`. 90% intervals (pass ≥ .86; H2c size ≤ .13). Author self-review, not independent.

## Outcomes

| Candidate | Outcome |
| :--- | :--- |
| `H2c_all` | fail |
| `Q2c_all` | fail |
| `E3_all` | fail |
| `C2_all` | **pass** |
| `M5_all` | **pass** |

## PUMS replicate Wald homogeneity (H2c: Hotelling F, exact per-measure nulls)

| Measure | K | n/stratum | Size (.10) |
| :--- | ---: | ---: | ---: |
| rr | 3 | 300 | 0.123 |
| rr | 3 | 1000 | 0.109 |
| rr | 5 | 300 | 0.119 |
| rr | 5 | 1000 | 0.113 |
| or | 3 | 300 | 0.122 |
| or | 3 | 1000 | 0.112 |
| or | 5 | 300 | 0.119 |
| or | 5 | 1000 | 0.124 |
| rd | 3 | 300 | 0.103 |
| rd | 3 | 1000 | 0.105 |
| rd | 5 | 300 | 0.131 |
| rd | 5 | 1000 | 0.126 |

## Designation PPV predictive interval (Q2c: FH bootstrap with rule re-selection)

| N | A | Rule | Q2c coverage |
| ---: | ---: | :--- | ---: |
| 200 | 0.005 | point | 0.868 |
| 200 | 0.005 | prob80 | 0.897 |
| 200 | 0.02 | point | 0.865 |
| 200 | 0.02 | prob80 | 0.880 |
| 1000 | 0.005 | point | 0.880 |
| 1000 | 0.005 | prob80 | 0.868 |
| 1000 | 0.02 | point | 0.850 |
| 1000 | 0.02 | prob80 | 0.895 |

## Ecologic / between-area slope (E3: Croon/Fuller reliability correction)

| J | n_j | beta_b | E3 coverage | Naive OLS coverage |
| ---: | ---: | ---: | ---: | ---: |
| 150 | 20 | 0.0 | 0.810 | 0.811 |
| 150 | 20 | 1.0 | 0.825 | 0.504 |
| 150 | 40 | 0.0 | 0.883 | 0.881 |
| 150 | 40 | 1.0 | 0.888 | 0.785 |

## Lin's CCC (C2: Fisher-z jackknife)

| n | True CCC | Shift | Scale | C2 coverage |
| ---: | ---: | ---: | ---: | ---: |
| 50 | 0.569 | 0.3 | 1.2 | 0.901 |
| 50 | 0.88 | 0.2 | 1.1 | 0.886 |
| 50 | 0.974 | 0.1 | 1.05 | 0.889 |
| 145 | 0.569 | 0.3 | 1.2 | 0.895 |
| 145 | 0.88 | 0.2 | 1.1 | 0.890 |
| 145 | 0.974 | 0.1 | 1.05 | 0.900 |

## Parametric g-formula (M5: Hernán & Robins ch. 21 + cluster jackknife)

| K | Feedback | psi | M5 cov (d1/d2/d3) | M5 bias (d1/d2/d3) |
| ---: | ---: | ---: | :--- | :--- |
| 12 | 0.0 | 0.0 | 0.888/0.901/0.904 | -0.004/-0.008/-0.010 |
| 12 | 0.0 | -2.0 | 0.888/0.898/0.897 | +0.000/+0.002/+0.003 |
| 12 | 0.5 | 0.0 | 0.909/0.916/0.906 | +0.000/+0.004/+0.002 |
| 12 | 0.5 | -2.0 | 0.890/0.883/0.889 | +0.001/+0.004/+0.002 |
| 12 | 1.0 | 0.0 | 0.907/0.912/0.907 | -0.007/+0.001/-0.003 |
| 12 | 1.0 | -2.0 | 0.895/0.891/0.888 | +0.022/+0.035/+0.033 |
| 18 | 0.0 | 0.0 | 0.901/0.894/0.890 | -0.004/-0.004/-0.004 |
| 18 | 0.0 | -2.0 | 0.912/0.916/0.913 | +0.007/+0.008/+0.009 |
| 18 | 0.5 | 0.0 | 0.911/0.907/0.908 | -0.003/+0.003/+0.003 |
| 18 | 0.5 | -2.0 | 0.902/0.896/0.891 | +0.005/+0.010/+0.010 |
| 18 | 1.0 | 0.0 | 0.920/0.918/0.916 | +0.010/+0.015/+0.013 |
| 18 | 1.0 | -2.0 | 0.884/0.883/0.884 | +0.006/+0.014/+0.013 |
