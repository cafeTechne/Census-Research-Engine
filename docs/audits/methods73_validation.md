# Round 73: three-level models and fixed-loading indices

Criterion commit: `e97e9fc`.

| G_top | Shares (bottom, mid, top) | M1 slope coverage | M3 share coverage (screening, 100 draws) |
| ---: | :--- | ---: | :--- |
| 30 | (0.7, 0.11, 0.19) | 0.9040 | bottom 0.96, mid 0.96, top 0.98 |
| 30 | (0.5, 0.25, 0.25) | 0.9110 | bottom 0.89, mid 0.88, top 0.90 |
| 49 | (0.7, 0.11, 0.19) | 0.9130 | bottom 0.94, mid 0.96, top 0.93 |
| 49 | (0.5, 0.25, 0.25) | 0.9120 | bottom 0.90, mid 0.89, top 0.90 |

| Reliability | Range km | Mean per-area coverage | Lowest area |
| ---: | ---: | ---: | ---: |
| 0.9 | 0 | 0.8978 | 0.8785 |
| 0.9 | 100 | 0.8980 | 0.8785 |
| 0.7 | 0 | 0.8971 | 0.8845 |
| 0.7 | 100 | 0.8986 | 0.8805 |

Outcomes: `{"M1": true, "M3_screen": true, "LI": true}` (M3 is a screening result; it stays exploratory).
