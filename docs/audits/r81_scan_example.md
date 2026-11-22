# Round 81 example: low-birth-weight clusters in MI and NY counties (CHR&R 2025, births 2017-2023)

Exploratory (no pre-specified window); author self-review, not independent. Expected counts proportional to live births; 50% maximum window; 999 Monte Carlo replicates. 144 counties scanned (1 excluded: no published count).

| Cluster | Counties | Centre | Cases / expected | RR | p (MC) |
| :--- | ---: | :--- | :--- | ---: | ---: |
| primary | 1 | 26163 | 17331 / 12943 | 1.37 | 0.001 |
| secondary 1 | 1 | 36005 | 13261 / 10878 | 1.24 | 0.001 |
| secondary 2 | 1 | 26049 | 3295 / 2622 | 1.26 | 0.001 |
| secondary 3 | 1 | 36081 | 16213 / 15274 | 1.07 | 0.001 |

Primary cluster counties: 26163.

Notes: 1 counties excluded (CHR&R did not publish the low-birth-weight count); results describe the remaining counties. Exploratory: the window and alpha were not declared in advance; report the cluster as descriptive. Expected counts were scaled to the observed total (conditional on the total).
