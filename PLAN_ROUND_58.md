# Round 58 plan: spatial inference outside MI/NY

**Goal.** Backlog issues N31 and N34 (`ROADMAP_BACKLOG.md` Round 58).

Round 54 found three problems:
- **Naive IM-8 outside MI/NY.** Naive IM-8 (Round 30's observed-estimate slope) under-covers on OH/PA when fields
  are spatially correlated (.72–.87), and 4 or 6 within-state clusters did not repair it.
- **Corrected slopes with many covariates.** G1 with three to five error-prone covariates and G2 with five failed on
  OH/PA at reliability .7 with correlated fields.
- **A doubtful MI/NY cell.** A fresh-seed MI/NY rerun of IM-8 covered .849 in one cell (linear, 100 km, reliability
  .7), where Round 30 had .885.

IM-8 assumes the eight clusters are independent. OH and PA share a border, so neighbouring clusters are not.

N34: corrected binomial slopes under spatial dependence were never tested (Round 53 covered Poisson and NB2).

Version 0.55.0. Baseline: the Round 57 suite. Branch `phase58/spatial-outside-miny`. Validation first.

## 1. Frozen core (`census/scpc_core.py`)

SCPC (Müller and Watson 2022, *Econometrica*), spatial-correlation-robust inference for a scalar parameter from
influence values e_l at locations with distances d_lk (great-circle km):
- **Benchmark.** c̄ solves mean_{l≠k} exp(−c̄ d_lk) = ρ̄. The weights W are the eigenvectors of the q largest
  eigenvalues of M Σ(c̄) M (M demeans, Σ(c) = exp(−c d)), with unit norm.
- **Statistic.** τ = (ι'e/√n) / √(q⁻¹ Σ_j (w_j'e)²). The critical value is the largest, over a grid of c ≥ c̄ (30
  log-spaced values up to an average correlation of 10⁻⁴, plus independence), of the 1 − α quantile of |τ| under
  Gaussian e with covariance Σ(c). It is computed exactly with Imhof's formula.
- **q** ∈ {1, …, 20} minimises cv(q)·E√(χ²_q/q), the expected length under independence.
- **Interval.** θ̂ ± cv · √(q⁻¹ Σ_j (w_j'e)²)/√n.
- **Influence values.** For OLS, e_l = n[(X'X)⁻¹ x_l û_l]_j. For binomial (trials) and Poisson (exposure) GLMs,
  e_l = n[I⁻¹ x_l (y_l − μ̂_l)]_j with the canonical-link information I.
- **ρ̄ variants: .05 and .10.** The authors' default .02 implies only a 38 km benchmark range on MI/NY. The
  influence values here are products of two fields with a 100 km range, so they behave like a 50 km field, whose
  average pairwise correlation is .033 on MI/NY and .046 on OH/PA. ρ̄ = .05 covers that, and .10 covers a 100 km
  score field. The engine uses the smallest ρ̄ that passes.

## 2. Validation (`scripts/spatial_outside_validation.py` → `docs/audits/spatial_outside_validation.md`/`.json`)

2,000 draws per cell unless stated; per-draw seeds `[20280401 + cell, draw]`.

- **N (24 cells): naive slopes.** Round 30's C1 cells (linear/binomial/Poisson × range {0, 100} km × reliability
  {.9, .7}; `im_acs_validation` `setup`/`outcome`) on MI/NY and OH/PA, Round 54's generator. Procedures: SCPC
  with ρ̄ = .05 and .10, plus IM-8 (comparison) on the same draw. Target: each geometry's observed-estimate β*
  (Rounds 30 and 44 reference files).
- **R (3 cells, 10,000 draws): the doubtful MI/NY cells.** Linear, binomial and Poisson at 100 km, reliability
  .7, on MI/NY: IM-8 and SCPC.
- **G (12 cells): a reliability gate for G1/G2.** p ∈ {3, 4, 5} × geometry {MI/NY, OH/PA} × range {0, 100} km at
  reliability .8 (Round 53's M generator with the state indicator). Target .5.
- **B (4 cells): calibrated binomial slopes with IM-8.** MI/NY, reliability {.9, .7} × range {0, 100}; Round
  53's S design with a binomial outcome (trials lognormal, median 3,900; logit −2.6 + .3x₁ + .3x₂ + .3·NY + .15 ×
  field). `rc_im` with binomial cluster GLMs. Target .3.

**Acceptance.** Coverage ≥ .86 in every cell of the problem:
- SCPC per ρ̄ and model, over N (both geometries) and R;
- G1 and G2 per p, over G;
- B1 over B.

Failed fits count as non-coverage. R also reports the 10,000-draw IM-8 coverage for the record.

## 3. Engine (only what passes)

- **SCPC.** If SCPC passes, add `fit_replicate(..., spatial_scpc={"rho_bar": ρ̄})` (smallest passing ρ̄) for
  linear, binomial and Poisson naive slopes, using the GEOIDs' representative points. Make it the recommended
  spatial interval outside MI/NY. Manifests get `args.spatial_scpc`; registered manifests are unchanged.
- **IM-8.** If the R cells' 10,000-draw IM-8 coverage is below .86, IM-8 gets a note for reliability below .8,
  and the MI/NY note recommends SCPC where it passes.
- **Spatial EIV.** If the G cells pass, spatial EIV outside MI/NY with three to five error-prone covariates is
  validated when every error-prone covariate's estimated reliability is ≥ .8 (the replicate-based ratio already
  reported); otherwise the note stays.
- **Binomial calibrated slopes.** If B passes, `fit_count_model`'s calibrated IM-8 route gets a binomial
  counterpart (`regression_calibration(..., spatial="clusters")` for binomial).
- Rule text mirrored; STATUS, CHANGELOG, version, compatibility audit; tests (flags = audit, SCPC against a
  brute-force simulation of its critical value); goldens identical.
- **Exploratory example:** OH/PA county child poverty (Round 54's frame), with SCPC next to IM-8 and HC3.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Core, script, criterion commit | done | SCPC size checked by simulation (.1014); `e8c6c8c` |
| N / R / G / B results | done | SCPC passes OLS (.05) and Poisson (.10), fails binomial; IM-8 OLS cell .858; G gate .8 passes; B passes (`19ef455`) |
| Engine, tests | done | `census.scpc`, MCP `spatial="scpc"`, binomial RC clusters, reliability gate; 7 new tests |
| Example | done | OH/PA child poverty with SCPC; `/tmp/r58_example_outputs.tar.gz` |
| Goldens, final suite | done | identical; 2112 passed, 37 skipped |
| Exceptions | see notes | SCPC ρ̄ variants .05/.10 instead of .02/.05 (set before freezing, documented); no manifest SCPC option yet |
