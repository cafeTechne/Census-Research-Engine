# Round 107 Validation Report — Final-Wave Exploratory-Measure Repairs

Runtime: 300.6s (`scripts/repairs107_validation.py`, seed `20287107`).

## Verdicts

- **Q2d-prob80** (FH parametric bootstrap PPV, `rule='prob80'`): **PASS** (min coverage 0.875, max 0.915)
- **Q2d-point** (FH parametric bootstrap PPV, `rule='point'` with LL floor): **PASS** (min coverage 0.873, max 0.922)
- **E3b** (Croon/Fuller ecologic slope, `n_j >= 40, J >= 50`): **FAIL** (min coverage 0.825, max 0.905)
- **H2d** (PUMS Hotelling F homogeneity, `min_stratum_n >= 500`): **PASS** (min size 0.068, max 0.128)
- **S2** (Shannon entropy SDR bias correction): **all n FAIL** / **n >= 100 FAIL** (all min 0.856; n>=100 min 0.856)

## Q2d-prob80
| N | A | n_eval | coverage |
| ---: | ---: | ---: | ---: |
| 200 | 0.02 | 400 | 0.875 |
| 200 | 0.08 | 400 | 0.915 |
| 1000 | 0.02 | 400 | 0.892 |
| 1000 | 0.08 | 400 | 0.890 |

## Q2d-point
| N | A | n_eval | coverage |
| ---: | ---: | ---: | ---: |
| 200 | 0.02 | 400 | 0.895 |
| 200 | 0.08 | 400 | 0.922 |
| 1000 | 0.02 | 400 | 0.873 |
| 1000 | 0.08 | 400 | 0.912 |

## E3b
| J | n_j | coverage | bias |
| ---: | ---: | ---: | ---: |
| 50 | 40 | 0.870 | +0.1394 |
| 50 | 80 | 0.880 | +0.0655 |
| 50 | 150 | 0.905 | +0.0305 |
| 150 | 40 | 0.825 | +0.1264 |
| 150 | 80 | 0.900 | +0.0525 |
| 150 | 150 | 0.890 | +0.0480 |

## H2d
| measure | K | n_per_stratum | size |
| :--- | ---: | ---: | ---: |
| rr | 3 | 500 | 0.113 |
| rr | 3 | 800 | 0.102 |
| rr | 5 | 500 | 0.070 |
| rr | 5 | 800 | 0.095 |
| or | 3 | 500 | 0.090 |
| or | 3 | 800 | 0.090 |
| or | 5 | 500 | 0.085 |
| or | 5 | 800 | 0.098 |
| rd | 3 | 500 | 0.072 |
| rd | 3 | 800 | 0.107 |
| rd | 5 | 500 | 0.128 |
| rd | 5 | 800 | 0.068 |

## S2
| G | n_resp | coverage | bias |
| ---: | ---: | ---: | ---: |
| 4 | 50 | 0.866 | +0.0041 |
| 4 | 100 | 0.878 | -0.0081 |
| 4 | 200 | 0.886 | -0.0021 |
| 6 | 50 | 0.868 | +0.0025 |
| 6 | 100 | 0.856 | +0.0013 |
| 6 | 200 | 0.904 | -0.0004 |
