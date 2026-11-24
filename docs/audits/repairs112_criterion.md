# Round 112 Validation Criterion (Frozen Before Full Run)

**Scope:** Five final repairable exploratory candidates (`M3b`, `Q2e-lower`/`Q2e-prob50`, `D2`, `R2_dens`, `W3_rr`) defined in `census/repairs112_core.py` and executed by `scripts/repairs112_validation.py`.

**Standing rule:** Every candidate is judged independently on its pre-specified cell grid. A candidate passes **only** if **every** cell in its grid meets the threshold.

| ID | Measure / Gate | Design Grid | Replicates | Criterion |
| :--- | :--- | :--- | :--- | :--- |
| `M3b` | Three-level variance-share delete-one-top-unit logit jackknife (`multilevel3_core.jackknife_shares`) | `G_top ∈ {30, 49}` × 2 splits (`(0.70, 0.15, 0.15)`, `(0.50, 0.25, 0.25)`) × 3 shares (`bottom`, `mid`, `top`) (12 share-cells) | `R = 200` | Nominal 90% coverage **≥ .86** in all 12 cells |
| `Q2e-lower` | FH parametric bootstrap PPV interval with Li–Lahiri floor for `rule="lower"` | `N ∈ {200, 1000}` × `A ∈ {0.02, 0.08}` (4 cells; `B = 120`) | `R = 300` | Nominal 90% coverage **≥ .86** in all 4 cells |
| `Q2e-prob50` | FH parametric bootstrap PPV interval with Li–Lahiri floor for `rule="prob50"` | `N ∈ {200, 1000}` × `A ∈ {0.02, 0.08}` (4 cells; `B = 120`) | `R = 300` | Nominal 90% coverage **≥ .86** in all 4 cells |
| `D2-{idisp,bgv,theil,mld}` | Count-scale disparity index parametric Poisson bootstrap on log-scale, gated at `min_events ≥ 100` | `G ∈ {3, 5}` × `min_events ∈ {100, 500}` × `spread ∈ {moderate, wide}` (8 cells per index; `B = 200`) | `R = 300` | Nominal 90% coverage **≥ .86** in all 8 cells (judged per index) |
| `R2_dens` | RDD density/manipulation test (`rdd_core.density_test`) under smooth null densities | `dist ∈ {uniform, normal, beta22}` × `n ∈ {1000, 5000}` (6 cells) | `R = 400` | Nominal `.10` size **∈ [.07, .13]** in all 6 cells |
| `W3_rr` | Stratified count RR homogeneity (Woolf/inverse-variance log-RR test gated at `min_cases ≥ 15`) | `K ∈ {3, 5}` × `min_cases ∈ {15, 40}` (4 cells) | `R = 400` | Nominal `.10` size **∈ [.07, .13]** in all 4 cells |
