# Round 83: stratified analysis, Mantel-Haenszel pooling and additive interaction

Criterion commit: `b35879913f46cdaa511929e88bae6c56dfebbd08`. 2000 draws per cell; 90% intervals; H1 at .10. Author self-review, not independent.

| Family | Outcome | Min (coverage or size) | Max | Cells |
| :--- | :--- | ---: | ---: | ---: |
| MH_rr | pass | 0.893 | None | 9 |
| MH_or | pass | 0.891 | None | 9 |
| MH_rd | pass | 0.877 | None | 9 |
| MH_irr | pass | 0.895 | None | 9 |
| H1_woolf | fail | 0.032 | 0.113 | 9 |
| H1_breslow_day | pass | 0.102 | 0.114 | 9 |
| RERI_delta | pass | 0.895 | None | 4 |
| RERI_boot | pass | 0.887 | None | 4 |
| MH2_rr | pass | 0.881 | None | 4 |
| MH2_or | pass | 0.888 | None | 4 |
| MH2_rd | pass | 0.883 | None | 4 |
| H1_pums_wald | fail | 0.099 | 0.151 | 12 |
| RERI_pums | pass | 0.891 | None | 4 |

## Cells

| Kind | Cell | Values |
| :--- | :--- | :--- |
| c | [2, 5, 'hom_rr'] | rr 0.906, bd_reject 0.122, woolf_reject 0.106 |
| c | [2, 5, 'hom_or'] | or 0.908, bd_reject 0.113, woolf_reject 0.113 |
| c | [2, 5, 'hom_rd'] | rd 0.884, bd_reject 0.144, woolf_reject 0.155 |
| c | [2, 5, 'hom_irr'] | irr 0.900 |
| c | [2, 5, 'het'] | bd_reject 0.629, woolf_reject 0.544 |
| c | [2, 20, 'hom_rr'] | rr 0.898, bd_reject 0.126, woolf_reject 0.103 |
| c | [2, 20, 'hom_or'] | or 0.899, bd_reject 0.102, woolf_reject 0.143 |
| c | [2, 20, 'hom_rd'] | rd 0.893, bd_reject 0.272, woolf_reject 0.381 |
| c | [2, 20, 'hom_irr'] | irr 0.901 |
| c | [2, 20, 'het'] | bd_reject 0.991, woolf_reject 0.962 |
| c | [2, 100, 'hom_rr'] | rr 0.910, bd_reject 0.232, woolf_reject 0.113 |
| c | [2, 100, 'hom_or'] | or 0.902, bd_reject 0.102, woolf_reject 0.271 |
| c | [2, 100, 'hom_rd'] | rd 0.907, bd_reject 0.736, woolf_reject 0.914 |
| c | [2, 100, 'hom_irr'] | irr 0.900 |
| c | [2, 100, 'het'] | bd_reject 1.000, woolf_reject 1.000 |
| c | [4, 5, 'hom_rr'] | rr 0.902, bd_reject 0.116, woolf_reject 0.054 |
| c | [4, 5, 'hom_or'] | or 0.909, bd_reject 0.111, woolf_reject 0.061 |
| c | [4, 5, 'hom_rd'] | rd 0.877, bd_reject 0.139, woolf_reject 0.103 |
| c | [4, 5, 'hom_irr'] | irr 0.908 |
| c | [4, 5, 'het'] | bd_reject 0.559, woolf_reject 0.392 |
| c | [4, 20, 'hom_rr'] | rr 0.896, bd_reject 0.114, woolf_reject 0.085 |
| c | [4, 20, 'hom_or'] | or 0.891, bd_reject 0.112, woolf_reject 0.121 |
| c | [4, 20, 'hom_rd'] | rd 0.896, bd_reject 0.246, woolf_reject 0.296 |
| c | [4, 20, 'hom_irr'] | irr 0.895 |
| c | [4, 20, 'het'] | bd_reject 0.976, woolf_reject 0.912 |
| c | [4, 100, 'hom_rr'] | rr 0.893, bd_reject 0.199, woolf_reject 0.108 |
| c | [4, 100, 'hom_or'] | or 0.892, bd_reject 0.107, woolf_reject 0.214 |
| c | [4, 100, 'hom_rd'] | rd 0.896, bd_reject 0.709, woolf_reject 0.864 |
| c | [4, 100, 'hom_irr'] | irr 0.901 |
| c | [4, 100, 'het'] | bd_reject 1.000, woolf_reject 1.000 |
| c | [8, 5, 'hom_rr'] | rr 0.895, bd_reject 0.116, woolf_reject 0.032 |
| c | [8, 5, 'hom_or'] | or 0.898, bd_reject 0.110, woolf_reject 0.037 |
| c | [8, 5, 'hom_rd'] | rd 0.897, bd_reject 0.128, woolf_reject 0.054 |
| c | [8, 5, 'hom_irr'] | irr 0.895 |
| c | [8, 5, 'het'] | bd_reject 0.577, woolf_reject 0.343 |
| c | [8, 20, 'hom_rr'] | rr 0.897, bd_reject 0.108, woolf_reject 0.074 |
| c | [8, 20, 'hom_or'] | or 0.898, bd_reject 0.110, woolf_reject 0.115 |
| c | [8, 20, 'hom_rd'] | rd 0.900, bd_reject 0.221, woolf_reject 0.267 |
| c | [8, 20, 'hom_irr'] | irr 0.902 |
| c | [8, 20, 'het'] | bd_reject 0.992, woolf_reject 0.944 |
| c | [8, 100, 'hom_rr'] | rr 0.899, bd_reject 0.194, woolf_reject 0.105 |
| c | [8, 100, 'hom_or'] | or 0.894, bd_reject 0.114, woolf_reject 0.209 |
| c | [8, 100, 'hom_rd'] | rd 0.897, bd_reject 0.689, woolf_reject 0.850 |
| c | [8, 100, 'hom_irr'] | irr 0.899 |
| c | [8, 100, 'het'] | bd_reject 1.000, woolf_reject 1.000 |
| p | [2, 300, 'hom_rr'] | rr 0.895, wald_reject 0.128 |
| p | [2, 300, 'hom_or'] | or 0.891, wald_reject 0.124 |
| p | [2, 300, 'hom_rd'] | rd 0.899, wald_reject 0.108 |
| p | [2, 3000, 'hom_rr'] | rr 0.893, wald_reject 0.103 |
| p | [2, 3000, 'hom_or'] | or 0.898, wald_reject 0.099 |
| p | [2, 3000, 'hom_rd'] | rd 0.896, wald_reject 0.105 |
| p | [4, 300, 'hom_rr'] | rr 0.891, wald_reject 0.151 |
| p | [4, 300, 'hom_or'] | or 0.890, wald_reject 0.142 |
| p | [4, 300, 'hom_rd'] | rd 0.883, wald_reject 0.141 |
| p | [4, 3000, 'hom_rr'] | rr 0.881, wald_reject 0.120 |
| p | [4, 3000, 'hom_or'] | or 0.888, wald_reject 0.130 |
| p | [4, 3000, 'hom_rd'] | rd 0.909, wald_reject 0.136 |
| pr | [0.0, 3000] | reri 0.908 |
| pr | [0.0, 10000] | reri 0.897 |
| pr | [0.5, 3000] | reri 0.891 |
| pr | [0.5, 10000] | reri 0.903 |
| r | [0.0, 0.05] | delta 0.895, boot 0.889 |
| r | [0.0, 0.2] | delta 0.896, boot 0.894 |
| r | [0.5, 0.05] | delta 0.896, boot 0.887 |
| r | [0.5, 0.2] | delta 0.898, boot 0.898 |
