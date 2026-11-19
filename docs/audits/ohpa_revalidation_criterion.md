# Round 44: pre-set criterion (OH/PA re-check and Round 29 post hoc)

Frozen with `scripts/ohpa_spatial_revalidation.py`, `scripts/r44_posthoc_r29.py` and
`docs/audits/ohpa_geometry.json` before either full run. Author self-review, not independent.

## B. OH/PA re-check of the spatial validations

- Geometry: 155 OH/PA counties (cached 2020 cartographic boundaries; `unit_coordinates`), eight clusters
  assigned by `cluster_points` (seed 20261126) with k = 4 **within each state**, so no cluster mixes
  states; state indicator PA. Prepared by `--prepare` and committed here.
- C1 (Round 30): 12 cells, the frozen Round 30 generator (`scripts/im_acs_validation.py` `setup`/`outcome`,
  `census.im_acs`), observed-estimate targets beta* recomputed for this geometry by the Round 30 reference
  procedure (400,000 areas; linear targets checked against the closed form within .005). C2 is not re-run.
- G1/G2 (Round 35): 8 cells, the Round 35 generator and `census.spatial_eiv_core`; target the true slope 0.5.
- 2,000 draws per cell; seeds as the originals.
- **Acceptance (unchanged from Rounds 30 and 35):** 90% coverage ≥ .86 in every cell, per candidate (C1 per
  model). Failed fits count as non-coverage. Passing = "replicates on OH/PA"; failing keeps the MI/NY
  validation with an engine note naming the OH/PA failure.

## A. Round 29 post hoc

- Inputs: the released `r29_study_outputs.tar.gz`, verified by manifest hash and file checksums.
- For H1–H3 (registered formulas and offsets): P0 Poisson HC3 and P1 NB2-HC3, both population target,
  one-sided "greater" p-values, Holm across H1–H3 within each; holds = Holm p < .10. P2: H2 only,
  interval-censored Poisson with suppressed counties as counts in [1, 9] (exploratory).
- **Pre-set reading:** a hypothesis that held as registered and holds under P1 "holds"; one that held as
  registered but not under P1 is "sensitive to overdispersion" (registered result kept). P0 and P2 are
  descriptive.
- Outputs: coefficients only; `census.wonder_outputs.audit_outputs` must pass.
