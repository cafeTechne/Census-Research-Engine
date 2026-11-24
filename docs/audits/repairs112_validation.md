# Round 112 Validation Report — Final Repairable Exploratory Wave

Runtime: 4316.2s (`scripts/repairs112_validation.py`, seed `20292112`).

## Verdicts

- **M3b**: **FAIL**
- **Q2e-lower**: **PASS**
- **Q2e-prob50**: **FAIL**
- **D2-idisp**: **PASS**
- **D2-bgv**: **PASS**
- **D2-theil**: **PASS**
- **D2-mld**: **PASS**
- **R2_dens**: **PASS**
- **W3_rr**: **FAIL**

## M3b (Three-level variance shares)
| G_top | split | share | coverage |
| ---: | :--- | :--- | ---: |
| 30 | 70_15_15 | bottom | 0.930 |
| 30 | 70_15_15 | mid | 0.890 |
| 30 | 70_15_15 | top | 0.930 |
| 30 | 50_25_25 | bottom | 0.850 |
| 30 | 50_25_25 | mid | 0.880 |
| 30 | 50_25_25 | top | 0.885 |
| 49 | 70_15_15 | bottom | 0.920 |
| 49 | 70_15_15 | mid | 0.910 |
| 49 | 70_15_15 | top | 0.925 |
| 49 | 50_25_25 | bottom | 0.895 |
| 49 | 50_25_25 | mid | 0.895 |
| 49 | 50_25_25 | top | 0.895 |

## Q2e-lower
| N | A | n_eval | coverage |
| ---: | ---: | ---: | ---: |
| 200 | 0.02 | 300 | 0.897 |
| 200 | 0.08 | 300 | 0.900 |
| 1000 | 0.02 | 300 | 0.890 |
| 1000 | 0.08 | 300 | 0.917 |

## Q2e-prob50
| N | A | n_eval | coverage |
| ---: | ---: | ---: | ---: |
| 200 | 0.02 | 300 | 0.847 |
| 200 | 0.08 | 300 | 0.867 |
| 1000 | 0.02 | 300 | 0.887 |
| 1000 | 0.08 | 300 | 0.870 |

## D2 (Count disparity indices, min_events >= 100)
| index | min_cov | max_cov |
| :--- | ---: | ---: |
| idisp | 0.880 | 0.920 |
| bgv | 0.870 | 0.907 |
| theil | 0.863 | 0.903 |
| mld | 0.870 | 0.913 |

## R2_dens (RDD density test)
| dist | n | size |
| :--- | ---: | ---: |
| uniform | 1000 | 0.120 |
| uniform | 5000 | 0.120 |
| normal | 1000 | 0.087 |
| normal | 5000 | 0.083 |
| beta22 | 1000 | 0.122 |
| beta22 | 5000 | 0.110 |

## W3_rr (Stratified RR homogeneity, min_cases >= 15)
| K | min_cases | size |
| ---: | ---: | ---: |
| 3 | 15 | 0.065 |
| 3 | 40 | 0.080 |
| 5 | 15 | 0.098 |
| 5 | 40 | 0.135 |
