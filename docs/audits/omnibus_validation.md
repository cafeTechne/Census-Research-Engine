# Omnibus tests and pairwise comparisons: validation (Round 31)

nominal-.10 null size in [.07,.13] in every judged cell, per candidate x model x design family (W0-W3 independent cells; W4 all applicable cells, where a design the engine refuses is not applicable; failed fits count as rejections; a family with no applicable cell fails); pairwise familywise error <= .13 in independent one-way cells.

Criterion commit: `3e3094a`. 2,000 null and 500 alternative draws per cell; nothing retuned.

| Candidate | Model | Design | Range km | Size .10 | Size .05 | Failed | Power .10 |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| W0 | binomial | ancova4 | 0 | 0.0150 | 0.0075 | 0 | 0.904 |
| W0 | binomial | ancova4 | 100 | 0.0365 | 0.0145 | 0 | 0.802 |
| W0 | binomial | oneway4 | 0 | 0.1335 | 0.0735 | 0 | 1.000 |
| W0 | binomial | oneway4 | 100 | 0.2565 | 0.1680 | 0 | 0.998 |
| W0 | binomial | oneway6 | 0 | 0.1730 | 0.1150 | 0 | 1.000 |
| W0 | binomial | oneway6 | 100 | 0.1530 | 0.0935 | 0 | 1.000 |
| W0 | binomial | spline3 | 0 | 0.0615 | 0.0310 | 0 | 1.000 |
| W0 | binomial | spline3 | 100 | 0.1470 | 0.0925 | 0 | 0.992 |
| W0 | binomial | spline5 | 0 | 0.0305 | 0.0135 | 0 | 1.000 |
| W0 | binomial | spline5 | 100 | 0.0730 | 0.0475 | 0 | 0.996 |
| W0 | binomial | twoway | 0 | 0.1250 | 0.0695 | 0 | 0.958 |
| W0 | binomial | twoway | 100 | 0.0940 | 0.0505 | 0 | 0.998 |
| W0 | linear | ancova4 | 0 | 0.0600 | 0.0265 | 0 | 0.252 |
| W0 | linear | ancova4 | 100 | 0.0515 | 0.0255 | 0 | 0.306 |
| W0 | linear | oneway4 | 0 | 0.0730 | 0.0360 | 0 | 0.374 |
| W0 | linear | oneway4 | 100 | 0.1160 | 0.0630 | 0 | 0.460 |
| W0 | linear | oneway6 | 0 | 0.0720 | 0.0380 | 0 | 0.592 |
| W0 | linear | oneway6 | 100 | 0.1435 | 0.0870 | 0 | 0.654 |
| W0 | linear | spline3 | 0 | 0.0270 | 0.0100 | 0 | 0.298 |
| W0 | linear | spline3 | 100 | 0.1545 | 0.0995 | 0 | 0.376 |
| W0 | linear | spline5 | 0 | 0.0070 | 0.0020 | 0 | 0.142 |
| W0 | linear | spline5 | 100 | 0.0875 | 0.0515 | 0 | 0.244 |
| W0 | linear | twoway | 0 | 0.0590 | 0.0280 | 0 | 0.144 |
| W0 | linear | twoway | 100 | 0.1155 | 0.0595 | 0 | 0.220 |
| W0 | poisson | ancova4 | 0 | 0.0185 | 0.0050 | 0 | 0.892 |
| W0 | poisson | ancova4 | 100 | 0.0425 | 0.0205 | 0 | 0.854 |
| W0 | poisson | oneway4 | 0 | 0.1275 | 0.0750 | 0 | 1.000 |
| W0 | poisson | oneway4 | 100 | 0.2155 | 0.1480 | 0 | 1.000 |
| W0 | poisson | oneway6 | 0 | 0.1730 | 0.1090 | 0 | 1.000 |
| W0 | poisson | oneway6 | 100 | 0.2335 | 0.1645 | 0 | 1.000 |
| W0 | poisson | spline3 | 0 | 0.0475 | 0.0230 | 0 | 1.000 |
| W0 | poisson | spline3 | 100 | 0.1220 | 0.0820 | 0 | 0.996 |
| W0 | poisson | spline5 | 0 | 0.0225 | 0.0090 | 0 | 1.000 |
| W0 | poisson | spline5 | 100 | 0.0870 | 0.0505 | 0 | 0.998 |
| W0 | poisson | twoway | 0 | 0.1065 | 0.0575 | 0 | 0.962 |
| W0 | poisson | twoway | 100 | 0.0965 | 0.0525 | 0 | 1.000 |
| W1 | binomial | ancova4 | 0 | 0.0145 | 0.0055 | 0 | 0.900 |
| W1 | binomial | ancova4 | 100 | 0.0345 | 0.0120 | 0 | 0.796 |
| W1 | binomial | oneway4 | 0 | 0.1295 | 0.0685 | 0 | 1.000 |
| W1 | binomial | oneway4 | 100 | 0.2490 | 0.1580 | 0 | 0.998 |
| W1 | binomial | oneway6 | 0 | 0.1640 | 0.1045 | 0 | 1.000 |
| W1 | binomial | oneway6 | 100 | 0.1470 | 0.0870 | 0 | 1.000 |
| W1 | binomial | spline3 | 0 | 0.0595 | 0.0275 | 0 | 1.000 |
| W1 | binomial | spline3 | 100 | 0.1390 | 0.0895 | 0 | 0.992 |
| W1 | binomial | spline5 | 0 | 0.0280 | 0.0115 | 0 | 1.000 |
| W1 | binomial | spline5 | 100 | 0.0710 | 0.0430 | 0 | 0.996 |
| W1 | binomial | twoway | 0 | 0.1210 | 0.0640 | 0 | 0.958 |
| W1 | binomial | twoway | 100 | 0.0890 | 0.0465 | 0 | 0.998 |
| W1 | linear | ancova4 | 0 | 0.0560 | 0.0230 | 0 | 0.246 |
| W1 | linear | ancova4 | 100 | 0.0480 | 0.0225 | 0 | 0.302 |
| W1 | linear | oneway4 | 0 | 0.0705 | 0.0320 | 0 | 0.352 |
| W1 | linear | oneway4 | 100 | 0.1100 | 0.0585 | 0 | 0.442 |
| W1 | linear | oneway6 | 0 | 0.0680 | 0.0330 | 0 | 0.574 |
| W1 | linear | oneway6 | 100 | 0.1350 | 0.0765 | 0 | 0.636 |
| W1 | linear | spline3 | 0 | 0.0240 | 0.0085 | 0 | 0.294 |
| W1 | linear | spline3 | 100 | 0.1505 | 0.0955 | 0 | 0.364 |
| W1 | linear | spline5 | 0 | 0.0065 | 0.0015 | 0 | 0.134 |
| W1 | linear | spline5 | 100 | 0.0780 | 0.0480 | 0 | 0.236 |
| W1 | linear | twoway | 0 | 0.0560 | 0.0265 | 0 | 0.142 |
| W1 | linear | twoway | 100 | 0.1115 | 0.0560 | 0 | 0.214 |
| W1 | poisson | ancova4 | 0 | 0.0170 | 0.0040 | 0 | 0.878 |
| W1 | poisson | ancova4 | 100 | 0.0405 | 0.0185 | 0 | 0.852 |
| W1 | poisson | oneway4 | 0 | 0.1210 | 0.0705 | 0 | 1.000 |
| W1 | poisson | oneway4 | 100 | 0.2085 | 0.1420 | 0 | 1.000 |
| W1 | poisson | oneway6 | 0 | 0.1635 | 0.1000 | 0 | 1.000 |
| W1 | poisson | oneway6 | 100 | 0.2245 | 0.1535 | 0 | 1.000 |
| W1 | poisson | spline3 | 0 | 0.0435 | 0.0205 | 0 | 1.000 |
| W1 | poisson | spline3 | 100 | 0.1180 | 0.0755 | 0 | 0.996 |
| W1 | poisson | spline5 | 0 | 0.0210 | 0.0080 | 0 | 1.000 |
| W1 | poisson | spline5 | 100 | 0.0795 | 0.0470 | 0 | 0.998 |
| W1 | poisson | twoway | 0 | 0.1035 | 0.0530 | 0 | 0.960 |
| W1 | poisson | twoway | 100 | 0.0915 | 0.0465 | 0 | 1.000 |
| W2 | binomial | ancova4 | 0 | 0.0155 | 0.0065 | 0 | 0.906 |
| W2 | binomial | ancova4 | 100 | 0.0350 | 0.0130 | 0 | 0.800 |
| W2 | binomial | oneway4 | 0 | 0.1360 | 0.0695 | 0 | 1.000 |
| W2 | binomial | oneway4 | 100 | 0.2435 | 0.1410 | 0 | 1.000 |
| W2 | binomial | oneway6 | 0 | 0.1525 | 0.0910 | 0 | 1.000 |
| W2 | binomial | oneway6 | 100 | 0.1330 | 0.0730 | 0 | 1.000 |
| W2 | binomial | spline3 | 0 | 0.0235 | 0.0040 | 0 | 1.000 |
| W2 | binomial | spline3 | 100 | 0.0840 | 0.0385 | 0 | 0.990 |
| W2 | binomial | spline5 | 0 | 0.0065 | 0.0030 | 0 | 1.000 |
| W2 | binomial | spline5 | 100 | 0.0270 | 0.0115 | 0 | 0.974 |
| W2 | binomial | twoway | 0 | 0.1550 | 0.0885 | 0 | 0.976 |
| W2 | binomial | twoway | 100 | 0.1225 | 0.0635 | 0 | 0.998 |
| W2 | linear | ancova4 | 0 | 0.0570 | 0.0240 | 0 | 0.246 |
| W2 | linear | ancova4 | 100 | 0.0500 | 0.0225 | 0 | 0.304 |
| W2 | linear | oneway4 | 0 | 0.0700 | 0.0310 | 0 | 0.352 |
| W2 | linear | oneway4 | 100 | 0.1100 | 0.0570 | 0 | 0.440 |
| W2 | linear | oneway6 | 0 | 0.0630 | 0.0295 | 0 | 0.556 |
| W2 | linear | oneway6 | 100 | 0.1255 | 0.0670 | 0 | 0.620 |
| W2 | linear | spline3 | 0 | 0.0100 | 0.0015 | 0 | 0.140 |
| W2 | linear | spline3 | 100 | 0.0970 | 0.0385 | 0 | 0.286 |
| W2 | linear | spline5 | 0 | 0.0010 | 0.0000 | 0 | 0.046 |
| W2 | linear | spline5 | 100 | 0.0340 | 0.0120 | 0 | 0.128 |
| W2 | linear | twoway | 0 | 0.0610 | 0.0275 | 0 | 0.144 |
| W2 | linear | twoway | 100 | 0.1170 | 0.0595 | 0 | 0.224 |
| W2 | poisson | ancova4 | 0 | 0.0175 | 0.0045 | 0 | 0.886 |
| W2 | poisson | ancova4 | 100 | 0.0410 | 0.0155 | 0 | 0.852 |
| W2 | poisson | oneway4 | 0 | 0.1515 | 0.0805 | 0 | 1.000 |
| W2 | poisson | oneway4 | 100 | 0.2080 | 0.1370 | 0 | 1.000 |
| W2 | poisson | oneway6 | 0 | 0.1720 | 0.0880 | 0 | 1.000 |
| W2 | poisson | oneway6 | 100 | 0.1975 | 0.1300 | 0 | 1.000 |
| W2 | poisson | spline3 | 0 | 0.0130 | 0.0040 | 0 | 1.000 |
| W2 | poisson | spline3 | 100 | 0.0640 | 0.0260 | 0 | 0.994 |
| W2 | poisson | spline5 | 0 | 0.0040 | 0.0010 | 0 | 1.000 |
| W2 | poisson | spline5 | 100 | 0.0235 | 0.0095 | 0 | 0.988 |
| W2 | poisson | twoway | 0 | 0.1225 | 0.0655 | 0 | 0.978 |
| W2 | poisson | twoway | 100 | 0.1100 | 0.0590 | 0 | 1.000 |
| W3 | binomial | ancova4 | 0 | 0.1385 | 0.0715 | 0 | 0.986 |
| W3 | binomial | ancova4 | 100 | 0.1560 | 0.0980 | 0 | 0.958 |
| W3 | binomial | oneway4 | 0 | 0.1080 | 0.0490 | 0 | 1.000 |
| W3 | binomial | oneway4 | 100 | 0.2360 | 0.1475 | 0 | 1.000 |
| W3 | binomial | oneway6 | 0 | 0.1275 | 0.0695 | 0 | 1.000 |
| W3 | binomial | oneway6 | 100 | 0.1120 | 0.0585 | 0 | 1.000 |
| W3 | binomial | spline3 | 0 | 0.0905 | 0.0465 | 0 | 1.000 |
| W3 | binomial | spline3 | 100 | 0.2730 | 0.1840 | 0 | 1.000 |
| W3 | binomial | spline5 | 0 | 0.0815 | 0.0405 | 0 | 1.000 |
| W3 | binomial | spline5 | 100 | 0.2020 | 0.1335 | 0 | 1.000 |
| W3 | binomial | twoway | 0 | 0.1675 | 0.0900 | 0 | 0.990 |
| W3 | binomial | twoway | 100 | 0.1405 | 0.0710 | 0 | 0.998 |
| W3 | linear | ancova4 | 0 | 0.1100 | 0.0550 | 0 | 0.364 |
| W3 | linear | ancova4 | 100 | 0.1250 | 0.0585 | 0 | 0.450 |
| W3 | linear | oneway4 | 0 | 0.1060 | 0.0530 | 0 | 0.434 |
| W3 | linear | oneway4 | 100 | 0.1700 | 0.0940 | 0 | 0.524 |
| W3 | linear | oneway6 | 0 | 0.1015 | 0.0510 | 0 | 0.672 |
| W3 | linear | oneway6 | 100 | 0.2100 | 0.1240 | 0 | 0.718 |
| W3 | linear | spline3 | 0 | 0.0870 | 0.0385 | 0 | 0.508 |
| W3 | linear | spline3 | 100 | 0.3250 | 0.2265 | 0 | 0.550 |
| W3 | linear | spline5 | 0 | 0.0645 | 0.0290 | 0 | 0.434 |
| W3 | linear | spline5 | 100 | 0.2960 | 0.2060 | 0 | 0.538 |
| W3 | linear | twoway | 0 | 0.0975 | 0.0440 | 0 | 0.220 |
| W3 | linear | twoway | 100 | 0.1825 | 0.1030 | 0 | 0.318 |
| W3 | poisson | ancova4 | 0 | 0.1370 | 0.0660 | 0 | 0.982 |
| W3 | poisson | ancova4 | 100 | 0.1810 | 0.1040 | 0 | 0.974 |
| W3 | poisson | oneway4 | 0 | 0.1310 | 0.0615 | 0 | 1.000 |
| W3 | poisson | oneway4 | 100 | 0.1920 | 0.1090 | 0 | 1.000 |
| W3 | poisson | oneway6 | 0 | 0.1190 | 0.0600 | 0 | 1.000 |
| W3 | poisson | oneway6 | 100 | 0.1715 | 0.1020 | 0 | 1.000 |
| W3 | poisson | spline3 | 0 | 0.1025 | 0.0470 | 0 | 1.000 |
| W3 | poisson | spline3 | 100 | 0.2285 | 0.1445 | 0 | 1.000 |
| W3 | poisson | spline5 | 0 | 0.0720 | 0.0320 | 0 | 1.000 |
| W3 | poisson | spline5 | 100 | 0.2075 | 0.1325 | 0 | 1.000 |
| W3 | poisson | twoway | 0 | 0.1365 | 0.0705 | 0 | 0.992 |
| W3 | poisson | twoway | 100 | 0.1185 | 0.0615 | 0 | 1.000 |
| W4 | binomial | ancova4 | 0 | 0.0795 | 0.0460 | 0 | 0.838 |
| W4 | binomial | ancova4 | 100 | 1.0000 | 1.0000 | 2000 | 0.000 |
| W4 | binomial | oneway4 | 0 | 0.0970 | 0.0495 | 0 | 1.000 |
| W4 | binomial | oneway4 | 100 | n/a | n/a | 0 | n/a |
| W4 | binomial | oneway6 | 0 | n/a | n/a | 0 | n/a |
| W4 | binomial | oneway6 | 100 | n/a | n/a | 0 | n/a |
| W4 | binomial | spline3 | 0 | 0.0850 | 0.0395 | 0 | 0.998 |
| W4 | binomial | spline3 | 100 | 0.1030 | 0.0625 | 58 | 0.862 |
| W4 | binomial | spline5 | 0 | 0.0905 | 0.0490 | 13 | 0.858 |
| W4 | binomial | spline5 | 100 | 0.4840 | 0.4600 | 889 | 0.326 |
| W4 | binomial | twoway | 0 | 1.0000 | 1.0000 | 2000 | 0.000 |
| W4 | binomial | twoway | 100 | n/a | n/a | 0 | n/a |
| W4 | linear | ancova4 | 0 | 0.1000 | 0.0485 | 0 | 0.186 |
| W4 | linear | ancova4 | 100 | 0.1035 | 0.0525 | 0 | 0.246 |
| W4 | linear | oneway4 | 0 | 0.0930 | 0.0510 | 0 | 0.268 |
| W4 | linear | oneway4 | 100 | n/a | n/a | 0 | n/a |
| W4 | linear | oneway6 | 0 | n/a | n/a | 0 | n/a |
| W4 | linear | oneway6 | 100 | n/a | n/a | 0 | n/a |
| W4 | linear | spline3 | 0 | 0.0805 | 0.0425 | 0 | 0.254 |
| W4 | linear | spline3 | 100 | 0.0925 | 0.0575 | 52 | 0.126 |
| W4 | linear | spline5 | 0 | 0.0860 | 0.0420 | 13 | 0.124 |
| W4 | linear | spline5 | 100 | 0.4960 | 0.4780 | 917 | 0.048 |
| W4 | linear | twoway | 0 | n/a | n/a | 0 | n/a |
| W4 | linear | twoway | 100 | n/a | n/a | 0 | n/a |
| W4 | poisson | ancova4 | 0 | 0.0935 | 0.0465 | 0 | 0.880 |
| W4 | poisson | ancova4 | 100 | n/a | n/a | 0 | n/a |
| W4 | poisson | oneway4 | 0 | 0.0950 | 0.0470 | 0 | 1.000 |
| W4 | poisson | oneway4 | 100 | 0.1000 | 0.0435 | 0 | 0.998 |
| W4 | poisson | oneway6 | 0 | n/a | n/a | 0 | n/a |
| W4 | poisson | oneway6 | 100 | n/a | n/a | 0 | n/a |
| W4 | poisson | spline3 | 0 | 0.0880 | 0.0345 | 0 | 0.996 |
| W4 | poisson | spline3 | 100 | 0.1080 | 0.0640 | 66 | 0.824 |
| W4 | poisson | spline5 | 0 | 0.0790 | 0.0440 | 10 | 0.876 |
| W4 | poisson | spline5 | 100 | 0.4750 | 0.4585 | 888 | 0.298 |
| W4 | poisson | twoway | 0 | n/a | n/a | 0 | n/a |
| W4 | poisson | twoway | 100 | n/a | n/a | 0 | n/a |

