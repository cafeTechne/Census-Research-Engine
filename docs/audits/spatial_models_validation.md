# Round 93: GWR, classification, regionalization and diversity with ACS uncertainty

Criterion commit: `504c6c76cde25f01a2be5c155dc68bdb692a7915`. Wayne County tracts (625). Author self-review, not independent.

| Family | Outcome |
| :--- | :--- |
| R1 | fail |
| D1 | fail |
| D1bc | fail |

## R1 GWR (local slope, 90% robust intervals; 500 draws)

| Slope | Sampling error | Mean coverage | Areas >= .80 | Lowest area | Non-stationarity rejections | Bandwidth (km) |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| constant | low | 0.866 | 1.000 | 0.836 | 0.166 | 21.1 |
| constant | high | 0.894 | 1.000 | 0.870 | 0.116 | 21.1 |
| varying | low | 0.714 | 0.314 | 0.332 | 1.000 | 5.8 |
| varying | high | 0.707 | 0.323 | 0.404 | 1.000 | 7.7 |

## C1/C2 classification and regionalization (reported; 200 draws)

| Method | Sampling error | ARI | Mean stability | Share unstable (< .8) | Misclassified if unstable | Misclassified if stable |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| kmeans | low | 0.499 | 0.893 | 0.202 | 0.500 | 0.164 |
| kmeans | high | 0.387 | 0.766 | 0.454 | 0.472 | 0.155 |
| skater | low | 0.719 | 0.821 | 0.289 | 0.436 | 0.030 |
| skater | high | 0.649 | 0.752 | 0.444 | 0.386 | 0.039 |

## D1 entropy diversity (1,000 draws)

| n_eff | D1 mean coverage | D1 areas >= .80 | D1bc mean coverage | D1bc areas >= .80 |
| ---: | ---: | ---: | ---: | ---: |
| 50 | 0.847 | 1.000 | 0.846 | 1.000 |
| 200 | 0.883 | 1.000 | 0.882 | 1.000 |
