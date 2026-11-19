# Rank and partial correlation, superiority and Kruskal-Wallis: validation (Round 33)

intervals: 90% coverage of the observed-estimate target >= .86 in every independent cell; Kruskal-Wallis: nominal-.10 size in [.07,.13] in independent null cells; failures count as non-coverage.

Criterion commit: `f660e9c`. 2,000 draws per cell.

## Coverage of the observed-estimate target (90%)

| corr | reliability | range km | kendall/1 | kendall/2 | partial/1 | partial/2 | pearson/1 | pearson/2 | spearman/1 | spearman/2 | B1 | B2 |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.0 | 0.9 | 0 | 0.9050 | 0.9450 | 0.8950 | 0.9400 | 0.9015 | 0.9345 | 0.9155 | 0.9510 | 0.8970 | 0.9300 |
| 0.0 | 0.9 | 100 | 0.6210 | 0.6995 | 0.6660 | 0.7280 | 0.6395 | 0.6980 | 0.6405 | 0.7070 | 0.9180 | 0.9535 |
| 0.0 | 0.7 | 0 | 0.9000 | 0.9755 | 0.9050 | 0.9680 | 0.9040 | 0.9650 | 0.9150 | 0.9795 | 0.9030 | 0.9545 |
| 0.0 | 0.7 | 100 | 0.7090 | 0.8600 | 0.7440 | 0.8810 | 0.7230 | 0.8595 | 0.7250 | 0.8675 | 0.9055 | 0.9730 |
| 0.4 | 0.9 | 0 | 0.8925 | 0.9490 | 0.8580 | 0.9025 | 0.8420 | 0.8920 | 0.8990 | 0.9470 | 0.8985 | 0.9335 |
| 0.4 | 0.9 | 100 | 0.6270 | 0.7245 | 0.6260 | 0.6985 | 0.5965 | 0.6620 | 0.6375 | 0.7290 | 0.8535 | 0.9015 |
| 0.4 | 0.7 | 0 | 0.8960 | 0.9765 | 0.8675 | 0.9555 | 0.8695 | 0.9570 | 0.9025 | 0.9770 | 0.9045 | 0.9580 |
| 0.4 | 0.7 | 100 | 0.7125 | 0.8870 | 0.7235 | 0.8580 | 0.6910 | 0.8380 | 0.7305 | 0.8895 | 0.8665 | 0.9445 |

## Superiority test size/power and Kruskal-Wallis size (nominal .10)

| corr | reliability | range km | B1 size | B2 size | B1 power | B2 power | KW size |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| 0.0 | 0.9 | 0 | 0.1030 | 0.0700 | 0.399 | 0.334 | 0.1060 |
| 0.0 | 0.9 | 100 | 0.0820 | 0.0465 | 0.378 | 0.301 | 0.0760 |
| 0.0 | 0.7 | 0 | 0.0970 | 0.0455 | 0.302 | 0.189 | 0.0950 |
| 0.0 | 0.7 | 100 | 0.0945 | 0.0270 | 0.296 | 0.157 | 0.1250 |
| 0.4 | 0.9 | 0 | 0.1015 | 0.0665 | 0.388 | 0.322 | n/a |
| 0.4 | 0.9 | 100 | 0.1465 | 0.0985 | 0.443 | 0.369 | n/a |
| 0.4 | 0.7 | 0 | 0.0955 | 0.0420 | 0.299 | 0.179 | n/a |
| 0.4 | 0.7 | 100 | 0.1335 | 0.0555 | 0.320 | 0.199 | n/a |

Coverage of the error-free coefficient is in the JSON (attenuation expected).

Outcomes: `{"B1": true, "B2": true, "KW": true, "kendall/1": true, "kendall/2": true, "partial/1": false, "partial/2": true, "pearson/1": false, "pearson/2": true, "spearman/1": true, "spearman/2": true}`.

Spatial (100 km) cells are informational; the procedures assume independent areas.
