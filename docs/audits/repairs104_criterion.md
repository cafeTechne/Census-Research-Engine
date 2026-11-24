# Round 104 validation criterion: exploratory-measure repairs

Pre-specified pass criteria for `scripts/repairs104_validation.py` operating on `census/repairs104_core.py`.
Every candidate is evaluated on the exact DGP cells where its predecessor failed in Rounds 91, 94, 96, 99 and 102.
Nominal interval level is 90%; pass threshold is **coverage ≥ 0.86** in every cell of the claimed scope (and
**nominal-.10 rejection size ≤ 0.13** for `E2`). Candidates that fail remain exploratory; no post-hoc retuning.

1. **Meta-analysis (`meta_validation.md` cells, 2,000 draws per cell):**
   - `P2` (Nagashima–Noma–Furukawa prediction interval): coverage of a new study's true effect ≥ 0.86 for every
     `k ∈ {10, 20, 40}` and `I² ∈ {0.0, 0.25, 0.5, 0.75}`. Fallback gate: `k ≥ 20` if `k = 10` fails.
   - `R2` (truncated Knapp–Hartung meta-regression): coverage ≥ 0.86 for `k ∈ {10, 20, 40}`, `I² ∈ {0.0, 0.5}`,
     `β ∈ {0.0, 0.2}`. Fallback gate: `k ≥ 20` if `k = 10` fails.
   - `E2` (random-effects Egger / Thompson–Sharp): null size ≤ 0.13 (target ≤ 0.10) for `k ∈ {10, 20, 40}`,
     `I² ∈ {0.0, 0.25, 0.5, 0.75}`. Fallback gate: `k ≥ 20` if `k = 10` fails.
2. **Nearest-neighbour matching ATT (`matching_validation.md` cells, 1,500 draws per cell):**
   - `M1b-ATT` (`M = 4`, Kish `t(df_eff)`): coverage ≥ 0.86 in all 8 cells (`N ∈ {145, 600}`, propensity
     `{0.5, 1.502}`, homogeneous/heterogeneous).
3. **BYM2 disease mapping (`disease_mapping_validation.md` county cells, 300 draws per cell):**
   - `B3` (PC prior + log-grid Jacobian): mean area coverage ≥ 0.86 and ≥ 80% of areas ≥ 0.80 in all 8 county
     cells (`φ ∈ {0.2, 0.8}`, `σ ∈ {0.2, 0.5}`, `median E ∈ {5, 30}`). Fallback gate: `median E ≥ 15` (tested at
     `median E = 30`).
4. **IP-weighted MSM (`msm_validation.md` cells, 500 draws per cell):**
   - `M3` (baseline-L0 stabilized + delete-one-unit cluster jackknife `t(G - 1)`): coverage ≥ 0.86 across all 3
     durations in all 6 `K = 12` and 6 `K = 18` cells (`Feedback ∈ {0.0, 0.5, 1.0}`, `ψ ∈ {0.0, -2.0}`).
5. **WHO mean differences (`inequality_monitoring_validation.md` cells, 1,500 draws per cell):**
   - `MD2` (replicate bias-corrected `mdm_w`, `mdb_w`): coverage ≥ 0.86 across `G ∈ {4, 6, 8}`, `c ∈ {0.1, 0.3, 0.5}`,
     `Spread ∈ {small, large}` (declared reference and `"best"`).
   - Fallback gate: uncorrected `mdm_w` / `mdb_w` gated at `max_group_cv ≤ 0.10` (all `c = 0.1` cells ≥ 0.86).
