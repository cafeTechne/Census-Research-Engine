# Round 110 Validation Criterion (Frozen Before Full Run)

**Scope:** Two validation candidates (`S3`, `W2`) defined in `census/repairs110_core.py` and executed by `scripts/repairs110_validation.py`.

**Standing rule:** A candidate passes **only** if **every** cell in its pre-specified grid meets the threshold. Any candidate that fails even one cell stays exploratory.

| ID | Measure / Gate | Design Grid | Replicates | Criterion |
| :--- | :--- | :--- | :--- | :--- |
| `S3` | Synthetic-control conformal inference interval (Chernozhukov–Wüthrich–Zhu 2021), gated at `T_pre ≥ 15, N_donors ≥ 25` | `T_pre ∈ {15, 20}` × `ρ ∈ {0.0, 0.3, 0.7}` × `effect ∈ {0.0, -2.0}` (12 cells; `N = 51` units, 50 donors) | `R = 250` | Nominal 90% coverage **≥ .86** in all 12 cells |
| `W2-mdm` | WHO weighted mean difference from overall mean (`mdm_w`) replicate interval, gated at `SNR ≥ 4.0, max_cv ≤ 0.15` | `G ∈ {4, 6}` × `CV ∈ {0.05, 0.15}` × `SNR ∈ {4.0, 8.0}` (8 cells; 80 SDR replicates) | `R = 400` | Nominal 90% coverage **≥ .86** in all 8 cells |
| `W2-mdb` | WHO weighted mean difference from best group (`mdb_w`) replicate interval, gated at `SNR ≥ 4.0, max_cv ≤ 0.15` | `G ∈ {4, 6}` × `CV ∈ {0.05, 0.15}` × `SNR ∈ {4.0, 8.0}` (8 cells; 80 SDR replicates) | `R = 400` | Nominal 90% coverage **≥ .86** in all 8 cells |
