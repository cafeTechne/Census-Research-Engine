# OH/PA re-check of the Round 30 and Round 35 spatial validations (Round 44)

as Rounds 30 and 35: 90% coverage >= .86 in every cell, per candidate (C1 per model); failed fits count as non-coverage; C1 target is the recomputed observed-estimate beta*, G1/G2 target the true slope 0.5; C1_naive and null sizes informational.

Criterion commit: `09ecd91`. 2,000 draws per cell; 155 OH/PA counties, state-respecting eight-cluster assignment.

## C1 (IM-8, observed-estimate target)

| Model | Range km | Reliability | beta* | Coverage | Failed | Null size (.05) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| linear | 0 | 0.9 | 0.4593 | 0.8990 | 0 | 0.0555 |
| linear | 0 | 0.7 | 0.3700 | 0.8975 | 0 | 0.0525 |
| linear | 100 | 0.9 | 0.4583 | 0.8525 | 0 | 0.0710 |
| linear | 100 | 0.7 | 0.3695 | 0.8190 | 0 | 0.0640 |
| binomial | 0 | 0.9 | 0.2701 | 0.8945 | 0 | 0.0450 |
| binomial | 0 | 0.7 | 0.2171 | 0.9090 | 0 | 0.0450 |
| binomial | 100 | 0.9 | 0.2716 | 0.8600 | 0 | 0.0595 |
| binomial | 100 | 0.7 | 0.2420 | 0.7020 | 0 | 0.0495 |
| poisson | 0 | 0.9 | 0.2765 | 0.9080 | 0 | 0.0565 |
| poisson | 0 | 0.7 | 0.2037 | 0.9055 | 0 | 0.0535 |
| poisson | 100 | 0.9 | 0.2643 | 0.8525 | 0 | 0.0505 |
| poisson | 100 | 0.7 | 0.2198 | 0.7590 | 0 | 0.0590 |

## G1/G2 (corrected slopes, target 0.5)

| Reliability | Range km | Error corr | G1 | G2 | C1_naive | Failed (G1/G2) | Mean lambda |
| ---: | ---: | ---: | ---: | ---: | ---: | :--- | ---: |
| 0.9 | 0 | 0.0 | 0.9035 | 0.8850 | 0.8865 | 0/0 | -0.058 |
| 0.9 | 0 | 0.3 | 0.9090 | 0.8900 | 0.9070 | 0/0 | -0.062 |
| 0.9 | 100 | 0.0 | 0.8870 | 0.8630 | 0.8310 | 0/0 | 0.662 |
| 0.9 | 100 | 0.3 | 0.8855 | 0.8790 | 0.8885 | 0/0 | 0.671 |
| 0.7 | 0 | 0.0 | 0.8845 | 0.8970 | 0.6915 | 0/0 | -0.059 |
| 0.7 | 0 | 0.3 | 0.8985 | 0.8990 | 0.8445 | 0/0 | -0.053 |
| 0.7 | 100 | 0.0 | 0.8795 | 0.8990 | 0.5355 | 0/8 | 0.668 |
| 0.7 | 100 | 0.3 | 0.8670 | 0.9210 | 0.7860 | 2/16 | 0.677 |

Outcomes: `{"C1": {"binomial": false, "linear": false, "poisson": false}, "G1": true, "G2": true}`.
