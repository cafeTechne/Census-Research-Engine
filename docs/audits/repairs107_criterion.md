# Round 107 Validation Criterion (Frozen Before Full Run)

**Scope:** Four final-wave exploratory-measure repair candidates (`Q2d`, `E3b`, `H2d`, `S2`) defined in `census/repairs107_core.py` and executed by `scripts/repairs107_validation.py`.

**Standing rule:** Every candidate is judged on its pre-specified cell grid below. A candidate passes **only** if **every** cell in its grid meets the threshold. Any candidate that fails even one cell stays exploratory.

| ID | Measure / Gate | Design Grid | Replicates | Criterion |
| :--- | :--- | :--- | :--- | :--- |
| `Q2d-prob80` | FH parametric bootstrap PPV interval with rule re-selection for `rule="prob80"` | `N ∈ {200, 1000}` × `A ∈ {0.02, 0.08}` (4 cells; `B = 150` bootstrap draws) | `R = 400` | Nominal 90% coverage **≥ .86** in all 4 cells |
| `Q2d-point` | FH parametric bootstrap PPV interval with Li–Lahiri positive-`A` floor for `rule="point"` | `N ∈ {200, 1000}` × `A ∈ {0.02, 0.08}` (4 cells; `B = 150` bootstrap draws) | `R = 400` | Nominal 90% coverage **≥ .86** in all 4 cells |
| `E3b` | Croon/Fuller reliability-corrected ecologic/between-area slope + delete-one-area jackknife `t(J - 2)`, gated at `median n_j ≥ 40, J ≥ 50` | `J ∈ {50, 150}` × `n_j ∈ {40, 80, 150}` (`ICC = 0.10`, 6 cells) | `R = 400` | Nominal 90% coverage **≥ .86** in all 6 cells |
| `H2d` | PUMS Hotelling `F(K - 1, R - K + 1)` homogeneity test under exact per-measure nulls, gated at `min_stratum_n ≥ 500` | `measure ∈ {rr, or, rd}` × `K ∈ {3, 5}` × `n ∈ {500, 800}` (12 cells) | `R = 400` | Nominal `.10` size **≤ .13** in all 12 cells |
| `S2` | Shannon entropy diversity with exact SDR replicate bias correction `E_bc = E - 4 * (mean(Er) - E)` and `t(R - 1)` interval | `n_resp ∈ {50, 100, 200}` × `G ∈ {4, 6}` (6 cells; 80 SDR replicates) | `R = 500` | Nominal 90% coverage **≥ .86** in all 6 cells (and separately evaluated on the `n_resp ≥ 100` 4-cell gated grid) |
