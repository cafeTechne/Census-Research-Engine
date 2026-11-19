# Causal and missing-data robustness: validation (Round 47)

90% coverage >= .86 (failed fits count as non-coverage): T1, S1 in every cell; D1 in every cell for both slopes; W2 in every observed-F bin of both reliabilities (bins need >= 200 draws); W1 cut-off = smallest bin edge with W1 >= .86 there and above in both reliabilities.

Criterion commit: `cbdc97f`. 2,000 draws per cell.

| Problem | Setting | Coverage | Bias | Failed |
| :--- | :--- | :--- | :--- | :--- |
| T | reliability 0.9, rho 0.0 | T0 0.8650, T1 0.8895 | T0 +0.0499, T1 -0.0000 | T0 0, T1 0 |
| T | reliability 0.9, rho 0.3 | T0 0.8660, T1 0.8885 | T0 +0.0515, T1 -0.0013 | T0 0, T1 0 |
| T | reliability 0.8, rho 0.0 | T0 0.8405, T1 0.8905 | T0 +0.0965, T1 -0.0063 | T0 0, T1 1 |
| T | reliability 0.8, rho 0.3 | T0 0.8360, T1 0.8980 | T0 +0.1058, T1 -0.0033 | T0 0, T1 0 |
| T | reliability 0.7, rho 0.0 | T0 0.8010, T1 0.9050 | T0 +0.1429, T1 -0.0094 | T0 0, T1 2 |
| T | reliability 0.7, rho 0.3 | T0 0.7710, T1 0.8925 | T0 +0.1550, T1 -0.0128 | T0 0, T1 11 |
| W | expected_f 2, reliability 0.9, mean F 2.0, AR bounded 512, disjoint 319, real_line 1169, empty 0, failed 0 | W1 0.9920, W2 0.9035 | W1 +1.0711, W2 - | W1 0, W2 0 |
| W | expected_f 5, reliability 0.9, mean F 5.1, AR bounded 1269, disjoint 206, real_line 525, empty 0, failed 0 | W1 0.9705, W2 0.9035 | W1 -0.7028, W2 - | W1 0, W2 0 |
| W | expected_f 10, reliability 0.9, mean F 10.2, AR bounded 1793, disjoint 79, real_line 128, empty 0, failed 0 | W1 0.9515, W2 0.9095 | W1 -0.0003, W2 - | W1 0, W2 0 |
| W | expected_f 20, reliability 0.9, mean F 20.1, AR bounded 1987, disjoint 5, real_line 8, empty 0, failed 0 | W1 0.9170, W2 0.8950 | W1 -0.0023, W2 - | W1 0, W2 0 |
| W | expected_f 30, reliability 0.9, mean F 30.6, AR bounded 2000, disjoint 0, real_line 0, empty 0, failed 0 | W1 0.9045, W2 0.9005 | W1 -0.0021, W2 - | W1 0, W2 0 |
| W | expected_f 2, reliability 0.7, mean F 2.0, AR bounded 532, disjoint 330, real_line 1138, empty 0, failed 0 | W1 0.9865, W2 0.8985 | W1 -1.3697, W2 - | W1 0, W2 0 |
| W | expected_f 5, reliability 0.7, mean F 5.1, AR bounded 1274, disjoint 223, real_line 503, empty 0, failed 0 | W1 0.9660, W2 0.8920 | W1 +0.0173, W2 - | W1 0, W2 0 |
| W | expected_f 10, reliability 0.7, mean F 10.2, AR bounded 1812, disjoint 74, real_line 114, empty 0, failed 0 | W1 0.9490, W2 0.9040 | W1 +0.0336, W2 - | W1 0, W2 0 |
| W | expected_f 20, reliability 0.7, mean F 20.8, AR bounded 1989, disjoint 7, real_line 4, empty 0, failed 0 | W1 0.9115, W2 0.8990 | W1 +0.0053, W2 - | W1 0, W2 0 |
| W | expected_f 30, reliability 0.7, mean F 30.9, AR bounded 1999, disjoint 1, real_line 0, empty 0, failed 0 | W1 0.9120, W2 0.9080 | W1 +0.0093, W2 - | W1 0, W2 0 |
| S | reliability 0.9, b 0.5 | S0 0.8430, S1 0.8980 | S0 -0.0232, S1 -0.0002 | S0 0, S1 0 |
| S | reliability 0.9, b 0.25 | S0 0.8575, S1 0.8910 | S0 -0.0107, S1 +0.0007 | S0 0, S1 0 |
| S | reliability 0.8, b 0.5 | S0 0.7180, S1 0.8880 | S0 -0.0454, S1 +0.0001 | S0 0, S1 0 |
| S | reliability 0.8, b 0.25 | S0 0.8045, S1 0.8960 | S0 -0.0218, S1 +0.0012 | S0 0, S1 0 |
| S | reliability 0.7, b 0.5 | S0 0.5770, S1 0.8825 | S0 -0.0650, S1 +0.0031 | S0 0, S1 0 |
| S | reliability 0.7, b 0.25 | S0 0.6970, S1 0.8880 | S0 -0.0334, S1 +0.0006 | S0 0, S1 0 |
| D | mechanism MCAR, fraction 0.2 | D0_x1 0.9150, D0_x2 0.9050, D1_x1 0.9090, D1_x2 0.9110 | D0_x1 -0.0004, D0_x2 +0.0009, D1_x1 -0.0004, D1_x2 -0.0011 | D0 0, D1 0 |
| D | mechanism MCAR, fraction 0.4 | D0_x1 0.9005, D0_x2 0.9025, D1_x1 0.9095, D1_x2 0.9145 | D0_x1 -0.0027, D0_x2 +0.0020, D1_x1 -0.0054, D1_x2 +0.0001 | D0 0, D1 0 |
| D | mechanism MAR, fraction 0.2 | D0_x1 0.8620, D0_x2 0.8590, D1_x1 0.8990, D1_x2 0.9155 | D0_x1 -0.0515, D0_x2 -0.0538, D1_x1 -0.0023, D1_x2 -0.0038 | D0 0, D1 0 |
| D | mechanism MAR, fraction 0.4 | D0_x1 0.8350, D0_x2 0.8370, D1_x1 0.9040, D1_x2 0.8980 | D0_x1 -0.0764, D0_x2 -0.0771, D1_x1 -0.0048, D1_x2 -0.0046 | D0 0, D1 0 |

## Weak instruments by observed first-stage F (pooled within reliability)

| Bin | Draws | W1 2SLS Wald | W2 Anderson–Rubin |
| :--- | ---: | :--- | :--- |
| rel0.9_F0 | 3451 | 0.9974 | 0.9067 |
| rel0.9_F5 | 1624 | 0.9501 | 0.8941 |
| rel0.9_F10 | 2211 | 0.9190 | 0.9055 |
| rel0.9_F20 | 2714 | 0.9042 | 0.8994 |
| rel0.7_F0 | 3490 | 0.9911 | 0.8946 |
| rel0.7_F5 | 1615 | 0.9480 | 0.9015 |
| rel0.7_F10 | 2097 | 0.9170 | 0.8989 |
| rel0.7_F20 | 2798 | 0.9067 | 0.9078 |

Outcomes: `{"D1": true, "S1": true, "T1": true, "W1_cutoff_f": 0, "W2": true}`.
