# Round 48 plan: small samples and spatial dependence

**Goal.** `ROADMAP_BACKLOG.md` issues N10, N12 and N13. Four procedures failed in earlier rounds:

- Interrupted time-series intervals with 20 annual points (Round 42: .47–.81).
- Correlation intervals and Cronbach/Feldt α under spatial dependence (Round 33: .60–.89; Round 36:
  .58–.67).
- Hartung–Knapp pooling, validated only for k ≤ 4 (Round 38).
- Bland–Altman limits of agreement (Round 37: observed .838, error-free .826).

Each problem gets a fixed simulation that reuses the earlier round's generator, so that only the new
procedure differs. Only procedures that pass enter the engine.

Version 0.45.0. Baseline: the Round 47 suite. Branch `phase48/small-samples-spatial`. Validation first.

## 1. Validation (`scripts/small_spatial_validation.py` → `docs/audits/small_spatial_validation.md`/`.json`)

**Frozen files:**
- New `census/small_spatial_core.py`.
- The script and the criterion doc.
- The earlier generators it imports: `scripts/rank_validation.py`, `scripts/index_validation.py`,
  `scripts/agreement_validation.py`, `scripts/evidence_validation.py` and their targets files.

The new procedures receive exactly the data the old procedures received. 2,000 draws per cell; seed
`20270601 + cell`.

**I: interrupted series (6 cells).**
- Design: as in Round 42 (annual points, interruption at the middle, AR(1) errors, innovation SD 1;
  level change 1, slope change .2), with n ∈ {15, 20, 30} × φ ∈ {.3, .6}.
- **I1:** REML AR(1). Profile the restricted likelihood over φ ∈ (−.95, .95) by bounded scalar
  minimisation, then fit GLS (Prais–Winsten, keeping the first point) at φ̂, with a t(n − 4) reference.
- **I2:** AR(1) residual bootstrap-t. Draw 499 resamples from the I1 fit (centred innovations, φ̂,
  first point from the stationary distribution), re-estimate I1 on each, and use the bootstrap
  quantiles of the t statistics.
- Comparison: the Round 42 GLSAR.
- Targets: both changes.

**C: correlations under spatial dependence (8 cells).**
- Design: the Round 33 cells (ρ ∈ {0, .4} × reliability {.9, .7} × range {0, 100} km; MI/NY geometry;
  lognormal fields with ACS error and replicates). Target: the Round 33 observed-value reference.
- **C1:** Dutilleul's modified effective sample size.
  - The spatial autocorrelation of each variable is estimated by Moran's I in 13 equal-width distance
    classes.
  - σ̂²_r = tr(R̂ₓR̂ᵧ)/n², and n_eff = 1 + 1/σ̂²_r, capped at n.
  - The Round 33 Fisher-type interval is then recomputed with n_eff in place of n, keeping the Round 33
    variance factor and, for Pearson and partial, the replicate variance term.
  - It is applied to Spearman, Kendall and Pearson (plus replicates).
- **C2:** IM-8. Compute the correlation within each of the eight fixed clusters, transform with Fisher
  z, and form a t(7) interval for the mean (comparison: the within-cluster correlation is attenuated
  when the field varies mostly between clusters).

**A: Feldt α under spatial dependence (8 cells).**
- Design: the Round 36 cells (reliability {.9, .7} × range {0, 100} × PCA/equal). Target: the Round 36
  α reference.
- **A3:** Feldt's interval with n replaced by the n_eff of the total score's autocorrelation with
  itself, by the C1 estimator.
- **A4:** IM-8 on log(1 − α̂_g).

**H: random-effects pooling for k = 5–10 (6 cells).**
- Design: the Round 38 heterogeneous generator, with k ∈ {5, 7, 10} × τ²/mean(sᵢ²) ∈ {.5, 2}.
- **H1:** Paule–Mandel with Hartung–Knapp (the existing `evidence_core.pooled(..., "hksj")`).
- **H2:** H1 with the Knapp–Hartung truncation, var = max(1, q)·(the H1 variance).
- Target: μ.

**B: Bland–Altman limits (4 independent cells).**
- Design: the Round 37 independent cells (A reliability {.9, .7} × B error {no, yes}). Targets: the
  Round 37 references.
- **B1r:** observed limits whose SE comes from the sample kurtosis: Var(s²) ≈ (m₄ − s⁴)/n, then the
  delta method for s.
- **B2r:** the error-free limits, with the same kurtosis-based variance of s² − mean(error variance).

**Acceptance.** 90% coverage must be ≥ .86, and failed fits count as non-coverage.

| Problem | Passes if coverage ≥ .86 in |
| :--- | :--- |
| I | every cell, for both changes |
| C | every cell, per method (Spearman, Kendall, Pearson) |
| A | every cell |
| H | every cell |
| B | every cell, both limits |

Each procedure is judged separately. For I, a procedure that fails at n = 15 but passes at n ≥ 20 is
reported with that minimum (the "n₀" rule: the smallest n at which it passes there and above, in both
φ).

## 2. Engine (only what passes)

- **I:** `interrupted_series(method=...)` gains the passing method(s), validated for n ≥ n₀.
- **C:** `correlation_interval(..., spatial="dutilleul", coords=...)` (library and MCP
  `correlation_matrix`). Manifests are not routed (deferred).
- **A:** `build_index` α interval with `spatial=` when it passes.
- **H:** `HKSJ_VALIDATED_MAX_K` raised to 10, using the passing variant.
- **B:** `check_agreement` limit intervals become validated with the kurtosis SE.
- **Shared steps:**
  - Mirror the rule text in `agent_protocol.md`, the recipes, `mcp_profiles` and the docstrings.
  - Update STATUS and the CHANGELOG.
  - Add tests that check the engine flags equal the audit.
  - Keep goldens unchanged.
  - Run the full suite.
- **Exploratory MI/NY example:** spatially corrected correlations among the Round 29 SMRs and poverty,
  plus pooled H1 slopes across MI/NY and OH/PA.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Criterion commit | `3fb07d3`, pushed before the full run | core, script, criterion and reused generators frozen |
| I / C / A / H / B results | ITS bootstrap-t passes at n = 30 only; REML fails; effective-n correlations (.862–.967) and α (.912–.926) pass; IM-8 fails except Kendall; HKSJ k 5–10 passes (truncated used); moment-based limits pass (.884–.936) | |
| Engine, tests | `small_spatial` flags, `coords=`/`spatial=True`, `bootstrap_t`, truncated HKSJ, validated limits; 8 tests; 2 old flag tests updated | |
| Example | Round 29 correlations with poverty, independent vs effective-n (n_eff 59–127) | `docs/studies/r48_spatial_example.md` |
| Goldens, final suite | both byte-identical; 2035 passed, 37 skipped | |
| Exceptions | estimator is Clifford–Richardson–Hémon (named Dutilleul in the plan) | recorded in the criterion |
