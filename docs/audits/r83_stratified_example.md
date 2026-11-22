# Round 83 example: uninsurance by disability, stratified by age (Michigan PUMS 2019-2023, adults 19-64)

Exploratory; author self-review, not independent. Outcome uninsured; exposure any disability; SDR 90% intervals. Records per stratum: 19-34: 88,828, 35-49: 82,227, 50-64: 111,377.

| Measure | Crude | Age 19-34 | Age 35-49 | Age 50-64 | MH pooled (90% CI) | Label |
| :--- | ---: | ---: | ---: | ---: | :--- | :--- |
| RR | 0.805 | 0.956 | 0.882 | 0.789 | 0.875 (0.836 to 0.915) | effect_modifier |
| OR | 0.792 | 0.952 | 0.873 | 0.779 | 0.865 (0.824 to 0.909) | effect_modifier |
| RD | -0.015 | -0.004 | -0.010 | -0.012 | -0.009 (-0.012 to -0.006) | confounder |

Homogeneity (replicate Wald, exploratory): RR p = 0.026, OR p = 0.032, RD p = 0.348.

Additive interaction of disability and male sex: RERI 0.051 (90% CI -0.057 to 0.160); AP 0.038; S 1.171.
