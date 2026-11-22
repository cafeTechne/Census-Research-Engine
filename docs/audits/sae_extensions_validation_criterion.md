# Round 80 criterion: arcsine Fay–Herriot for proportions and Rao–Yu temporal Fay–Herriot

Committed before the full run. Author self-review, not independent. Frozen with `validate_pins`:
- `scripts/sae_extensions_validation.py`;
- `census/sae_extensions_core.py` (new);
- the design file `docs/audits/sae_extensions_neff.csv.gz`;
- this file.

**Seen before this commit:**
- the design file. It holds effective sample sizes from the 2019–2023 S2701 percent uninsured and its MOE: MI/NY
  counties (83 and 62) and tracts (2,868 and 5,176). Areas with a published 0 or 100% or a zero MOE are omitted;
- one smoke run (2 draws per cell), which only checked that the script runs;
- timing probes: arcsine FH with 200 bootstrap fits took 1.1 s on 5,176 tracts; Rao–Yu with 100 bootstrap fits took
  1.8 s on 145 counties.

## Methods (`census/sae_extensions_core.py`)

- **P1: arcsine-square-root Fay–Herriot.**
  - D_i = 1/(4 n_eff), which stays positive for a direct estimate of 0. REML estimates the model variance.
  - The back-transform is bias-corrected, E[sin² t] with t ~ N(θ̂, γD).
  - MSE comes from a parametric bootstrap with B = 200.
  - Interval: a normal interval from the bootstrap MSE, clipped to [0, 1].
- **P1q:** the same estimate, with bootstrap-error quantile intervals.
- **P1b:** the naive back-transform sin²(θ̂). Reported only.
- **T1: Rao–Yu.**
  - The model has an area effect plus a stationary AR(1) area-time effect, fitted by REML (L-BFGS-B). The
    prediction target is the last release.
  - MSE comes from a parametric bootstrap with B = 100.
  - **Deviation from the plan, made before any run:** a parametric bootstrap MSE replaces the Prasad–Rao-type
    analytic MSE. The second-order term for three variance parameters was not implemented, and the bootstrap
    matches P1.
- **Comparison:** single-release FH on the last release, with the g1 + g2 MSE.

## Designs (500 draws per cell)

- **P1 (8 cells).** Four geometries (MI county, NY county, MI tract, NY tract) × σ_u ∈ {.05, .10} on the arcsine
  scale. This puts true proportions at about .01–.45.
  - Each area has one covariate.
  - Direct estimates are binomial counts over the rounded n_eff.
- **T1 (8 cells).** Two geometries × 2 or 3 releases × ρ ∈ {.3, .8}.
  - Geometries: the 145 MI+NY counties, and 300 MI tracts sampled once.
  - Area-effect SD .05; AR(1) innovation SD .05; sampling variance 1/(4 n_eff) per release.
  - **Deviation from the plan, made before any run:** T1 uses a 300-tract sample rather than all tracts, because
    of the bootstrap refits.

## Pass rules

- **P1 and P1q (judged separately):** in every cell,
  - mean per-area coverage ≥ .86;
  - the 10th percentile of per-area coverage ≥ .80;
  - |relative bias| ≤ .10 among area-draws with p < .10.
- **T1:** mean per-area coverage of the last-release value ≥ .86 in every cell. The MSE gain over single-release
  FH is reported.

Seeds: `[20282001 + cell, draw]` for P1; `[20282051 + cell, draw]` for T1.

## Engine (only what passes)

- `small_area_estimates(transform="arcsine")` (passing interval: P1, else P1q).
- `small_area_estimates(temporal=True, release_column="Year")` (T1).
- Manifest `fay_herriot` `args.transform` and `args.temporal`.
- **Refused:**
  - overlapping releases;
  - for P1, a direct variance of 0 together with a direct estimate strictly between 0 and 1.
