# Spatial inference outside MI/NY: validation (Round 58)

N/R: naive (observed-estimate) slopes with SCPC (rho_bar .05, .10) and IM-8 on MI/NY and OH/PA; R cells 10,000 draws. G: G1/G2 with three to five error-prone covariates at reliability .8. B: calibrated binomial slopes with IM-8. Pass: coverage >= .86 in every cell of the problem.

Criterion commit: `e8c6c8c`.

| Geometry | rho_bar | q | Critical value | Benchmark range (km) |
| :--- | ---: | ---: | ---: | ---: |
| miny | 0.05 | 6 | 2.239 | 65.2 |
| miny | 0.1 | 5 | 2.602 | 107.3 |
| ohpa | 0.05 | 5 | 2.362 | 52.4 |
| ohpa | 0.1 | 4 | 2.734 | 81.2 |

| Problem | Geometry | Model | Range | Reliability | Draws | IM8 | SCPC05 | SCPC10 | Width IM8 / SCPC05 / SCPC10 |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| N | miny | linear | 0 | 0.9 | 2000 | 0.9025 | 0.9215 | 0.9455 | 0.394 / 0.403 / 0.463 |
| N | miny | linear | 0 | 0.7 | 2000 | 0.9150 | 0.9305 | 0.9475 | 0.367 / 0.382 / 0.441 |
| N | miny | linear | 100 | 0.9 | 2000 | 0.8715 | 0.8615 | 0.9070 | 0.474 / 0.555 / 0.659 |
| N | miny | linear | 100 | 0.7 | 2000 | 0.8605 | 0.8690 | 0.9075 | 0.397 / 0.455 / 0.545 |
| N | miny | binomial | 0 | 0.9 | 2000 | 0.9150 | 0.8815 | 0.9265 | 0.115 / 0.120 / 0.144 |
| N | miny | binomial | 0 | 0.7 | 2000 | 0.8995 | 0.8925 | 0.9205 | 0.144 / 0.161 / 0.191 |
| N | miny | binomial | 100 | 0.9 | 2000 | 0.8735 | 0.7930 | 0.8465 | 0.140 / 0.135 / 0.159 |
| N | miny | binomial | 100 | 0.7 | 2000 | 0.8850 | 0.8915 | 0.9225 | 0.159 / 0.192 / 0.222 |
| N | miny | poisson | 0 | 0.9 | 2000 | 0.9035 | 0.8910 | 0.9205 | 0.120 / 0.124 / 0.151 |
| N | miny | poisson | 0 | 0.7 | 2000 | 0.9110 | 0.9035 | 0.9340 | 0.151 / 0.169 / 0.203 |
| N | miny | poisson | 100 | 0.9 | 2000 | 0.8755 | 0.8685 | 0.9125 | 0.141 / 0.145 / 0.172 |
| N | miny | poisson | 100 | 0.7 | 2000 | 0.8705 | 0.8780 | 0.9040 | 0.155 / 0.196 / 0.224 |
| N | ohpa | linear | 0 | 0.9 | 2000 | 0.9005 | 0.9265 | 0.9425 | 0.381 / 0.395 / 0.452 |
| N | ohpa | linear | 0 | 0.7 | 2000 | 0.8930 | 0.9225 | 0.9385 | 0.353 / 0.363 / 0.416 |
| N | ohpa | linear | 100 | 0.9 | 2000 | 0.8635 | 0.8620 | 0.8975 | 0.457 / 0.576 / 0.668 |
| N | ohpa | linear | 100 | 0.7 | 2000 | 0.8255 | 0.8840 | 0.9075 | 0.381 / 0.474 / 0.549 |
| N | ohpa | binomial | 0 | 0.9 | 2000 | 0.8930 | 0.9065 | 0.9280 | 0.116 / 0.128 / 0.150 |
| N | ohpa | binomial | 0 | 0.7 | 2000 | 0.8995 | 0.9140 | 0.9365 | 0.142 / 0.155 / 0.179 |
| N | ohpa | binomial | 100 | 0.9 | 2000 | 0.8465 | 0.8210 | 0.8595 | 0.132 / 0.144 / 0.165 |
| N | ohpa | binomial | 100 | 0.7 | 2000 | 0.7165 | 0.8535 | 0.8770 | 0.153 / 0.167 / 0.190 |
| N | ohpa | poisson | 0 | 0.9 | 2000 | 0.8955 | 0.8930 | 0.9265 | 0.111 / 0.117 / 0.136 |
| N | ohpa | poisson | 0 | 0.7 | 2000 | 0.9045 | 0.9170 | 0.9335 | 0.141 / 0.164 / 0.189 |
| N | ohpa | poisson | 100 | 0.9 | 2000 | 0.8455 | 0.8315 | 0.8630 | 0.140 / 0.134 / 0.153 |
| N | ohpa | poisson | 100 | 0.7 | 2000 | 0.7560 | 0.8300 | 0.8675 | 0.159 / 0.169 / 0.194 |
| R | miny | linear | 100 | 0.7 | 10000 | 0.8583 | 0.8710 | 0.9131 | 0.397 / 0.461 / 0.551 |
| R | miny | binomial | 100 | 0.7 | 10000 | 0.8857 | 0.9000 | 0.9233 | 0.157 / 0.193 / 0.224 |
| R | miny | poisson | 100 | 0.7 | 10000 | 0.8756 | 0.8768 | 0.9091 | 0.156 / 0.199 / 0.228 |

