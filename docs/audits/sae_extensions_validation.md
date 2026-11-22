# Round 80: arcsine Fay-Herriot for proportions and Rao-Yu temporal Fay-Herriot

Criterion commit: `251dc9d47235024a3c8cdc1fafed6bdfce790ec0`. 500 draws per cell; 90% intervals. Author self-review, not independent.

## P1: arcsine FH (per-area coverage: mean / 10th percentile)

| Geometry | sigma_u | Areas | P1 MSE-normal | P1q quantile | P1b naive | Rel. bias p<.10 (P1 / naive) |
| :--- | ---: | ---: | :--- | :--- | :--- | :--- |
| MI county | 0.05 | 83 | 0.900 / 0.880 | 0.892 / 0.872 | 0.899 / 0.880 | 0.008 / 0.006 |
| MI county | 0.1 | 83 | 0.903 / 0.882 | 0.895 / 0.878 | 0.898 / 0.884 | 0.010 / 0.007 |
| NY county | 0.05 | 62 | 0.899 / 0.882 | 0.892 / 0.876 | 0.899 / 0.882 | 0.006 / 0.005 |
| NY county | 0.1 | 62 | 0.904 / 0.888 | 0.894 / 0.874 | 0.899 / 0.886 | 0.004 / 0.002 |
| MI tract | 0.05 | 2868 | 0.901 / 0.884 | 0.894 / 0.876 | 0.899 / 0.880 | 0.043 / 0.026 |
| MI tract | 0.1 | 2868 | 0.898 / 0.880 | 0.892 / 0.872 | 0.895 / 0.878 | 0.071 / 0.039 |
| NY tract | 0.05 | 5176 | 0.901 / 0.884 | 0.895 / 0.876 | 0.899 / 0.880 | 0.044 / 0.026 |
| NY tract | 0.1 | 5176 | 0.898 / 0.880 | 0.892 / 0.874 | 0.896 / 0.878 | 0.078 / 0.044 |

## T1: Rao-Yu temporal FH (last release)

| Geometry | Releases | rho | T1 mean coverage | 10th pct | FH (g1+g2) coverage | MSE gain vs FH |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| counties | 2 | 0.3 | 0.898 | 0.882 | 0.900 | 0.030 |
| counties | 2 | 0.8 | 0.898 | 0.882 | 0.900 | 0.070 |
| counties | 3 | 0.3 | 0.897 | 0.881 | 0.900 | 0.035 |
| counties | 3 | 0.8 | 0.898 | 0.884 | 0.901 | 0.070 |
| tracts300 | 2 | 0.3 | 0.897 | 0.880 | 0.899 | 0.099 |
| tracts300 | 2 | 0.8 | 0.897 | 0.880 | 0.899 | 0.208 |
| tracts300 | 3 | 0.3 | 0.897 | 0.880 | 0.900 | 0.125 |
| tracts300 | 3 | 0.8 | 0.897 | 0.882 | 0.900 | 0.235 |

Outcomes: `{"P1": true, "P1q": true, "T1": true}`.