| Pairwise | Model | Design | FWER P1 (Holm) | FWER P2 (simultaneous) |
| :--- | :--- | :--- | ---: | ---: |
| independent | linear | oneway4 | 0.0485 | 0.0700 |
| independent | linear | oneway6 | 0.0465 | 0.0665 |
| independent | binomial | oneway4 | 0.0915 | 0.1205 |
| independent | binomial | oneway6 | 0.1165 | 0.1525 |
| independent | poisson | oneway4 | 0.0855 | 0.1180 |
| independent | poisson | oneway6 | 0.1170 | 0.1590 |

Outcomes (candidate/model/family): `{"P1/binomial": true, "P1/linear": true, "P1/poisson": true, "P2/binomial": false, "P2/linear": true, "P2/poisson": false, "W0/binomial/factor": false, "W0/binomial/spline": false, "W0/linear/factor": false, "W0/linear/spline": false, "W0/poisson/factor": false, "W0/poisson/spline": false, "W1/binomial/factor": false, "W1/binomial/spline": false, "W1/linear/factor": false, "W1/linear/spline": false, "W1/poisson/factor": false, "W1/poisson/spline": false, "W2/binomial/factor": false, "W2/binomial/spline": false, "W2/linear/factor": false, "W2/linear/spline": false, "W2/poisson/factor": false, "W2/poisson/spline": false, "W3/binomial/factor": false, "W3/binomial/spline": true, "W3/linear/factor": true, "W3/linear/spline": false, "W3/poisson/factor": false, "W3/poisson/spline": true, "W4/binomial/factor": false, "W4/binomial/spline": false, "W4/linear/factor": true, "W4/linear/spline": false, "W4/poisson/factor": true, "W4/poisson/spline": false}`.

W0 is the Round 27 chi-squared reference (comparison only). W1-W3 assume independent areas and are judged on independent cells; their spatial-cell sizes are informational. W4 targets the naive (observed-ACS) coefficients through the fixed eight MI/NY clusters and is judged on all cells.
