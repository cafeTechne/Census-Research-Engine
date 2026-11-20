# OH/PA external validity, part 2, and IM with 4/6 clusters: validation (Round 54)

C: naive IM (observed-estimate target) with G = 4, 6 (within-state) and 8 clusters on MI/NY and OH/PA. K: Round 45 IM-8 counts on OH/PA. S: Round 53 calibrated IM-8 counts on OH/PA. M: G1/G2 with 3-5 error-prone covariates on OH/PA. Pass: coverage >= .86 in every cell of the problem.

Criterion commit: `e42840d`. 2,000 draws per cell.

## C: naive IM by cluster count

| Geometry | Model | Range km | Reliability | IM4 | IM6 | IM8 | Mean width IM4 / IM6 / IM8 |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| miny | linear | 0 | 0.9 | 0.8975 | 0.9035 | 0.9035 | 0.450 / 0.430 / 0.395 |
| miny | linear | 0 | 0.7 | 0.9065 | 0.9105 | 0.9125 | 0.413 / 0.388 / 0.365 |
| miny | linear | 100 | 0.9 | 0.8985 | 0.8905 | 0.8860 | 0.625 / 0.533 / 0.477 |
| miny | linear | 100 | 0.7 | 0.8850 | 0.8690 | 0.8485 | 0.519 / 0.439 / 0.398 |
| miny | binomial | 0 | 0.9 | 0.9070 | 0.9030 | 0.8970 | 0.147 / 0.127 / 0.114 |
| miny | binomial | 0 | 0.7 | 0.9125 | 0.8950 | 0.8875 | 0.188 / 0.164 / 0.147 |
| miny | binomial | 100 | 0.9 | 0.9035 | 0.8900 | 0.8805 | 0.182 / 0.149 / 0.137 |
| miny | binomial | 100 | 0.7 | 0.9080 | 0.9050 | 0.8885 | 0.202 / 0.172 / 0.156 |
| miny | poisson | 0 | 0.9 | 0.9080 | 0.9130 | 0.9025 | 0.152 / 0.129 / 0.120 |
| miny | poisson | 0 | 0.7 | 0.9315 | 0.9320 | 0.9145 | 0.200 / 0.174 / 0.150 |
| miny | poisson | 100 | 0.9 | 0.9010 | 0.8955 | 0.8830 | 0.172 / 0.152 / 0.140 |
| miny | poisson | 100 | 0.7 | 0.9215 | 0.8965 | 0.8820 | 0.214 / 0.172 / 0.155 |
| ohpa | linear | 0 | 0.9 | 0.9030 | 0.9015 | 0.8945 | 0.411 / 0.375 / 0.382 |
| ohpa | linear | 0 | 0.7 | 0.9160 | 0.9155 | 0.9080 | 0.396 / 0.349 / 0.354 |
| ohpa | linear | 100 | 0.9 | 0.8760 | 0.8690 | 0.8665 | 0.593 / 0.490 / 0.463 |
| ohpa | linear | 100 | 0.7 | 0.8690 | 0.8355 | 0.8250 | 0.480 / 0.394 / 0.376 |
| ohpa | binomial | 0 | 0.9 | 0.9075 | 0.9030 | 0.9020 | 0.137 / 0.119 / 0.115 |
| ohpa | binomial | 0 | 0.7 | 0.9090 | 0.9080 | 0.9200 | 0.164 / 0.142 / 0.143 |
| ohpa | binomial | 100 | 0.9 | 0.8815 | 0.8670 | 0.8490 | 0.170 / 0.143 / 0.134 |
| ohpa | binomial | 100 | 0.7 | 0.8275 | 0.7535 | 0.7200 | 0.183 / 0.155 / 0.153 |
| ohpa | poisson | 0 | 0.9 | 0.8990 | 0.9070 | 0.9105 | 0.126 / 0.113 / 0.111 |
| ohpa | poisson | 0 | 0.7 | 0.9260 | 0.9105 | 0.8995 | 0.178 / 0.149 / 0.142 |
| ohpa | poisson | 100 | 0.9 | 0.8680 | 0.8645 | 0.8565 | 0.161 / 0.142 / 0.141 |
| ohpa | poisson | 100 | 0.7 | 0.8440 | 0.8020 | 0.7650 | 0.191 / 0.166 / 0.160 |

## K, S, M on OH/PA

