# Negative replicate estimates: validation (Round 51)

A. Segregation: Round 50 design with Gaussian replicates (negative counts clipped at zero before the index refits); Round 50 bin rule plus an affected-draw check (pooled coverage >= .86 over county-draws with a clipped replicate, inside the validated range). B. SMR: negative band replicates accepted as published or clipped; coverage >= .86 in all eight cells. Failed or refused draws count as non-coverage.

Criterion commit: `2837bfb`. 2,000 draws per cell.

## A. Segregation, two groups

137 counties; per bin: [0, 88, 49, 0]. Share of populated tract-group cells with a negative replicate: rho 0.0: 0.040, rho -0.3: 0.040.

| Index | Bin | Counties | Judged | rho 0: mean / share >= .80 / min | rho -.3: mean / share >= .80 / min | Passed |
| :--- | :--- | ---: | :--- | :--- | :--- | :--- |
| D_naive | [0, .15) | 0 | False | — | — | False |
| D_naive | [.15, .30) | 88 | True | 0.8703 / 0.909 / 0.5650 | 0.8647 / 0.886 / 0.5025 | False |
| D_naive | [.30, .50) | 49 | True | 0.7282 / 0.408 / 0.2320 | 0.7079 / 0.347 / 0.1590 | False |
| D_naive | [.50, inf) | 0 | False | — | — | False |
| I_bc | [0, .15) | 0 | False | — | — | False |
| I_bc | [.15, .30) | 88 | True | 0.8786 / 1.000 / 0.8370 | 0.8818 / 1.000 / 0.8445 | True |
| I_bc | [.30, .50) | 49 | True | 0.9109 / 1.000 / 0.8435 | 0.9154 / 1.000 / 0.8350 | True |
| I_bc | [.50, inf) | 0 | False | — | — | False |
| H_bc | [0, .15) | 0 | False | — | — | False |
| H_bc | [.15, .30) | 88 | True | 0.9275 / 1.000 / 0.8735 | 0.9306 / 1.000 / 0.8770 | True |
| H_bc | [.30, .50) | 49 | True | 0.9673 / 1.000 / 0.9085 | 0.9689 / 1.000 / 0.9180 | True |
| H_bc | [.50, inf) | 0 | False | — | — | False |
| H_naive | [0, .15) | 0 | False | — | — | False |
| H_naive | [.15, .30) | 88 | True | 0.9060 / 0.989 / 0.6095 | 0.9039 / 0.977 / 0.5705 | True |
| H_naive | [.30, .50) | 49 | True | 0.8101 / 0.694 / 0.5825 | 0.7958 / 0.612 / 0.5085 | False |
| H_naive | [.50, inf) | 0 | False | — | — | False |
| D_bc | [0, .15) | 0 | False | — | — | False |
| D_bc | [.15, .30) | 88 | True | 0.8713 / 1.000 / 0.8170 | 0.8722 / 1.000 / 0.8300 | True |
| D_bc | [.30, .50) | 49 | True | 0.9156 / 1.000 / 0.8435 | 0.9182 / 1.000 / 0.8560 | True |
| D_bc | [.50, inf) | 0 | False | — | — | False |
| I_naive | [0, .15) | 0 | False | — | — | False |
| I_naive | [.15, .30) | 88 | True | 0.8701 / 0.989 / 0.6420 | 0.8703 / 0.989 / 0.6020 | True |
| I_naive | [.30, .50) | 49 | True | 0.7841 / 0.633 / 0.4650 | 0.7738 / 0.612 / 0.4295 | False |
| I_naive | [.50, inf) | 0 | False | — | — | False |

