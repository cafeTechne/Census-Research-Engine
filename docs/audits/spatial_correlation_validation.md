# Correlations under spatial dependence: validation (Round 59)

P: effective-n partial correlations (P1) vs the independent-area interval (P0), MI/NY. O: Round 48 effective-n correlations (C1) and P1 on OH/PA. A: Round 48 effective-n alpha (A3) on OH/PA. Targets: Round 33/36 observed-value references (OH/PA recomputed). Pass: coverage >= .86 in every cell of the problem.

Criterion commit: `669a506`. 2,000 draws per cell.

| Problem | Geometry | Cell | Coverage | Failed |
| :--- | :--- | ---: | :--- | :--- |
| P | miny | 0 | P1 0.9370, P0 0.9365 |  |
| P | miny | 1 | P1 0.9040, P0 0.7260 |  |
| P | miny | 2 | P1 0.9715, P0 0.9700 |  |
| P | miny | 3 | P1 0.9560, P0 0.8800 |  |
| P | miny | 4 | P1 0.9155, P0 0.9115 |  |
| P | miny | 5 | P1 0.8695, P0 0.6895 |  |
| P | miny | 6 | P1 0.9650, P0 0.9635 |  |
| P | miny | 7 | P1 0.9250, P0 0.8580 |  |
| O | ohpa | 0 | P1 0.9300, C1_spearman 0.9070, C1_kendall 0.8940, C1_pearson 0.9275 |  |
| O | ohpa | 1 | P1 0.9150, C1_spearman 0.9095, C1_kendall 0.9015, C1_pearson 0.9205 |  |
| O | ohpa | 2 | P1 0.9685, C1_spearman 0.9020, C1_kendall 0.8805, C1_pearson 0.9645 |  |
| O | ohpa | 3 | P1 0.9510, C1_spearman 0.9035, C1_kendall 0.8905, C1_pearson 0.9500 |  |
| O | ohpa | 4 | P1 0.9035, C1_spearman 0.9040, C1_kendall 0.9020, C1_pearson 0.8925 |  |
| O | ohpa | 5 | P1 0.8840, C1_spearman 0.9050, C1_kendall 0.8950, C1_pearson 0.8895 |  |
| O | ohpa | 6 | P1 0.9635, C1_spearman 0.9185, C1_kendall 0.9050, C1_pearson 0.9650 |  |
| O | ohpa | 7 | P1 0.9275, C1_spearman 0.8915, C1_kendall 0.8835, C1_pearson 0.9230 |  |
| A | ohpa | 0 | A3 0.9330 |  |
| A | ohpa | 1 | A3 0.9220 |  |
| A | ohpa | 2 | A3 0.9100 |  |
| A | ohpa | 3 | A3 0.9020 |  |
| A | ohpa | 4 | A3 0.9225 |  |
| A | ohpa | 5 | A3 0.9230 |  |
| A | ohpa | 6 | A3 0.9125 |  |
| A | ohpa | 7 | A3 0.9015 |  |

Outcomes: `{"A3_ohpa": true, "C1_kendall_ohpa": true, "C1_pearson_ohpa": true, "C1_spearman_ohpa": true, "P0": false, "P1": true}`.
