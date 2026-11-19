# Small samples and spatial dependence: validation (Round 48)

90% coverage >= .86 in every cell of the problem (failed fits count as non-coverage); I: smallest n with both changes >= .86 there and at every larger n, both phi; C per method; B both limits; I0 is the Round 42 GLSAR comparison.

Criterion commit: `3fb07d3`. 2,000 draws per cell. Suffix _a/_b: level/slope change (I) or lower/upper limit (B).

| Problem | Setting | Coverage | Failed |
| :--- | :--- | :--- | :--- |
| I | n 15, phi 0.3 | I0_a 0.7495, I0_b 0.7110, I1_a 0.8250, I1_b 0.8555, I2_a 0.8735, I2_b 0.8855 | I0 0, I1 0, I2 0 |
| I | n 15, phi 0.6 | I0_a 0.7095, I0_b 0.5850, I1_a 0.8295, I1_b 0.7915, I2_a 0.8930, I2_b 0.8460 | I0 0, I1 0, I2 0 |
| I | n 20, phi 0.3 | I0_a 0.7820, I0_b 0.7730, I1_a 0.8420, I1_b 0.8630, I2_a 0.8880, I2_b 0.8940 | I0 0, I1 0, I2 0 |
| I | n 20, phi 0.6 | I0_a 0.7395, I0_b 0.6345, I1_a 0.8310, I1_b 0.8120, I2_a 0.8850, I2_b 0.8565 | I0 0, I1 0, I2 0 |
| I | n 30, phi 0.3 | I0_a 0.8145, I0_b 0.7970, I1_a 0.8600, I1_b 0.8800, I2_a 0.8935, I2_b 0.8955 | I0 0, I1 0, I2 0 |
| I | n 30, phi 0.6 | I0_a 0.7870, I0_b 0.7055, I1_a 0.8460, I1_b 0.8530, I2_a 0.8950, I2_b 0.8830 | I0 0, I1 0, I2 0 |
| C | r33_cell 0, rho 0.0, reliability 0.9, range_km 0 | C1_spearman 0.9165, C2_spearman 0.9080, C1_kendall 0.9030, C2_kendall 0.9065, C1_pearson 0.9400, C2_pearson 0.9085 | C1_spearman 0, C2_spearman 0, C1_kendall 0, C2_kendall 0, C1_pearson 0, C2_pearson 0 |
| C | r33_cell 1, rho 0.0, reliability 0.9, range_km 100 | C1_spearman 0.9060, C2_spearman 0.9010, C1_kendall 0.8940, C2_kendall 0.8975, C1_pearson 0.9030, C2_pearson 0.8950 | C1_spearman 0, C2_spearman 0, C1_kendall 0, C2_kendall 0, C1_pearson 0, C2_pearson 0 |
| C | r33_cell 2, rho 0.0, reliability 0.7, range_km 0 | C1_spearman 0.9165, C2_spearman 0.9040, C1_kendall 0.9045, C2_kendall 0.9065, C1_pearson 0.9665, C2_pearson 0.9010 | C1_spearman 0, C2_spearman 0, C1_kendall 0, C2_kendall 0, C1_pearson 0, C2_pearson 0 |
| C | r33_cell 3, rho 0.0, reliability 0.7, range_km 100 | C1_spearman 0.9070, C2_spearman 0.8865, C1_kendall 0.8940, C2_kendall 0.8885, C1_pearson 0.9550, C2_pearson 0.8970 | C1_spearman 0, C2_spearman 0, C1_kendall 0, C2_kendall 0, C1_pearson 0, C2_pearson 0 |
| C | r33_cell 4, rho 0.4, reliability 0.9, range_km 0 | C1_spearman 0.9095, C2_spearman 0.9060, C1_kendall 0.8990, C2_kendall 0.9065, C1_pearson 0.8980, C2_pearson 0.9115 | C1_spearman 0, C2_spearman 0, C1_kendall 0, C2_kendall 0, C1_pearson 0, C2_pearson 0 |
| C | r33_cell 5, rho 0.4, reliability 0.9, range_km 100 | C1_spearman 0.8750, C2_spearman 0.8825, C1_kendall 0.8620, C2_kendall 0.8870, C1_pearson 0.8640, C2_pearson 0.8770 | C1_spearman 0, C2_spearman 0, C1_kendall 0, C2_kendall 0, C1_pearson 0, C2_pearson 0 |
| C | r33_cell 6, rho 0.4, reliability 0.7, range_km 0 | C1_spearman 0.9105, C2_spearman 0.8975, C1_kendall 0.9005, C2_kendall 0.8935, C1_pearson 0.9605, C2_pearson 0.8955 | C1_spearman 0, C2_spearman 0, C1_kendall 0, C2_kendall 0, C1_pearson 0, C2_pearson 0 |
| C | r33_cell 7, rho 0.4, reliability 0.7, range_km 100 | C1_spearman 0.8875, C2_spearman 0.8585, C1_kendall 0.8805, C2_kendall 0.8710, C1_pearson 0.9220, C2_pearson 0.8475 | C1_spearman 0, C2_spearman 0, C1_kendall 0, C2_kendall 0, C1_pearson 0, C2_pearson 0 |
| A | r36_cell 0, reliability 0.9, range_km 0, weights pca | A3 0.9190, A4 0.9000 | A3 0, A4 0 |
| A | r36_cell 1, reliability 0.9, range_km 0, weights equal | A3 0.9120, A4 0.8945 | A3 0, A4 0 |
| A | r36_cell 2, reliability 0.9, range_km 100, weights pca | A3 0.9250, A4 0.8030 | A3 0, A4 0 |
| A | r36_cell 3, reliability 0.9, range_km 100, weights equal | A3 0.9245, A4 0.8145 | A3 0, A4 0 |
| A | r36_cell 4, reliability 0.7, range_km 0, weights pca | A3 0.9145, A4 0.8835 | A3 0, A4 0 |
| A | r36_cell 5, reliability 0.7, range_km 0, weights equal | A3 0.9255, A4 0.9000 | A3 0, A4 0 |
| A | r36_cell 6, reliability 0.7, range_km 100, weights pca | A3 0.9205, A4 0.7485 | A3 0, A4 0 |
| A | r36_cell 7, reliability 0.7, range_km 100, weights equal | A3 0.9250, A4 0.7585 | A3 0, A4 0 |
| H | k 5, tau_ratio 0.5 | H1 0.8635, H2 0.9175 | H1 0, H2 0 |
| H | k 5, tau_ratio 2.0 | H1 0.8850, H2 0.8920 | H1 0, H2 0 |
| H | k 7, tau_ratio 0.5 | H1 0.8615, H2 0.8840 | H1 0, H2 0 |
| H | k 7, tau_ratio 2.0 | H1 0.8770, H2 0.8785 | H1 0, H2 0 |
| H | k 10, tau_ratio 0.5 | H1 0.8695, H2 0.8740 | H1 0, H2 0 |
| H | k 10, tau_ratio 2.0 | H1 0.8890, H2 0.8900 | H1 0, H2 0 |
| B | r37_cell 0, reliability_a 0.9, b_error False, range_km 0 | B1r_a 0.8985, B1r_b 0.8945, B2r_a 0.8965, B2r_b 0.8895 | B1r 0, B2r 0 |
| B | r37_cell 2, reliability_a 0.9, b_error True, range_km 0 | B1r_a 0.8980, B1r_b 0.8975, B2r_a 0.9070, B2r_b 0.9030 | B1r 0, B2r 1 |
| B | r37_cell 4, reliability_a 0.7, b_error False, range_km 0 | B1r_a 0.8895, B1r_b 0.8910, B2r_a 0.9085, B2r_b 0.9095 | B1r 0, B2r 4 |
| B | r37_cell 6, reliability_a 0.7, b_error True, range_km 0 | B1r_a 0.8860, B1r_b 0.8835, B2r_a 0.9355, B2r_b 0.9320 | B1r 0, B2r 39 |

Outcomes: `{"A3": true, "A4": false, "B1r": true, "B2r": true, "C1_kendall": true, "C1_pearson": true, "C1_spearman": true, "C2_kendall": true, "C2_pearson": false, "C2_spearman": false, "H1": true, "H2": true, "I1_min_n": null, "I2_min_n": 30}`.