| Problem | Setting | Coverage | Bias | Failed |
| :--- | :--- | :--- | :--- | :--- |
| K | median 10, range_km 0 | K2a 0.9010, K2b 0.9035 | K2a +0.0013, K2b -0.0026 | K2a 0, K2b 0 |
| K | median 10, range_km 100 | K2a 0.9045, K2b 0.9055 | K2a +0.0011, K2b -0.0039 | K2a 0, K2b 0 |
| K | median 30, range_km 0 | K2a 0.9115, K2b 0.9010 | K2a +0.0016, K2b -0.0033 | K2a 0, K2b 0 |
| K | median 30, range_km 100 | K2a 0.8915, K2b 0.8995 | K2a +0.0015, K2b -0.0016 | K2a 0, K2b 0 |
| S | model poisson, reliability 0.9, range_km 0 | S1 0.9050, S0 0.8145 | S1 -0.0014, S0 -0.0242 | S1 0, S0 0 |
| S | model poisson, reliability 0.9, range_km 100 | S1 0.8910, S0 0.7685 | S1 -0.0127, S0 -0.0388 | S1 0, S0 0 |
| S | model poisson, reliability 0.7, range_km 0 | S1 0.9025, S0 0.5625 | S1 +0.0004, S0 -0.0608 | S1 0, S0 0 |
| S | model poisson, reliability 0.7, range_km 100 | S1 0.8755, S0 0.3325 | S1 -0.0232, S0 -0.0967 | S1 0, S0 0 |
| S | model negbin, reliability 0.9, range_km 0 | S1 0.9025, S0 0.8875 | S1 +0.0027, S0 -0.0164 | S1 0, S0 0 |
| S | model negbin, reliability 0.9, range_km 100 | S1 0.9120, S0 0.8720 | S1 -0.0117, S0 -0.0380 | S1 0, S0 0 |
| S | model negbin, reliability 0.7, range_km 0 | S1 0.9070, S0 0.6935 | S1 +0.0001, S0 -0.0657 | S1 0, S0 0 |
| S | model negbin, reliability 0.7, range_km 100 | S1 0.8875, S0 0.6395 | S1 -0.0187, S0 -0.0923 | S1 0, S0 0 |
| M | p 3, reliability 0.9, range_km 0 | G1 0.8930, G2 0.8930 | G1 -0.0025, G2 +0.0031 | G1 0, G2 0 |
| M | p 3, reliability 0.9, range_km 100 | G1 0.8870, G2 0.8835 | G1 -0.0139, G2 +0.0033 | G1 0, G2 0 |
| M | p 3, reliability 0.7, range_km 0 | G1 0.8965, G2 0.8940 | G1 -0.0022, G2 -0.0007 | G1 0, G2 0 |
| M | p 3, reliability 0.7, range_km 100 | G1 0.8595, G2 0.9205 | G1 -0.0834, G2 -0.0092 | G1 12, G2 82 |
| M | p 4, reliability 0.9, range_km 0 | G1 0.8975, G2 0.9045 | G1 +0.0013, G2 +0.0033 | G1 0, G2 0 |
| M | p 4, reliability 0.9, range_km 100 | G1 0.8925, G2 0.8745 | G1 +0.0206, G2 -0.0011 | G1 0, G2 0 |
| M | p 4, reliability 0.7, range_km 0 | G1 0.8985, G2 0.9040 | G1 +0.0007, G2 -0.0001 | G1 0, G2 0 |
| M | p 4, reliability 0.7, range_km 100 | G1 0.8595, G2 0.8615 | G1 +0.0208, G2 +0.0418 | G1 42, G2 229 |
| M | p 5, reliability 0.9, range_km 0 | G1 0.9040, G2 0.8855 | G1 +0.0013, G2 -0.0004 | G1 0, G2 0 |
| M | p 5, reliability 0.9, range_km 100 | G1 0.8905, G2 0.8895 | G1 -0.0157, G2 -0.0056 | G1 0, G2 0 |
| M | p 5, reliability 0.7, range_km 0 | G1 0.9100, G2 0.9185 | G1 +0.0027, G2 -0.0260 | G1 2, G2 2 |
| M | p 5, reliability 0.7, range_km 100 | G1 0.8500, G2 0.8070 | G1 +0.0255, G2 -3.6618 | G1 93, G2 363 |

Outcomes: `{"G1_p3": false, "G1_p4": false, "G1_p5": false, "G2_p3": true, "G2_p4": true, "G2_p5": false, "IM4": false, "IM4_miny": true, "IM4_ohpa": false, "IM6": false, "IM6_miny": true, "IM6_ohpa": false, "IM8": false, "IM8_miny": false, "IM8_ohpa": false, "K2a": true, "K2b": true, "S1_negbin": true, "S1_poisson": true}`.
