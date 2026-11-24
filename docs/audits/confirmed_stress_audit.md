# Round 111 Adversarial Out-of-DGP Stress-Test Audit of Confirmed Methods

Runtime: 5.7s (`scripts/confirmed_stress_audit.py`, seed `20291111`).

Checks whether confirmed methods hold nominal 90% coverage (≥ .86) or nominal .10 size (≤ .13) under deliberate departures from their validation DGPs.

| Method | Stress Departure | Metric | Observed | Holds? |
| :--- | :--- | :--- | ---: | :--- |
| `P2_meta_PI` | `t3_random_effects_k12` | coverage | 0.880 | **YES** |
| `R2_meta_reg` | `t3_random_effects_k12` | coverage | 0.900 | **YES** |
| `E2_egger_re` | `t3_random_effects_k12` | size | 0.100 | **YES** |
| `M5_gformula` | `t3_errors` | min_coverage_d1_3 | 0.892 | **YES** |
| `M5_gformula` | `mild_quadratic_L` | min_coverage_d1_3 | 0.884 | **YES** |
| `R1b_rdd_continuous` | `t3_and_3x_heteroscedastic_jump` | coverage | 0.900 | **YES** |
| `C2_lin_ccc` | `skewed_lognormal_n80` | coverage | 0.867 | **YES** |
| `E3d_ecologic_fuller` | `unbalanced_nj_50_200_and_t3` | coverage | 0.873 | **YES** |
| `J3c_joinpoint_aapc` | `negbin_overdispersed_2.5x` | coverage | 0.916 | **YES** |
| `H2d_pums_hotelling_f` | `extreme_weight_cv_1.2` | size | 0.097 | **YES** |
