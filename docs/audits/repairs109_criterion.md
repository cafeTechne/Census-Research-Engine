# Round 109 Validation Criterion (Frozen Before Full Run)

**Scope:** Two validation candidates (`E3d`, `J3c`) defined in `census/repairs109_core.py` and executed by `scripts/repairs109_validation.py`.

**Standing rule:** A candidate passes **only** if **every** cell in its pre-specified grid meets the threshold. Any candidate that fails even one cell stays exploratory.

| ID | Measure / Gate | Design Grid | Replicates | Criterion |
| :--- | :--- | :--- | :--- | :--- |
| `E3d` | Fuller (1987, $\alpha = 4$) modified-denominator Croon/Fuller ecologic slope + delete-one-area jackknife `t(J - 2)`, gated at `median n_j ≥ 80, J ≥ 50` | `ICC ∈ {0.05, 0.15}` × `J ∈ {50, 150}` × `n_j ∈ {80, 150, 300}` (12 cells) | `R = 400` | Nominal 90% coverage **≥ .86** in all 12 cells |
| `J3c` | Joinpoint AAPC parametric residual bootstrap with joinpoint-location re-estimation + `t(n - 2k - 2)` SE interval | `T ∈ {15, 20}` × `k_true ∈ {0, 1}` × `events ∈ {200, 1000}` (8 cells; `B = 150` bootstrap draws) | `R = 300` | Nominal 90% coverage **≥ .86** in all 8 cells |
