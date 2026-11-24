# Round 113 Validation Criterion (Frozen Before Full Run)

**Scope:** Domain-gated three-level variance-share delete-one-top-unit logit jackknife (`M3c`, `multilevel3_core.jackknife_shares`) on the national state-level domain (`G_top ≥ 49`).

**Standing rule:** `M3c` passes **only** if **every** share-cell in the pre-specified grid meets nominal 90% coverage **≥ .86**.

| ID | Measure / Gate | Design Grid | Replicates | Criterion |
| :--- | :--- | :--- | :--- | :--- |
| `M3c` | Three-level variance-share delete-one-top-unit logit jackknife, gated at `G_top ≥ 49` | `G_top ∈ {49, 51}` × 2 splits (`(0.70, 0.15, 0.15)`, `(0.50, 0.25, 0.25)`) × 3 shares (`bottom`, `mid`, `top`) (12 share-cells; `n_mid = 5, n_bot = 6`) | `R = 200` | Nominal 90% coverage **≥ .86** in all 12 cells |
