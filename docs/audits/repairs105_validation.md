# Round 105: second-wave exploratory-measure repairs validation

Elapsed: 178.1s. Frozen SHA-256: `{'census/repairs105_core.py': '49d08d1dab9804c8', 'scripts/repairs105_validation.py': '404f3e39f05b1640', 'docs/audits/repairs105_criterion.md': '25d76abb51957f1a'}`. 90% intervals (pass ≥ .86; H2b size ≤ .13). Author self-review, not independent.

## Outcomes

| Candidate | Outcome |
| :--- | :--- |
| `R1b_all` | **pass** |
| `H2b_all` | fail |
| `Q2b_all` | fail |
| `M1b_all` | **pass** |
| `M4_all` | fail |

## Continuous RDD (R1b: CER bandwidth)

| n | c2 | c3 | R1b coverage |
| ---: | ---: | ---: | ---: |
| 2000 | 0.0 | 0.0 | 0.917 |
| 2000 | 0.0 | 3.0 | 0.890 |
| 2000 | 2.0 | 0.0 | 0.915 |
| 2000 | 2.0 | 3.0 | 0.877 |
| 10000 | 0.0 | 0.0 | 0.903 |
| 10000 | 0.0 | 3.0 | 0.895 |
| 10000 | 2.0 | 0.0 | 0.920 |
| 10000 | 2.0 | 3.0 | 0.889 |

## PUMS replicate Wald homogeneity (H2b: Hotelling F)

| K | n/stratum | RR size | OR size | RD size |
| ---: | ---: | ---: | ---: | ---: |
| 3 | 300 | 0.102 | 0.104 | 0.117 |
| 3 | 1000 | 0.112 | 0.115 | 0.157 |
| 5 | 300 | 0.126 | 0.129 | 0.184 |
| 5 | 1000 | 0.103 | 0.120 | 0.262 |

## Designation PPV predictive interval (Q2b: FH parametric bootstrap)

| N | A | Rule | Q2b coverage |
| ---: | ---: | :--- | ---: |
| 200 | 0.005 | point | 0.858 |
| 200 | 0.005 | prob80 | 0.973 |
| 200 | 0.02 | point | 0.848 |
| 200 | 0.02 | prob80 | 0.975 |
| 1000 | 0.005 | point | 0.853 |
| 1000 | 0.005 | prob80 | 0.963 |
| 1000 | 0.02 | point | 0.843 |
| 1000 | 0.02 | prob80 | 0.970 |

## Probabilistic misclassification (M1b: propagated sampling)

| Kind | True RR | Diff | RR cov | OR cov |
| :--- | ---: | :--- | ---: | ---: |
| outcome | 1.0 | False | 0.898 | 0.898 |
| outcome | 1.5 | False | 0.895 | 0.890 |
| outcome | 1.5 | True | 0.894 | 0.896 |
| exposure | 1.0 | False | 0.908 | 0.908 |
| exposure | 1.5 | False | 0.896 | 0.897 |

## IP-weighted MSM (M4: Firth logit + L0 + cluster jackknife)

| K | Feedback | psi | M4 cov (d1/d2/d3) | M4 bias (d1/d2/d3) |
| ---: | ---: | ---: | :--- | :--- |
| 12 | 0.0 | 0.0 | 0.888/0.918/0.922 | +0.087/+0.031/-0.000 |
| 12 | 0.0 | -2.0 | 0.890/0.902/0.892 | +0.118/+0.043/-0.019 |
| 12 | 0.5 | 0.0 | 0.884/0.874/0.892 | +0.069/+0.035/+0.016 |
| 12 | 0.5 | -2.0 | 0.876/0.884/0.910 | +0.117/+0.058/+0.016 |
| 12 | 1.0 | 0.0 | 0.884/0.914/0.890 | +0.103/+0.043/+0.013 |
| 12 | 1.0 | -2.0 | 0.872/0.882/0.886 | +0.119/+0.046/+0.000 |
| 18 | 0.0 | 0.0 | 0.880/0.918/0.914 | +0.092/+0.063/+0.019 |
| 18 | 0.0 | -2.0 | 0.874/0.890/0.902 | +0.121/+0.065/-0.013 |
| 18 | 0.5 | 0.0 | 0.882/0.902/0.932 | +0.085/+0.044/-0.005 |
| 18 | 0.5 | -2.0 | 0.852/0.898/0.898 | +0.142/+0.069/+0.052 |
| 18 | 1.0 | 0.0 | 0.832/0.910/0.908 | +0.097/+0.057/+0.032 |
| 18 | 1.0 | -2.0 | 0.870/0.908/0.898 | +0.093/+0.056/+0.011 |
