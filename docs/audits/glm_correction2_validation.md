# Corrected GLM slopes, part 2: validation (Round 53)

J: regression calibration with delete-one-area jackknife SEs (t, n - p df), independent areas, Round 46 generator. S: pooled calibration + IM-8 per-cluster Poisson/NB2 slopes (S1) vs naive IM-8 (S0), MI/NY spatial fields. M: G1/G2 with five and six error-prone covariates. Pass: coverage >= .86 in every cell.

Criterion commit: `8d48956`. 2,000 draws per cell.

| Problem | Setting | Coverage | Bias | Failed |
| :--- | :--- | :--- | :--- | :--- |
| J | model binomial, reliability 0.9, error_corr 0.0 | J1 0.8955 | J1 +0.0007 | J1 0 |
| J | model binomial, reliability 0.9, error_corr 0.3 | J1 0.8825 | J1 -0.0055 | J1 0 |
| J | model binomial, reliability 0.7, error_corr 0.0 | J1 0.9040 | J1 -0.0033 | J1 0 |
| J | model binomial, reliability 0.7, error_corr 0.3 | J1 0.8895 | J1 -0.0199 | J1 0 |
| J | model poisson, reliability 0.9, error_corr 0.0 | J1 0.8865 | J1 +0.0008 | J1 0 |
| J | model poisson, reliability 0.9, error_corr 0.3 | J1 0.8875 | J1 -0.0043 | J1 0 |
| J | model poisson, reliability 0.7, error_corr 0.0 | J1 0.9040 | J1 +0.0015 | J1 0 |
| J | model poisson, reliability 0.7, error_corr 0.3 | J1 0.9000 | J1 -0.0138 | J1 0 |
| J | model negbin, reliability 0.9, error_corr 0.0 | J1 0.9055 | J1 +0.0013 | J1 0 |
| J | model negbin, reliability 0.9, error_corr 0.3 | J1 0.8995 | J1 -0.0028 | J1 0 |
| J | model negbin, reliability 0.7, error_corr 0.0 | J1 0.9085 | J1 +0.0034 | J1 0 |
| J | model negbin, reliability 0.7, error_corr 0.3 | J1 0.8970 | J1 -0.0169 | J1 0 |
| S | model poisson, reliability 0.9, range_km 0 | S1 0.9045, S0 0.8530 | S1 -0.0000, S0 -0.0194 | S1 0, S0 0 |
| S | model poisson, reliability 0.9, range_km 100 | S1 0.8960, S0 0.7880 | S1 -0.0097, S0 -0.0348 | S1 0, S0 0 |
| S | model poisson, reliability 0.7, range_km 0 | S1 0.9005, S0 0.4970 | S1 +0.0032, S0 -0.0659 | S1 0, S0 0 |
| S | model poisson, reliability 0.7, range_km 100 | S1 0.8775, S0 0.3495 | S1 -0.0212, S0 -0.0955 | S1 0, S0 0 |
| S | model negbin, reliability 0.9, range_km 0 | S1 0.9090, S0 0.8905 | S1 -0.0021, S0 -0.0225 | S1 0, S0 0 |
| S | model negbin, reliability 0.9, range_km 100 | S1 0.8945, S0 0.8695 | S1 -0.0065, S0 -0.0319 | S1 0, S0 0 |
| S | model negbin, reliability 0.7, range_km 0 | S1 0.8945, S0 0.7340 | S1 +0.0028, S0 -0.0583 | S1 0, S0 0 |
| S | model negbin, reliability 0.7, range_km 100 | S1 0.8945, S0 0.5780 | S1 -0.0223, S0 -0.1013 | S1 0, S0 0 |
| M | p 5, reliability 0.9, range_km 0 | G1 0.9055, G2 0.8990 | G1 -0.0061, G2 -0.0064 | G1 0, G2 0 |
| M | p 5, reliability 0.9, range_km 100 | G1 0.8850, G2 0.8840 | G1 +0.0174, G2 +0.0036 | G1 0, G2 0 |
| M | p 5, reliability 0.7, range_km 0 | G1 0.9085, G2 0.9255 | G1 +0.0171, G2 -0.0096 | G1 1, G2 2 |
| M | p 5, reliability 0.7, range_km 100 | G1 0.8645, G2 0.8850 | G1 -0.2138, G2 +1.2438 | G1 68, G2 200 |
| M | p 6, reliability 0.9, range_km 0 | G1 0.9095, G2 0.8950 | G1 +0.0066, G2 -0.0000 | G1 0, G2 0 |
| M | p 6, reliability 0.9, range_km 100 | G1 0.8980, G2 0.8830 | G1 +0.0256, G2 -0.0037 | G1 0, G2 0 |
| M | p 6, reliability 0.7, range_km 0 | G1 0.8970, G2 0.9330 | G1 +0.0017, G2 -0.0359 | G1 4, G2 8 |
| M | p 6, reliability 0.7, range_km 100 | G1 0.8110, G2 0.8040 | G1 -0.3453, G2 -0.1642 | G1 185, G2 373 |

Outcomes: `{"G1_p5": true, "G1_p6": false, "G2_p5": true, "G2_p6": false, "J1_binomial": true, "J1_negbin": true, "J1_poisson": true, "S1_negbin": true, "S1_poisson": true}`.
