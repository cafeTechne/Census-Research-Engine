# Segregation under realistic ACS error: validation (Round 50)

Truth: 2024 five-year MI/NY tract counts; Gamma-copula observed counts and replicates with the published SEs. Per index: counties binned by noise level (max over groups of the median tract CV); a judged bin (>= 5 counties) passes when, for rho 0 and -.3, mean county coverage >= .86 and >= 90% of counties cover >= .80. Failed draws count as non-coverage.

Criterion commit: `686d121`. 2,000 draws per cell.

## two groups

137 counties (excluded, fewer than 5 populated tracts: 26003, 26013, 26083, 26085, 26095, 26131, 26153, 36041). Counties per bin: [0, 88, 49, 0].

| Index | Bin | Counties | Judged | rho 0: mean / share >= .80 / min | rho -.3: mean / share >= .80 / min | Passed |
| :--- | :--- | ---: | :--- | :--- | :--- | :--- |
| D_naive | [0, .15) | 0 | False | — | — | False |
| D_naive | [.15, .30) | 88 | True | 0.8706 / 0.932 / 0.5730 | 0.8619 / 0.886 / 0.5030 | False |
| D_naive | [.30, .50) | 49 | True | 0.7344 / 0.408 / 0.2730 | 0.7131 / 0.347 / 0.2140 | False |
| D_naive | [.50, inf) | 0 | False | — | — | False |
| I_bc | [0, .15) | 0 | False | — | — | False |
| I_bc | [.15, .30) | 88 | True | 0.8834 / 1.000 / 0.8585 | 0.8865 / 1.000 / 0.8585 | True |
| I_bc | [.30, .50) | 49 | True | 0.9141 / 1.000 / 0.8645 | 0.9201 / 1.000 / 0.8665 | True |
| I_bc | [.50, inf) | 0 | False | — | — | False |
| H_bc | [0, .15) | 0 | False | — | — | False |
| H_bc | [.15, .30) | 88 | True | 0.9256 / 1.000 / 0.8635 | 0.9278 / 1.000 / 0.8785 | True |
| H_bc | [.30, .50) | 49 | True | 0.9658 / 1.000 / 0.9070 | 0.9689 / 1.000 / 0.9210 | True |
| H_bc | [.50, inf) | 0 | False | — | — | False |
| H_naive | [0, .15) | 0 | False | — | — | False |
| H_naive | [.15, .30) | 88 | True | 0.8986 / 0.977 / 0.5845 | 0.8952 / 0.977 / 0.5305 | True |
| H_naive | [.30, .50) | 49 | True | 0.8006 / 0.612 / 0.5610 | 0.7864 / 0.592 / 0.5200 | False |
| H_naive | [.50, inf) | 0 | False | — | — | False |
| D_bc | [0, .15) | 0 | False | — | — | False |
| D_bc | [.15, .30) | 88 | True | 0.8721 / 1.000 / 0.8365 | 0.8709 / 1.000 / 0.8270 | True |
| D_bc | [.30, .50) | 49 | True | 0.9202 / 1.000 / 0.8545 | 0.9212 / 1.000 / 0.8475 | True |
| D_bc | [.50, inf) | 0 | False | — | — | False |
| I_naive | [0, .15) | 0 | False | — | — | False |
| I_naive | [.15, .30) | 88 | True | 0.8737 / 0.977 / 0.6390 | 0.8719 / 0.977 / 0.5950 | True |
| I_naive | [.30, .50) | 49 | True | 0.7878 / 0.633 / 0.4760 | 0.7798 / 0.653 / 0.4335 | False |
| I_naive | [.50, inf) | 0 | False | — | — | False |

| Index | Validated noise up to | rho 0: failed draws / median abs bias / median SE/SD | rho -.3 |
| :--- | :--- | :--- | :--- |
| D_naive | None | 0 / 0.0207 / 1.211 | 0 / 0.0241 / 1.239 |
| I_bc | 0.5 | 0 / 0.0005 / 0.966 | 0 / 0.0005 / 0.980 |
| H_bc | 0.5 | 0 / 0.0019 / 1.202 | 0 / 0.0018 / 1.221 |
| H_naive | 0.3 | 0 / 0.0105 / 1.239 | 0 / 0.0120 / 1.266 |
| D_bc | 0.5 | 0 / 0.0022 / 0.941 | 0 / 0.0028 / 0.946 |
| I_naive | 0.3 | 0 / 0.0070 / 1.023 | 0 / 0.0083 / 1.038 |

## three groups

137 counties (excluded, fewer than 5 populated tracts: 26003, 26013, 26083, 26085, 26095, 26131, 26153, 36041). Counties per bin: [9, 117, 11, 0].

| Index | Bin | Counties | Judged | rho 0: mean / share >= .80 / min | rho -.3: mean / share >= .80 / min | Passed |
| :--- | :--- | ---: | :--- | :--- | :--- | :--- |
| H_bc | [0, .15) | 9 | True | 0.9446 / 1.000 / 0.9170 | 0.9478 / 1.000 / 0.9105 | True |
| H_bc | [.15, .30) | 117 | True | 0.9660 / 1.000 / 0.9005 | 0.9713 / 1.000 / 0.9025 | True |
| H_bc | [.30, .50) | 11 | True | 0.9973 / 1.000 / 0.9895 | 0.9990 / 1.000 / 0.9970 | True |
| H_bc | [.50, inf) | 0 | False | — | — | False |
| H_naive | [0, .15) | 9 | True | 0.8893 / 0.889 / 0.7815 | 0.8808 / 0.889 / 0.7580 | False |
| H_naive | [.15, .30) | 117 | True | 0.7893 / 0.573 / 0.4190 | 0.7674 / 0.444 / 0.3320 | False |
| H_naive | [.30, .50) | 11 | True | 0.6102 / 0.000 / 0.4220 | 0.5605 / 0.000 / 0.3075 | False |
| H_naive | [.50, inf) | 0 | False | — | — | False |

| Index | Validated noise up to | rho 0: failed draws / median abs bias / median SE/SD | rho -.3 |
| :--- | :--- | :--- | :--- |
| H_bc | 0.5 | 0 / 0.0008 / 1.374 | 0 / 0.0009 / 1.427 |
| H_naive | None | 0 / 0.0089 / 1.400 | 0 / 0.0113 / 1.459 |

Outcomes (validated upper noise level per judged index; null = none): `{"three": {"H_bc": 0.5, "H_naive": null}, "two": {"D_bc": 0.5, "D_naive": null, "H_bc": 0.5, "H_naive": 0.3, "I_bc": 0.5, "I_naive": 0.3}}`.
