# Composite index scores and Cronbach alpha: validation (Round 36)

S1: mean per-area 90% coverage >= .86 and every area >= .80, per weighting (all cells); A1/A2: 90% coverage of the population alpha >= .86 in every independent cell; failures count as non-coverage.

Criterion commit: `e86907d`. 2,000 draws per cell.

| Reliability | Range km | Weights | S1 mean | S1 min area | A1 Feldt | A2 + replicates | population α |
| ---: | ---: | :--- | ---: | ---: | ---: | ---: | ---: |
| 0.9 | 0 | pca | 0.8977 | 0.8805 | 0.8955 | 0.9340 | 0.772 |
| 0.9 | 0 | equal | 0.8984 | 0.8775 | 0.9120 | 0.9395 | 0.772 |
| 0.9 | 100 | pca | 0.8983 | 0.8805 | 0.6015 | 0.6615 | 0.774 |
| 0.9 | 100 | equal | 0.8984 | 0.8745 | 0.5830 | 0.6375 | 0.774 |
| 0.7 | 0 | pca | 0.8982 | 0.8825 | 0.8905 | 0.9685 | 0.728 |
| 0.7 | 0 | equal | 0.8979 | 0.8735 | 0.8985 | 0.9765 | 0.728 |
| 0.7 | 100 | pca | 0.8980 | 0.8790 | 0.6520 | 0.8095 | 0.731 |
| 0.7 | 100 | equal | 0.8990 | 0.8810 | 0.6650 | 0.8235 | 0.727 |

Outcomes: `{"A1": true, "A2": true, "S1/equal": true, "S1/pca": true}`.
