# Count-model repairs: validation (Round 45)

90% coverage of the true slope 0.3 >= .86 in every cell of the problem, per procedure; failed fits count as non-coverage; K1b, K1c, K2c, K3b are comparisons.

Criterion commit: `0c368dd`. 2,000 draws per cell; 145 areas.

| Problem | Setting | Coverage | Failed fits |
| :--- | :--- | :--- | :--- |
| K1 | median 10, shape 4.0 | K1a 0.8925, K1b 0.8410, K1c 0.8685 | K1a 0, K1b 0, K1c 0 |
| K1 | median 10, shape 1.5 | K1a 0.8775, K1b 0.8410, K1c 0.8775 | K1a 0, K1b 0, K1c 0 |
| K1 | median 30, shape 4.0 | K1a 0.8980, K1b 0.8625, K1c 0.8575 | K1a 0, K1b 0, K1c 0 |
| K1 | median 30, shape 1.5 | K1a 0.8690, K1b 0.8265, K1c 0.8305 | K1a 0, K1b 0, K1c 0 |
| K2 | median 10, range_km 0 | K2a 0.9090, K2b 0.9035, K2c 0.8840 | K2a 0, K2b 0, K2c 0 |
| K2 | median 10, range_km 100 | K2a 0.9055, K2b 0.8940, K2c 0.8045 | K2a 0, K2b 0, K2c 0 |
| K2 | median 30, range_km 0 | K2a 0.9045, K2b 0.8965, K2c 0.8775 | K2a 0, K2b 0, K2c 0 |
| K2 | median 30, range_km 100 | K2a 0.8955, K2b 0.9045, K2c 0.7950 | K2a 0, K2b 0, K2c 0 |
| K3 | c 0.05 | K3a 0.8910, K3b 0.8550 | K3a 0, K3b 0 |
| K3 | c 0.15 | K3a 0.8875, K3b 0.8325 | K3a 0, K3b 0 |

Outcomes: `{"K1a": true, "K2a": true, "K2b": true, "K3a": true}`.
