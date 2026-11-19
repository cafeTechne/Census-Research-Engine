# GLM measurement-error correction and EIV with more covariates: validation (Round 46)

90% coverage of the true slope >= .86 in every cell, per procedure (R1 per model; G1/G2 per p); failed fits count as non-coverage; R0 is a comparison.

Criterion commit: `4aceb22`. 2,000 draws per cell.

| Problem | Setting | Coverage | Bias | Failed |
| :--- | :--- | :--- | :--- | :--- |
| R | model binomial, reliability 0.9, error_corr 0.0 | R0 0.7815, R1 0.8635 | R0 -0.0215, R1 -0.0007 | R0 0, R1 0 |
| R | model binomial, reliability 0.9, error_corr 0.3 | R0 0.7905, R1 0.8505 | R0 -0.0231, R1 -0.0044 | R0 0, R1 0 |
| R | model binomial, reliability 0.7, error_corr 0.0 | R0 0.4515, R1 0.8885 | R0 -0.0623, R1 -0.0012 | R0 0, R1 0 |
| R | model binomial, reliability 0.7, error_corr 0.3 | R0 0.3810, R1 0.8795 | R0 -0.0774, R1 -0.0164 | R0 0, R1 0 |
| R | model poisson, reliability 0.9, error_corr 0.0 | R0 0.7995, R1 0.8690 | R0 -0.0224, R1 +0.0002 | R0 0, R1 0 |
| R | model poisson, reliability 0.9, error_corr 0.3 | R0 0.7640, R1 0.8855 | R0 -0.0323, R1 -0.0037 | R0 0, R1 0 |
| R | model poisson, reliability 0.7, error_corr 0.0 | R0 0.5410, R1 0.8925 | R0 -0.0634, R1 -0.0001 | R0 0, R1 0 |
| R | model poisson, reliability 0.7, error_corr 0.3 | R0 0.4525, R1 0.8890 | R0 -0.0743, R1 -0.0165 | R0 0, R1 0 |
| R | model negbin, reliability 0.9, error_corr 0.0 | R0 0.8545, R1 0.8985 | R0 -0.0191, R1 +0.0021 | R0 0, R1 0 |
| R | model negbin, reliability 0.9, error_corr 0.3 | R0 0.8385, R1 0.8875 | R0 -0.0258, R1 -0.0054 | R0 0, R1 0 |
| R | model negbin, reliability 0.7, error_corr 0.0 | R0 0.5795, R1 0.9095 | R0 -0.0660, R1 +0.0011 | R0 0, R1 0 |
| R | model negbin, reliability 0.7, error_corr 0.3 | R0 0.5035, R1 0.9175 | R0 -0.0794, R1 -0.0169 | R0 0, R1 0 |
| M | p 3, reliability 0.9, range_km 0 | G1 0.9065, G2 0.8925 | G1 +0.0072, G2 +0.0023 | G1 0, G2 0 |
| M | p 3, reliability 0.9, range_km 100 | G1 0.8870, G2 0.8775 | G1 +0.0035, G2 +0.0029 | G1 0, G2 0 |
| M | p 3, reliability 0.7, range_km 0 | G1 0.8930, G2 0.8935 | G1 -0.0049, G2 -0.0058 | G1 0, G2 0 |
| M | p 3, reliability 0.7, range_km 100 | G1 0.8810, G2 0.9270 | G1 +0.0610, G2 -0.0285 | G1 10, G2 35 |
| M | p 4, reliability 0.9, range_km 0 | G1 0.9040, G2 0.8860 | G1 +0.0013, G2 +0.0019 | G1 0, G2 0 |
| M | p 4, reliability 0.9, range_km 100 | G1 0.8935, G2 0.8765 | G1 +0.0103, G2 -0.0002 | G1 0, G2 0 |
| M | p 4, reliability 0.7, range_km 0 | G1 0.8925, G2 0.9045 | G1 -0.0122, G2 -0.0052 | G1 0, G2 0 |
| M | p 4, reliability 0.7, range_km 100 | G1 0.8895, G2 0.9120 | G1 +0.0907, G2 +0.1679 | G1 32, G2 114 |

Outcomes: `{"G1_p3": true, "G1_p4": true, "G2_p3": true, "G2_p4": true, "R1_binomial": false, "R1_negbin": true, "R1_poisson": true}`.
