# Cunningham, *Causal Inference: The Mixtape*: guidance mapped to engine work

Source: Cunningham S. *Causal Inference: The Mixtape* (2018 edition, 328 pages;
`literature_pdfs/Cunningham-Cuasal-Inference-the-Mixtape.pdf`). Published by Yale University Press, 2021. Mapping by
the maintainer agent, used to draft Rounds 98–99 (backlog N75–N76). Author self-review, not independent.

| Chapter | Guidance | Engine today | Planned |
| :--- | :--- | :--- | :--- |
| Probability, regression, DAGs | Regression anatomy, collider bias, backdoor paths | Covered (Round 89 DAG checks) | — |
| Potential outcomes | ATE, ATT, selection bias, SUTVA | Covered (Rounds 41, 89–90) | — |
| Matching and subclassification | Subclassification (Cochran 1968); exact, nearest-neighbour and **bias-corrected matching** (Abadie and Imbens); **coarsened exact matching**; propensity scores and common support (Dehejia and Wahba) | IPW, AIPW and RA (Round 41); positivity diagnostics (Round 90); no matching estimators | 99: nearest-neighbour matching with bias correction and Abadie–Imbens SEs; coarsened exact matching |
| Regression discontinuity | Sharp and fuzzy RDD; local polynomial estimation; bandwidth choice; **density (McCrary) test**; covariate balance at the cutoff; regression kink; Card, Dobkin and Maestas (2008): insurance at age 65 | None | 98: RDD with robust bias-corrected intervals, density and placebo tests; PUMS example at age 65 |
| Instrumental variables | 2SLS, weak instruments, LATE | Covered (Rounds 41, 47) | — |
| Panel data | Fixed effects, clustered SEs | Covered | — |
| Difference-in-differences | Parallel trends, event studies, **triple differences** (Gruber 1994) | DiD, staggered DiD (Rounds 25, 78), MSMs (Round 91); no triple differences | 99: triple-difference design |
| Synthetic control | Abadie, Diamond and Hainmueller; placebo inference | Round 78: failed validation (exploratory) | — |
