# van Buuren, *Flexible Imputation of Missing Data*: guidance mapped to engine work

Source: van Buuren S. *Flexible Imputation of Missing Data*. Chapman & Hall/CRC, 2012 (1st edition;
`literature_pdfs/fimd.pdf`). Mapping by the maintainer agent, used to draft Round 100 (backlog N77). Author
self-review, not independent.

| Chapter | Guidance | Engine today | Planned |
| :--- | :--- | :--- | :--- |
| 1–2 | MCAR/MAR/MNAR; Rubin's rules; Barnard–Rubin degrees of freedom; fraction of missing information; number of imputations | Rubin's rules and Barnard–Rubin df (Rounds 42, 47) | 100: report the fraction of missing information and λ |
| 3 | Univariate imputation: Bayesian linear regression, **predictive mean matching** (observed donors; keeps bounds and skew), logistic and polytomous models; **sensitivity analysis with δ-adjustment** | Normal-model imputation of one or two covariates | 100: PMM; δ-adjustment sensitivity |
| 4–5 | Multivariate missing data by fully conditional specification (MICE): visit sequence, convergence, predictor selection, passive imputation of derived variables | Chained equations for two covariates (Round 47) | 100: FCS for any number of incomplete variables, with passive derived variables |
| 6 | Analysis of imputed data; pooling non-normal quantities (transform first) | Partly | 100: pooling on transformed scales |
| 7–9 | Case studies; δ-adjustment for MNAR; reporting guidelines | — | 100: reporting block in results |
