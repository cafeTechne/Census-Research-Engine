# Round 108 Validation Criterion (Frozen Before Full Run)

**Scope:** Three validation candidates (`M5b`, `E3c`, `S2b`) defined in `census/repairs108_core.py` and executed by `scripts/repairs108_validation.py`.

**Standing rule:** A candidate passes **only** if **every** cell in its pre-specified grid meets the threshold. Any candidate that fails even one cell stays exploratory.

| ID | Measure / Gate | Design Grid | Replicates | Criterion |
| :--- | :--- | :--- | :--- | :--- |
| `M5b` | Vector multi-confounder parametric g-formula (VAR(1) transition + outcome model + delete-one-unit cluster jackknife `t(G - 1)`) | `p ∈ {2, 3}` × `K ∈ {12, 18}` × `feedback ∈ {0.0, 0.5}` × `psi ∈ {0.0, -2.0}` × `duration ∈ {1, 2, 3}` (48 cells; `G = 51` units) | `R = 400` | Nominal 90% coverage **≥ .86** in all 48 cells |
| `E3c` | Croon/Fuller reliability-corrected ecologic/between-area slope + delete-one-area jackknife `t(J - 2)`, gated at `median n_j ≥ 80, J ≥ 50` | `J ∈ {50, 150}` × `n_j ∈ {80, 150, 300}` × `ICC ∈ {0.05, 0.15}` (12 cells) | `R = 400` | Nominal 90% coverage **≥ .86** in all 12 cells |
| `S2b` | Shannon entropy diversity with exact SDR replicate bias correction `E_bc = E - 4 * (mean(Er) - E)` and `t(R - 1)`, gated at `n_resp ≥ 150` | `G ∈ {4, 6}` × `n_resp ∈ {150, 200, 400}` (6 cells; 80 SDR replicates) | `R = 500` | Nominal 90% coverage **≥ .86** in all 6 cells |
