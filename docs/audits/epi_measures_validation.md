# Round 84: marginal risk ratios and differences, prevalence ratios, attributable fractions, dose-response

Criterion commit: `c5f6266cbf74c7d7eb85c74443abacc2266bbece`. 2000 draws per cell; 90% intervals; trend tests at .10. P1b (design-blind robust SE) is reported only. Author self-review, not independent.

| Quantity | Outcome | Min | Max | Cells |
| :--- | :--- | ---: | ---: | ---: |
| G1a_rr | pass | 0.864 |  | 18 |
| G1a_rd | pass | 0.868 |  | 18 |
| F1a_paf | pass | 0.862 |  | 18 |
| D1a_size | pass | 0.083 | 0.111 | 6 |
| G1p_rr | pass | 0.868 |  | 12 |
| G1p_rd | pass | 0.875 |  | 12 |
| F1p_paf | pass | 0.866 |  | 12 |
| P1_pr | pass | 0.869 |  | 12 |
| P1b_robust | pass | 0.867 |  | 12 |
| D1p_size | pass | 0.099 | 0.1285 | 6 |

| Kind | Cell | Values |
| :--- | :--- | :--- |
| a | ['counties', 0.05, 1.0] | rr 0.893, rd 0.896, paf 0.898, trend_reject 0.090 (failed 0) |
| a | ['counties', 0.05, 1.3] | rr 0.864, rd 0.868, paf 0.862, trend_reject 0.000 (failed 0) |
| a | ['counties', 0.05, 1.8] | rr 0.893, rd 0.895, paf 0.890, trend_reject 0.000 (failed 0) |
| a | ['counties', 0.15, 1.0] | rr 0.888, rd 0.889, paf 0.889, trend_reject 0.083 (failed 0) |
| a | ['counties', 0.15, 1.3] | rr 0.896, rd 0.900, paf 0.897, trend_reject 0.000 (failed 0) |
| a | ['counties', 0.15, 1.8] | rr 0.886, rd 0.889, paf 0.884, trend_reject 0.000 (failed 0) |
| a | ['counties', 0.35, 1.0] | rr 0.879, rd 0.879, paf 0.879, trend_reject 0.111 (failed 0) |
| a | ['counties', 0.35, 1.3] | rr 0.880, rd 0.877, paf 0.880, trend_reject 0.000 (failed 0) |
| a | ['counties', 0.35, 1.8] | rr 0.875, rd 0.879, paf 0.875, trend_reject 0.000 (failed 0) |
| a | ['tracts', 0.05, 1.0] | rr 0.902, rd 0.903, paf 0.901, trend_reject 0.098 (failed 0) |
| a | ['tracts', 0.05, 1.3] | rr 0.914, rd 0.909, paf 0.911, trend_reject 0.000 (failed 0) |
| a | ['tracts', 0.05, 1.8] | rr 0.893, rd 0.903, paf 0.893, trend_reject 0.000 (failed 0) |
| a | ['tracts', 0.15, 1.0] | rr 0.908, rd 0.907, paf 0.907, trend_reject 0.103 (failed 0) |
| a | ['tracts', 0.15, 1.3] | rr 0.892, rd 0.896, paf 0.891, trend_reject 0.000 (failed 0) |
| a | ['tracts', 0.15, 1.8] | rr 0.900, rd 0.901, paf 0.901, trend_reject 0.000 (failed 0) |
| a | ['tracts', 0.35, 1.0] | rr 0.906, rd 0.906, paf 0.905, trend_reject 0.100 (failed 0) |
| a | ['tracts', 0.35, 1.3] | rr 0.901, rd 0.892, paf 0.903, trend_reject 0.000 (failed 0) |
| a | ['tracts', 0.35, 1.8] | rr 0.881, rd 0.894, paf 0.884, trend_reject 0.000 (failed 0) |
| p | [0.05, 1000, 'bin_effect'] | rr 0.868, rd 0.875, paf 0.867, pr 0.869, pr_robust 0.867, trend_reject 0.000 (failed 0) |
| p | [0.05, 1000, 'bin_null'] | rr 0.881, rd 0.890, paf 0.873, pr 0.880, pr_robust 0.878, trend_reject 0.000 (failed 0) |
| p | [0.05, 1000, 'ord3_null'] | rr 0.000, rd 0.000, paf 0.000, pr 0.000, pr_robust 0.000, trend_reject 0.117 (failed 0) |
| p | [0.05, 1000, 'ord3_lin'] | rr 0.000, rd 0.000, paf 0.000, pr 0.000, pr_robust 0.000, trend_reject 0.371 (failed 0) |
| p | [0.05, 5000, 'bin_effect'] | rr 0.883, rd 0.881, paf 0.887, pr 0.885, pr_robust 0.891, trend_reject 0.000 (failed 0) |
| p | [0.05, 5000, 'bin_null'] | rr 0.902, rd 0.902, paf 0.902, pr 0.903, pr_robust 0.905, trend_reject 0.000 (failed 0) |
| p | [0.05, 5000, 'ord3_null'] | rr 0.000, rd 0.000, paf 0.000, pr 0.000, pr_robust 0.000, trend_reject 0.099 (failed 0) |
| p | [0.05, 5000, 'ord3_lin'] | rr 0.000, rd 0.000, paf 0.000, pr 0.000, pr_robust 0.000, trend_reject 0.679 (failed 0) |
| p | [0.15, 1000, 'bin_effect'] | rr 0.879, rd 0.881, paf 0.873, pr 0.876, pr_robust 0.881, trend_reject 0.000 (failed 0) |
| p | [0.15, 1000, 'bin_null'] | rr 0.874, rd 0.875, paf 0.866, pr 0.875, pr_robust 0.872, trend_reject 0.000 (failed 0) |
| p | [0.15, 1000, 'ord3_null'] | rr 0.000, rd 0.000, paf 0.000, pr 0.000, pr_robust 0.000, trend_reject 0.129 (failed 0) |
| p | [0.15, 1000, 'ord3_lin'] | rr 0.000, rd 0.000, paf 0.000, pr 0.000, pr_robust 0.000, trend_reject 0.523 (failed 0) |
| p | [0.15, 5000, 'bin_effect'] | rr 0.891, rd 0.896, paf 0.893, pr 0.890, pr_robust 0.896, trend_reject 0.000 (failed 0) |
| p | [0.15, 5000, 'bin_null'] | rr 0.906, rd 0.907, paf 0.909, pr 0.906, pr_robust 0.910, trend_reject 0.000 (failed 0) |
| p | [0.15, 5000, 'ord3_null'] | rr 0.000, rd 0.000, paf 0.000, pr 0.000, pr_robust 0.000, trend_reject 0.111 (failed 0) |
| p | [0.15, 5000, 'ord3_lin'] | rr 0.000, rd 0.000, paf 0.000, pr 0.000, pr_robust 0.000, trend_reject 0.960 (failed 0) |
| p | [0.35, 1000, 'bin_effect'] | rr 0.897, rd 0.888, paf 0.894, pr 0.895, pr_robust 0.896, trend_reject 0.000 (failed 0) |
| p | [0.35, 1000, 'bin_null'] | rr 0.898, rd 0.894, paf 0.900, pr 0.896, pr_robust 0.896, trend_reject 0.000 (failed 0) |
| p | [0.35, 1000, 'ord3_null'] | rr 0.000, rd 0.000, paf 0.000, pr 0.000, pr_robust 0.000, trend_reject 0.121 (failed 0) |
| p | [0.35, 1000, 'ord3_lin'] | rr 0.000, rd 0.000, paf 0.000, pr 0.000, pr_robust 0.000, trend_reject 0.692 (failed 0) |
| p | [0.35, 5000, 'bin_effect'] | rr 0.896, rd 0.896, paf 0.899, pr 0.897, pr_robust 0.893, trend_reject 0.000 (failed 0) |
| p | [0.35, 5000, 'bin_null'] | rr 0.887, rd 0.886, paf 0.887, pr 0.888, pr_robust 0.898, trend_reject 0.000 (failed 0) |
| p | [0.35, 5000, 'ord3_null'] | rr 0.000, rd 0.000, paf 0.000, pr 0.000, pr_robust 0.000, trend_reject 0.104 (failed 0) |
| p | [0.35, 5000, 'ord3_lin'] | rr 0.000, rd 0.000, paf 0.000, pr 0.000, pr_robust 0.000, trend_reject 1.000 (failed 0) |
