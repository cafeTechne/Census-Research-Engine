# Beta and median regression: validation (Round 40)

90% coverage of the naive-target slope >= .86 in every cell of the family; failures count as non-coverage.

Criterion commit: `d5c9b02`. 1,000 draws per cell.

| Family | Covariate reliability | Outcome error | Coverage | Failures |
| :--- | ---: | ---: | :--- | ---: |
| beta | 0.9 | 0.02 | B1 0.8880, B2 0.8920, B3 0.9500 | 0 |
| beta | 0.9 | 0.05 | B1 0.8950, B2 0.9030, B3 0.9570 | 0 |
| beta | 0.7 | 0.02 | B1 0.8560, B2 0.8920, B3 0.9870 | 0 |
| beta | 0.7 | 0.05 | B1 0.8590, B2 0.8850, B3 0.9910 | 0 |
| median | 0.9 | None | Q1 0.9120, Q2 0.9930 | 0 |
| median | 0.7 | None | Q1 0.9170, Q2 0.9910 | 0 |

Outcomes: `{"B1": false, "B2": true, "B3": true, "Q1": true, "Q2": true}`.
