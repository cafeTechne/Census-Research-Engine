# Corrected slope inference under spatial dependence: validation (Round 35)

90% coverage of the true slope >= .86 in every cell (spatial and independent), per candidate; failed fits count as non-coverage; C1_naive informational.

Criterion commit: `46fab40`. 2,000 draws per cell.

| Reliability | Range km | Error corr | G1 | G2 | C1 naive (true slope) | G1 bias | G2 bias | G1 / G2 failed | mean λ̂ |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- | ---: |
| 0.9 | 0 | 0.0 | 0.8985 | 0.8915 | 0.8825 | +0.0022 | +0.0009 | 0 / 0 | -0.065 |
| 0.9 | 0 | 0.3 | 0.8985 | 0.8820 | 0.8995 | +0.0055 | +0.0063 | 0 / 0 | -0.072 |
| 0.9 | 100 | 0.0 | 0.8830 | 0.8870 | 0.8455 | -0.0065 | -0.0023 | 0 / 0 | 0.617 |
| 0.9 | 100 | 0.3 | 0.8835 | 0.8630 | 0.8855 | +0.0067 | +0.0058 | 0 / 0 | 0.627 |
| 0.7 | 0 | 0.0 | 0.8990 | 0.8870 | 0.7280 | +0.0174 | +0.0046 | 0 / 0 | -0.073 |
| 0.7 | 0 | 0.3 | 0.8990 | 0.8980 | 0.8470 | +0.0108 | +0.0074 | 0 / 0 | -0.076 |
| 0.7 | 100 | 0.0 | 0.8790 | 0.8985 | 0.5800 | +0.0270 | +0.0423 | 0 / 1 | 0.617 |
| 0.7 | 100 | 0.3 | 0.8850 | 0.9175 | 0.7945 | +0.0390 | +0.0364 | 0 / 1 | 0.625 |

Outcomes: `{"G1": true, "G2": true}`.
