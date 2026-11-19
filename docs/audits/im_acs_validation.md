# IM with ACS sampling error validation (Round 30)

90% coverage >=0.86 in every cell, separately by candidate/model; failures are non-coverage

Criterion commit: `2774140a3bdfe0dd5d4f9727a7cdc99631255c01`. Exactly 2,000 draws per cell; nothing retuned.

| Candidate | Model | Range km | Reliability | Coverage | True-beta coverage | Failed | Width | Null size (.05) | Null failed |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| C1 | linear | 0 | 0.9 | 0.8995 | 0.8795 | 0 | 0.3963 | 0.0460 | 0 |
| C2 | linear | 0 | 0.9 | 0.9035 | 0.9035 | 3 | 0.5472 | 0.0435 | 3 |
| C1 | linear | 0 | 0.7 | 0.9130 | 0.6670 | 0 | 0.3662 | 0.0515 | 0 |
| C2 | linear | 0 | 0.7 | 0.4380 | 0.4380 | 1054 | 4.6606 | 0.0110 | 1054 |
| C1 | linear | 100 | 0.9 | 0.8790 | 0.8565 | 0 | 0.4708 | 0.0515 | 0 |
| C2 | linear | 100 | 0.9 | 0.8355 | 0.8355 | 125 | 0.9512 | 0.0505 | 125 |
| C1 | linear | 100 | 0.7 | 0.8850 | 0.5690 | 0 | 0.4006 | 0.0605 | 0 |
| C2 | linear | 100 | 0.7 | 0.0695 | 0.0695 | 1852 | 18.6661 | 0.0015 | 1852 |
| C1 | binomial | 0 | 0.9 | 0.9060 | 0.7940 | 0 | 0.1143 | 0.0530 | 0 |
| C1 | binomial | 0 | 0.7 | 0.9020 | 0.4415 | 0 | 0.1477 | 0.0500 | 0 |
| C1 | binomial | 100 | 0.9 | 0.8690 | 0.7085 | 0 | 0.1350 | 0.0535 | 0 |
| C1 | binomial | 100 | 0.7 | 0.8855 | 0.2170 | 0 | 0.1559 | 0.0620 | 0 |
| C1 | poisson | 0 | 0.9 | 0.9030 | 0.7955 | 0 | 0.1193 | 0.0515 | 0 |
| C1 | poisson | 0 | 0.7 | 0.9235 | 0.4615 | 0 | 0.1512 | 0.0485 | 0 |
| C1 | poisson | 100 | 0.9 | 0.8695 | 0.7330 | 0 | 0.1400 | 0.0495 | 0 |
| C1 | poisson | 100 | 0.7 | 0.8925 | 0.1635 | 0 | 0.1558 | 0.0555 | 0 |

Outcomes: `{"C1": {"binomial": true, "linear": true, "poisson": true}, "C2": {"linear": false}}`.

C1 targets the committed observed-estimate probability limit, not the true slope. C2 targets the true slope.
Null size and interval widths are informational. Null failures are reported separately and remain in the size denominator.
Eight fixed MI/NY clusters; state factor absorbed by the cluster intercept. Failed clusters are never dropped.
ACS uncertainty enters between-cluster variation; no additive replicate SE. No criterion, seed or target changed.
