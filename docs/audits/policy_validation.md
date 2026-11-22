# Round 78: staggered-adoption DiD and synthetic control

Criterion commit: `baf934be8e5363467bbf0a989fc2dc724971dc17`. 1000 draws per cell; 90% intervals. Author self-review, not independent.

## Staggered adoption (lowest coverage over the overall ATT and every event time)

| T | rho | Effect | S1 CS | S1r CS + ACS | S2 SA | S1 uniform band |
| ---: | ---: | :--- | ---: | ---: | ---: | ---: |
| 12 | 0.3 | constant | 0.864 | 0.896 | 0.899 | 0.787 |
| 12 | 0.3 | growing | 0.855 | 0.886 | 0.890 | 0.793 |
| 12 | 0.7 | constant | 0.848 | 0.896 | 0.891 | 0.797 |
| 12 | 0.7 | growing | 0.859 | 0.890 | 0.892 | 0.798 |
| 18 | 0.3 | constant | 0.858 | 0.882 | 0.881 | 0.764 |
| 18 | 0.3 | growing | 0.868 | 0.893 | 0.888 | 0.778 |
| 18 | 0.7 | constant | 0.866 | 0.906 | 0.889 | 0.812 |
| 18 | 0.7 | growing | 0.853 | 0.884 | 0.884 | 0.758 |

## Synthetic control (one treated unit, 50 donors, 3 post periods)

| T | rho | Effect | Placebo rejection at .10 | C2 coverage by post period | Pre-fit flagged |
| ---: | ---: | :--- | ---: | :--- | ---: |
| 12 | 0.3 | none | 0.194 | 0: 0.765, 1: 0.765, 2: 0.760 | 0.006 |
| 12 | 0.3 | constant | 0.211 | 0: 0.835, 1: 0.849, 2: 0.821 | 0.128 |
| 12 | 0.3 | growing | 0.146 | 0: 0.863, 1: 0.848, 2: 0.851 | 0.136 |
| 12 | 0.7 | none | 0.132 | 0: 0.785, 1: 0.761, 2: 0.737 | 0.027 |
| 12 | 0.7 | constant | 0.386 | 0: 0.782, 1: 0.734, 2: 0.735 | 0.030 |
| 12 | 0.7 | growing | 0.226 | 0: 0.815, 1: 0.780, 2: 0.797 | 0.064 |
| 18 | 0.3 | none | 0.121 | 0: 0.933, 1: 0.923, 2: 0.945 | 0.001 |
| 18 | 0.3 | constant | 0.639 | 0: 0.923, 1: 0.911, 2: 0.924 | 0.001 |
| 18 | 0.3 | growing | 0.328 | 0: 0.939, 1: 0.939, 2: 0.923 | 0.008 |
| 18 | 0.7 | none | 0.161 | 0: 0.919, 1: 0.900, 2: 0.883 | 0.001 |
| 18 | 0.7 | constant | 0.360 | 0: 0.923, 1: 0.929, 2: 0.934 | 0.059 |
| 18 | 0.7 | growing | 0.529 | 0: 0.904, 1: 0.902, 2: 0.870 | 0.003 |

Outcomes: `{"S1": false, "S1r": true, "S2": true, "C1": false, "C2": false}`.
