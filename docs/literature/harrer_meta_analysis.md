# Harrer et al., *Doing Meta-Analysis with R*: guidance mapped to engine work

Source: Harrer M, Cuijpers P, Furukawa TA, Ebert DD. *Doing Meta-Analysis with R: A Hands-On Guide*. Chapman &
Hall/CRC, 2021 (online edition https://doing-meta.guide/, read 2026-11-23; the PDF preview in `literature_pdfs/` is
damaged and could not be read). Mapping by the maintainer agent, used to draft Round 102 (backlog N79). Author
self-review, not independent.

| Chapter | Guidance | Engine today (`combine_estimates`, Rounds 38, 48) | Planned |
| :--- | :--- | :--- | :--- |
| 4 Pooling | Inverse-variance random effects; τ² by REML (continuous outcomes), Paule–Mandel (binary), DerSimonian–Laird only for comparability; Knapp–Hartung "usually sensible" | Paule–Mandel + Hartung–Knapp (validated up to 10 estimates, truncated) | 102: REML τ² option |
| 5 Heterogeneity | Report τ², I² with its CI, and the **prediction interval**; do not rely on the Q test; influence diagnostics (leave-one-out, Baujat) | Q, I², a prediction interval (never validated) | 102: validated prediction interval; I² CI (Q-profile); leave-one-out |
| 7–8 Subgroups and meta-regression | Fewer than 10 studies is too few; Knapp–Hartung for meta-regression; permutation tests; no stepwise selection | None | 102: meta-regression with Knapp–Hartung and permutation p-values |
| 9 Publication bias | Egger's and Peters' tests only with K ≥ 10; trim-and-fill, PET-PEESE, selection models; use several | None (pooled areas, not publications) | 102: Egger test with the K ≥ 10 gate, for pooling published estimates (replications) |
| 10 Multilevel | Three-level models; robust variance estimation (CR2) | None | Not planned (few nested estimates in this engine) |
| 13–14 Bayesian, power | Weakly informative priors; power for pooled effects | Power for z tests (Round 38) | — |