| Index | Clipped range up to | Round 50 range up to | Affected pairs / coverage (rho 0; rho -.3) | Affected check | Clip validated up to |
| :--- | :--- | :--- | :--- | :--- | :--- |
| D_naive | None | None | 0 / —; 0 / — | not judged | None |
| I_bc | 0.5 | 0.5 | 133864 / 0.9029; 134118 / 0.9072 | passed | 0.5 |
| H_bc | 0.5 | 0.5 | 133864 / 0.9645; 134118 / 0.9666 | passed | 0.5 |
| H_naive | 0.3 | 0.3 | 45599 / 0.8606; 45512 / 0.8512 | failed | None |
| D_bc | 0.5 | 0.5 | 133864 / 0.9040; 134118 / 0.9060 | passed | 0.5 |
| I_naive | 0.3 | 0.3 | 45599 / 0.8478; 45512 / 0.8481 | failed | None |

## A. Segregation, three groups

137 counties; per bin: [9, 117, 11, 0]. Share of populated tract-group cells with a negative replicate: rho 0.0: 0.026, rho -0.3: 0.026.

| Index | Bin | Counties | Judged | rho 0: mean / share >= .80 / min | rho -.3: mean / share >= .80 / min | Passed |
| :--- | :--- | ---: | :--- | :--- | :--- | :--- |
| H_bc | [0, .15) | 9 | True | 0.9451 / 1.000 / 0.9070 | 0.9500 / 1.000 / 0.9145 | True |
| H_bc | [.15, .30) | 117 | True | 0.9665 / 1.000 / 0.8920 | 0.9722 / 1.000 / 0.9035 | True |
| H_bc | [.30, .50) | 11 | True | 0.9981 / 1.000 / 0.9935 | 0.9992 / 1.000 / 0.9960 | True |
| H_bc | [.50, inf) | 0 | False | — | — | False |
| H_naive | [0, .15) | 9 | True | 0.8911 / 0.889 / 0.7835 | 0.8888 / 0.889 / 0.7800 | False |
| H_naive | [.15, .30) | 117 | True | 0.7992 / 0.615 / 0.4200 | 0.7775 / 0.513 / 0.3625 | False |
| H_naive | [.30, .50) | 11 | True | 0.6084 / 0.000 / 0.4525 | 0.5577 / 0.000 / 0.3565 | False |
| H_naive | [.50, inf) | 0 | False | — | — | False |

| Index | Clipped range up to | Round 50 range up to | Affected pairs / coverage (rho 0; rho -.3) | Affected check | Clip validated up to |
| :--- | :--- | :--- | :--- | :--- | :--- |
| H_bc | 0.5 | 0.5 | 111271 / 0.9880; 111440 / 0.9907 | passed | 0.5 |
| H_naive | None | None | 0 / —; 0 / — | not judged | None |

## B. SMR

| E | High-CV band | CV | Draws with a negative band replicate | accept: coverage / refused | clip: coverage / refused |
| ---: | ---: | ---: | ---: | :--- | :--- |
| 10 | 1 | 0.6 | 0.389 | 0.9170 / 0 | 0.9170 / 0 |
| 10 | 1 | 1.0 | 0.693 | 0.9160 / 0 | 0.9160 / 0 |
| 10 | 4 | 0.6 | 0.390 | 0.9030 / 0 | 0.9010 / 0 |
| 10 | 4 | 1.0 | 0.701 | 0.9150 / 0 | 0.8945 / 0 |
| 100 | 1 | 0.6 | 0.391 | 0.9035 / 0 | 0.9030 / 0 |
| 100 | 1 | 1.0 | 0.704 | 0.9030 / 0 | 0.9030 / 0 |
| 100 | 4 | 0.6 | 0.392 | 0.9155 / 0 | 0.9025 / 0 |
| 100 | 4 | 1.0 | 0.700 | 0.9220 / 0 | 0.8910 / 0 |

Outcomes: `{"segregation_clip": {"three": {"H_bc": 0.5, "H_naive": null}, "two": {"D_bc": 0.5, "D_naive": null, "H_bc": 0.5, "H_naive": null, "I_bc": 0.5, "I_naive": null}}, "smr": {"accept": true, "clip": true}}`.