| Problem | Setting | Coverage | Bias | Failed |
| :--- | :--- | :--- | :--- | :--- |
| G | p 3, geometry miny, range_km 0 | G1 0.9075, G2 0.9050 | G1 -0.0022, G2 +0.0030 | G1 0, G2 0 |
| G | p 3, geometry miny, range_km 100 | G1 0.9005, G2 0.9245 | G1 +0.0297, G2 +0.0194 | G1 0, G2 1 |
| G | p 3, geometry ohpa, range_km 0 | G1 0.8975, G2 0.8915 | G1 +0.0082, G2 +0.0040 | G1 0, G2 0 |
| G | p 3, geometry ohpa, range_km 100 | G1 0.8900, G2 0.9090 | G1 -0.0214, G2 -0.0071 | G1 0, G2 0 |
| G | p 4, geometry miny, range_km 0 | G1 0.8920, G2 0.8935 | G1 +0.0040, G2 -0.0006 | G1 0, G2 0 |
| G | p 4, geometry miny, range_km 100 | G1 0.8940, G2 0.9140 | G1 +0.0164, G2 +0.0172 | G1 0, G2 3 |
| G | p 4, geometry ohpa, range_km 0 | G1 0.9000, G2 0.8990 | G1 -0.0030, G2 -0.0019 | G1 0, G2 0 |
| G | p 4, geometry ohpa, range_km 100 | G1 0.8860, G2 0.9340 | G1 -0.0093, G2 -0.0238 | G1 0, G2 7 |
| G | p 5, geometry miny, range_km 0 | G1 0.8995, G2 0.8875 | G1 -0.0002, G2 +0.0069 | G1 0, G2 0 |
| G | p 5, geometry miny, range_km 100 | G1 0.8915, G2 0.9175 | G1 -0.0361, G2 -0.0874 | G1 1, G2 13 |
| G | p 5, geometry ohpa, range_km 0 | G1 0.8930, G2 0.8965 | G1 -0.0163, G2 -0.0078 | G1 0, G2 0 |
| G | p 5, geometry ohpa, range_km 100 | G1 0.8995, G2 0.9325 | G1 -0.0158, G2 -0.2036 | G1 6, G2 28 |
| B | reliability 0.9, range_km 0 | B1 0.9070 | B1 +0.0009 | B1 0 |
| B | reliability 0.9, range_km 100 | B1 0.8885 | B1 -0.0102 | B1 0 |
| B | reliability 0.7, range_km 0 | B1 0.8845 | B1 +0.0014 | B1 0 |
| B | reliability 0.7, range_km 100 | B1 0.8770 | B1 -0.0225 | B1 0 |

Outcomes: `{"B1_binomial": true, "G1_p3_rel80": true, "G1_p4_rel80": true, "G1_p5_rel80": true, "G2_p3_rel80": true, "G2_p4_rel80": true, "G2_p5_rel80": true, "IM8_R_binomial": true, "IM8_R_linear": false, "IM8_R_poisson": true, "SCPC05_binomial": false, "SCPC05_linear": true, "SCPC05_poisson": false, "SCPC10_binomial": false, "SCPC10_linear": true, "SCPC10_poisson": true}`.
