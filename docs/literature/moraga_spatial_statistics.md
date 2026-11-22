# Moraga, *Spatial Statistics for Data Science*: guidance mapped to engine work

Source: Moraga P. *Spatial Statistics for Data Science: Theory and Practice with R*. Chapman & Hall/CRC Data Science
Series, 2023 (online edition https://www.paulamoraga.com/book-spatial/, CC BY-NC-ND 4.0; read 2026-11-23, all 23
chapters). Summary and mapping by the maintainer agent, used to draft Rounds 96–97 (backlog N73–N74). Author
self-review, not independent.

| Chapters | Guidance | Engine today | Planned |
| :--- | :--- | :--- | :--- |
| 1–6 | Spatial data types, sf/terra, CRS, maps, open-data packages | Boundaries, maps, context sources: covered | — |
| 7–8 | Neighbourhood matrices (contiguity, k-NN, distance bands, higher orders); global and local Moran's I with permutation inference | Covered (`spatial_autocorrelation`; Round 22 LISA, BH correction) | — |
| 9–10 | Disease mapping: SMR = O/E with indirectly standardized expected counts; Poisson model log θ = β + Besag ICAR + iid (BYM/BYM2) fitted by INLA; relative risks shrunk toward 1; **exceedance probabilities** P(θ > c) | SMR (Round 29), empirical-Bayes Poisson–gamma smoothing (Round 27), spatial Fay–Herriot (Gaussian). No count-scale spatial model and no exceedance probabilities | 96: BYM2 Poisson disease mapping (Laplace approximation, no INLA dependency) with exceedance probabilities, validated against planted risks |
| 11 | Misaligned data, the modifiable areal unit problem (scale and zoning effects), ecological fallacy; data fusion by melding | Ecologic checks (Round 87), crosswalks; no MAUP sensitivity analysis | 97: MAUP sensitivity (the same analysis at several scales and over random zonings) |
| 12–15 | Gaussian random fields, variograms, kriging, model-based geostatistics (SPDE) | Not applicable to ACS areal estimates (no point-referenced data); left out | — |
| 16 | Predictive assessment: MAE, RMSE, interval coverage, CRPS; random cross-validation overstates skill under spatial autocorrelation, so use **spatial block cross-validation** | Model checks are in-sample | 97: spatial block cross-validation for small-area and regression models |
| 17–23 | Point patterns (intensity, CSR, K-function, log-Gaussian Cox processes) | No point data in the engine's sources; left out | — |
