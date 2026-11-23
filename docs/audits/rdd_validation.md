# Round 98: regression discontinuity

Criterion commit: `37d68c924766c84bf4f216da5adc544d76f076f7`. 2000 draws per cell; 90% intervals. Author self-review, not independent.

| Estimator | Outcome | Key value |
| :--- | :--- | ---: |
| R1 robust bias-corrected (continuous) | fail | lowest coverage 0.780 |
| R1-rep replicate SEs (discrete ages) | pass | lowest coverage 0.893 |
| D1 density test | fail | largest null rejection rate 0.114 |

## Continuous

| Shape | Jump | n | R1 robust | R0 conventional | D1 rejection | Failures |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| linear | 0.0 | 2,000 | 0.907 | 0.866 | 0.108 | 0.000 |
| linear | 0.0 | 10,000 | 0.903 | 0.861 | 0.099 | 0.000 |
| linear | 0.0 | 50,000 | 0.909 | 0.878 | 0.110 | 0.000 |
| linear | 0.2 | 2,000 | 0.912 | 0.872 | 0.099 | 0.000 |
| linear | 0.2 | 10,000 | 0.902 | 0.870 | 0.097 | 0.000 |
| linear | 0.2 | 50,000 | 0.903 | 0.870 | 0.107 | 0.000 |
| quadratic | 0.0 | 2,000 | 0.893 | 0.872 | 0.097 | 0.000 |
| quadratic | 0.0 | 10,000 | 0.915 | 0.875 | 0.103 | 0.000 |
| quadratic | 0.0 | 50,000 | 0.899 | 0.856 | 0.114 | 0.000 |
| quadratic | 0.2 | 2,000 | 0.894 | 0.870 | 0.102 | 0.000 |
| quadratic | 0.2 | 10,000 | 0.906 | 0.868 | 0.109 | 0.000 |
| quadratic | 0.2 | 50,000 | 0.906 | 0.879 | 0.102 | 0.000 |
| lee | 0.0 | 2,000 | 0.780 | 0.386 | 0.107 | 0.000 |
| lee | 0.0 | 10,000 | 0.791 | 0.303 | 0.103 | 0.000 |
| lee | 0.0 | 50,000 | 0.886 | 0.482 | 0.107 | 0.000 |
| lee | 0.2 | 2,000 | 0.787 | 0.383 | 0.105 | 0.000 |
| lee | 0.2 | 10,000 | 0.804 | 0.321 | 0.109 | 0.000 |
| lee | 0.2 | 50,000 | 0.893 | 0.493 | 0.110 | 0.000 |

## Discrete (ages 45-84, cutoff 65, survey weights)

| Design | Jump | R1-rep | R1-cluster | R1-hc | Failures |
| :--- | ---: | ---: | ---: | ---: | ---: |
| linear | 0.0 | 0.905 | 0.709 | 0.905 | 0.000 |
| linear | 0.05 | 0.897 | 0.703 | 0.897 | 0.000 |
| quadratic | 0.0 | 0.906 | 0.706 | 0.909 | 0.000 |
| quadratic | 0.05 | 0.893 | 0.697 | 0.901 | 0.000 |
| fuzzy | 0.15 | 0.898 | 0.688 | 0.902 | 0.000 |
