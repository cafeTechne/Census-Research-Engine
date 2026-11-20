# Leftover failures: validation (Round 62)

A: binomial SCPC with rho_bar .15/.20 (Round 58 cells). B: Theil T with 8,000 households (T1 log interval). C: clipped six-group segregation (Round 57 design A). Pass: coverage >= .86 in every cell (C: Round 50 bin rule with the Round 57 affected-draw check).

Criterion commit: `8f14e39`.

| Problem | Setting | Draws | Coverage | Failed |
| :--- | :--- | ---: | :--- | :--- |
| A | geometry miny, r30_cell 4 | 2000 | SCPC15 0.9345, SCPC20 0.9485 |  |
| A | geometry miny, r30_cell 5 | 2000 | SCPC15 0.9325, SCPC20 0.9495 |  |
| A | geometry miny, r30_cell 6 | 2000 | SCPC15 0.8925, SCPC20 0.9145 |  |
| A | geometry miny, r30_cell 7 | 2000 | SCPC15 0.9185, SCPC20 0.9380 |  |
| A | geometry ohpa, r30_cell 4 | 2000 | SCPC15 0.9410, SCPC20 0.9585 |  |
| A | geometry ohpa, r30_cell 5 | 2000 | SCPC15 0.9540, SCPC20 0.9660 |  |
| A | geometry ohpa, r30_cell 6 | 2000 | SCPC15 0.8860, SCPC20 0.9090 |  |
| A | geometry ohpa, r30_cell 7 | 2000 | SCPC15 0.9115, SCPC20 0.9300 |  |
| A | geometry miny, r30_cell 7, long True | 10000 | SCPC15 0.9205, SCPC20 0.9401 |  |
| B | rho 0.1, weight_cv 0.3, households 8000 | 2000 | I1|T0 0.8855, I1|T1 0.8880, I2|T0 0.8845, I2|T1 0.8855 |  |
| B | rho 0.1, weight_cv 1.0, households 8000 | 2000 | I1|T0 0.8740, I1|T1 0.8730, I2|T0 0.8585, I2|T1 0.8585 |  |
| B | rho 0.4, weight_cv 0.3, households 8000 | 2000 | I1|T0 0.8965, I1|T1 0.8985, I2|T0 0.8860, I2|T1 0.8880 |  |
| B | rho 0.4, weight_cv 1.0, households 8000 | 2000 | I1|T0 0.8795, I1|T1 0.8795, I2|T0 0.8640, I2|T1 0.8645 |  |

## C: clipped six-group H

| Index | Bin | Counties | Judged | rho cells (mean / share >= .80 / min) | Affected | Passed |
| :--- | :--- | ---: | :--- | :--- | :--- | :--- |
| H_bc | [.50, .75) | 4 | False | 0.9547 / 1.000 / 0.9360; 0.9589 / 1.000 / 0.9435 | 7994 / 0.9547; 7995 / 0.9588 | False |
| H_bc | [.75, 1) | 11 | True | 0.9557 / 1.000 / 0.8910; 0.9581 / 1.000 / 0.9080 | 21997 / 0.9557; 21999 / 0.9581 | True |
| H_bc | [1, inf) | 97 | True | 0.9729 / 1.000 / 0.8240; 0.9722 / 1.000 / 0.8080 | 193987 / 0.9729; 193988 / 0.9722 | True |
| H_bc | **validated to** | | | inf | | |
| H_naive | [.50, .75) | 4 | False | 0.8119 / 0.500 / 0.7230; 0.8020 / 0.500 / 0.6875 | 7994 / 0.8120; 7995 / 0.8019 | False |
| H_naive | [.75, 1) | 11 | True | 0.7881 / 0.455 / 0.6830; 0.7689 / 0.182 / 0.6665 | 21997 / 0.7881; 21999 / 0.7689 | False |
| H_naive | [1, inf) | 97 | True | 0.6357 / 0.144 / 0.0945; 0.6107 / 0.082 / 0.0710 | 193987 / 0.6357; 193988 / 0.6107 | False |
| H_naive | **validated to** | | | None | | |

Outcomes: `{"binomial_SCPC15": true, "binomial_SCPC20": true, "clip_six": {"H_bc": "inf", "H_naive": null}, "theil_t_T1_8000": false}`.
