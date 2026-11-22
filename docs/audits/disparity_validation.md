# Round 76: between-group disparity measures and Kitagawa decomposition

Criterion commit: `e9959787d90404851cd28db098da2137e8947d19`. 2000 draws per cell; 90% intervals; pass = coverage >= .86 in every cell (lowest contrast for rd/log_rr). Author self-review, not independent.

## ACS replicate design (G groups, smallest-group CV)

| Measure | (2, 0.1) | (2, 0.3) | (2, 0.5) | (4, 0.1) | (4, 0.3) | (4, 0.5) | (6, 0.1) | (6, 0.3) | (6, 0.5) | Outcome |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| rd | 0.903 | 0.914 | 0.924 | 0.879 | 0.910 | 0.914 | 0.893 | 0.894 | 0.900 | pass |
| log_rr | 0.903 | 0.909 | 0.663 | 0.888 | 0.904 | 0.654 | 0.889 | 0.900 | 0.664 | pass with range gate |
| idisp | 0.919 | 0.902 | 0.880 | 0.898 | 0.917 | 0.875 | 0.889 | 0.901 | 0.898 | pass |
| bgv | 0.920 | 0.904 | 0.884 | 0.887 | 0.894 | 0.839 | 0.891 | 0.889 | 0.832 | pass with range gate |
| theil | 0.923 | 0.897 | 0.877 | 0.893 | 0.884 | 0.817 | 0.883 | 0.885 | 0.819 | pass with range gate |
| mld | 0.922 | 0.896 | 0.649 | 0.891 | 0.889 | 0.498 | 0.887 | 0.889 | 0.552 | pass with range gate |

## Count design (G groups, expected count per group)

| Measure | (2, 20) | (2, 100) | (2, 1000) | (4, 20) | (4, 100) | (4, 1000) | (6, 20) | (6, 100) | (6, 1000) | Outcome |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| rd | 0.897 | 0.905 | 0.910 | 0.894 | 0.891 | 0.889 | 0.897 | 0.893 | 0.888 | pass |
| log_rr | 0.911 | 0.906 | 0.904 | 0.908 | 0.897 | 0.890 | 0.903 | 0.891 | 0.891 | pass |
| idisp | 0.091 | 0.737 | 0.916 | 0.831 | 0.898 | 0.899 | 0.836 | 0.868 | 0.877 | fail |
| bgv | 0.090 | 0.753 | 0.914 | 0.793 | 0.896 | 0.895 | 0.770 | 0.878 | 0.899 | fail |
| theil | 0.070 | 0.722 | 0.917 | 0.775 | 0.887 | 0.892 | 0.743 | 0.867 | 0.892 | fail |
| mld | 0.087 | 0.678 | 0.917 | 0.782 | 0.887 | 0.892 | 0.745 | 0.862 | 0.895 | fail |

## Kitagawa, ACS replicates (stratum-rate CV)

| Measure | ('acs', 0.1) | ('acs', 0.3) | ('acs', 0.5) | Outcome |
| :--- | ---: | ---: | ---: | :--- |
| difference | 0.895 | 0.906 | 0.920 | pass |
| rate_effect | 0.893 | 0.907 | 0.907 | pass |
| composition_effect | 0.909 | 0.907 | 0.927 | pass |

## Kitagawa, Poisson counts (expected count per stratum)

| Measure | ('counts', 20) | ('counts', 100) | ('counts', 1000) | Outcome |
| :--- | ---: | ---: | ---: | :--- |
| difference | 0.887 | 0.894 | 0.896 | pass |
| rate_effect | 0.887 | 0.895 | 0.889 | pass |
| composition_effect | 0.900 | 0.889 | 0.896 | pass |
