# Combining evidence: validation (Round 38)

pooled: 90% coverage >= .86 per k (fixed only without heterogeneity; dl, hksj in all cells); TOST: size at the margin <= .07 (nominal .05); power: |predicted - empirical| <= .03.

Criterion commit: `3edd5f4`.

| k | heterogeneity | fixed | DerSimonian–Laird | Paule–Mandel + HKSJ |
| ---: | :--- | ---: | ---: | ---: |
| 2 | False | 0.8975 | 0.9230 | 0.8850 |
| 2 | True | 0.7245 | 0.8180 | 0.9105 |
| 4 | False | 0.8835 | 0.9130 | 0.8920 |
| 4 | True | 0.7030 | 0.8405 | 0.8850 |
| 8 | False | 0.8900 | 0.9160 | 0.8890 |
| 8 | True | 0.4360 | 0.8170 | 0.8550 |

| TOST SEs | margin | size at margin | power at 0 |
| :--- | ---: | ---: | ---: |
| (1.0, 1.0) | 3.0 | 0.0458 | 0.3716 |
| (1.0, 2.0) | 3.0 | 0.0000 | 0.0000 |

| α | predicted power | empirical |
| ---: | ---: | ---: |
| 0.1 | 0.501 | 0.5079 |
| 0.1 | 0.800 | 0.7998 |
| 0.05 | 0.500 | 0.5063 |
| 0.05 | 0.800 | 0.7958 |

Outcomes: `{"dl/k2": false, "dl/k4": false, "dl/k8": false, "fixed/k2": true, "fixed/k4": true, "fixed/k8": true, "hksj/k2": true, "hksj/k4": true, "hksj/k8": false, "power": true, "tost": true}`.
