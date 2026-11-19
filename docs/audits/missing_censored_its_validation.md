# Missing data, censored counts and interrupted time series: validation (Round 42)

90% coverage >= .86 in every cell of the problem (ITS: level and slope change); failures count as non-coverage; D0, C0, A0 are comparisons.

Criterion commit: `5f81de2`. 2,000 draws per cell.

| Problem | Setting | Coverage | Failed draws |
| :--- | :--- | :--- | ---: |
| missing | MAR | D0 0.8710, D1 0.9070 | 0 |
| missing | MCAR | D0 0.9130, D1 0.9190 | 0 |
| censored | 10 | C0 0.8240, C1 0.8560 | 0 |
| censored | 30 | C0 0.8275, C1 0.8390 | 0 |
| its | 0.3 | A0_level 0.8145, A0_slope 0.7955, A1_level 0.6355, A1_slope 0.6030, A2_level 0.7855, A2_slope 0.7615 | 0 |
| its | 0.6 | A0_level 0.6890, A0_slope 0.5885, A1_level 0.5450, A1_slope 0.4655, A2_level 0.7305, A2_slope 0.6285 | 0 |

Outcomes: `{"A1": false, "A2": false, "C1": false, "D1": true}`.
