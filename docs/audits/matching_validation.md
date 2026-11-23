# Round 99: matching estimators and triple differences

Criterion commit: `0e75ba5d21233b616065f96c37c407aa53db9683`. 2000 draws per cell; 90% intervals. Author self-review, not independent.

| Estimator | Outcome | Lowest coverage |
| :--- | :--- | ---: |
| M1-ATT | fail | 0.852 |
| M1-ATE | pass | 0.861 |
| M2 | pass | 0.951 |
| M3 | pass | 0.962 |
| T3 | pass | 0.980 |

| N | Propensity strength | Heterogeneous | M1-ATT | M1-ATE | M2 (CEM) | M3 (PS) | CEM share matched | Failures |
| ---: | ---: | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| 145 | 0.5 | False | 0.895 | 0.889 | 0.955 | 0.988 | 0.92 | 0.000 |
| 145 | 0.5 | True | 0.896 | 0.877 | 0.967 | 0.987 | 0.92 | 0.000 |
| 145 | 1.502 | False | 0.852 | 0.877 | 0.951 | 0.970 | 0.78 | 0.000 |
| 145 | 1.502 | True | 0.858 | 0.861 | 0.973 | 0.969 | 0.79 | 0.000 |
| 600 | 0.5 | False | 0.889 | 0.896 | 0.960 | 0.987 | 1.00 | 0.000 |
| 600 | 0.5 | True | 0.914 | 0.903 | 0.974 | 0.993 | 1.00 | 0.000 |
| 600 | 1.502 | False | 0.880 | 0.896 | 0.952 | 0.969 | 0.95 | 0.000 |
| 600 | 1.502 | True | 0.890 | 0.882 | 0.961 | 0.962 | 0.95 | 0.000 |

| tau | delta (treated-unit trend) | T3 coverage | T3 bias | D2 (group A DiD) coverage | D2 bias |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0.0 | 0.0 | 0.981 | 0.006 | 0.907 | 0.001 |
| 0.0 | 0.3 | 0.983 | -0.005 | 0.000 | 1.502 |
| -2.0 | 0.0 | 0.986 | 0.003 | 0.920 | -0.000 |
| -2.0 | 0.3 | 0.980 | -0.007 | 0.000 | 1.496 |
