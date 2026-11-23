# Round 96 example: BYM2 drug-overdose relative risks, Michigan counties, 2018-2022 (exploratory)

Author self-review, not independent; not a registered study. Observed deaths from the owner's county WONDER export; expected deaths from national age x sex rates and each county's ACS age x sex mix and WONDER person-years. Only smoothed relative risks, intervals and probabilities are shown (no counts).

83 counties; 12 with suppressed counts predicted from neighbours; 6 with P(RR > 1.2) >= .8; 70 with P(RR > 1.2) <= .2.

Highest smoothed relative risks:

| County | RR | 90% interval | P(RR > 1.2) | Count used |
| :--- | ---: | :--- | ---: | :--- |
| 26049 | 1.92 | 1.82-2.02 | 1.00 | yes |
| 26163 | 1.78 | 1.73-1.82 | 1.00 | yes |
| 26025 | 1.47 | 1.33-1.63 | 1.00 | yes |
| 26065 | 1.45 | 1.35-1.56 | 1.00 | yes |
| 26069 | 1.32 | 1.05-1.68 | 0.76 | yes |
| 26099 | 1.30 | 1.24-1.35 | 1.00 | yes |
| 26147 | 1.28 | 1.16-1.41 | 0.85 | yes |
| 26101 | 1.26 | 0.99-1.59 | 0.63 | yes |

Notes: BYM2 Poisson model (scaled ICAR + unstructured effects), Laplace approximation; relative risks are shrunk toward the neighbourhood and overall level (Moraga 2023 ch. 10). Hyperparameters: sigma 0.407, phi 0.35 (share of spatially structured variance). 12 area(s) with suppressed counts: relative risks predicted from neighbours only (not validated; nothing derived from the hidden counts). Relative-risk intervals are exploratory: they under-covered (.79-.80) with very small expected counts (median 5) across few areas, and covered .84-.90 otherwise (docs/audits/disease_mapping_validation.md). Exceedance probabilities were calibrated in validation. The contiguity graph had separate parts; 1 bridge edge(s) join each part to its nearest area: [['26097', '26047']].
