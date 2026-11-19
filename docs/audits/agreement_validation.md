# Agreement between sources: validation (Round 37)

90% coverage >= .86 in every independent cell, per procedure (both limits for B1, B2); failures count as non-coverage; spatial cells informational.

Criterion commit: `e6d4be6`. 2,000 draws per cell.

| A reliability | B error | Range km | B0 | B1_lower | B1_upper | B2_lower | B2_upper | C1 | C2 | K1 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.9 | False | 0 | 0.8995 | 0.8740 | 0.8915 | 0.8695 | 0.8875 | 0.8865 | 0.7745 | 0.8825 |
| 0.9 | False | 100 | 0.8870 | 0.8845 | 0.8730 | 0.8895 | 0.8745 | 0.6495 | 0.5900 | 0.7895 |
| 0.9 | True | 0 | 0.8960 | 0.8550 | 0.8660 | 0.8625 | 0.8630 | 0.8850 | 0.5595 | 0.8980 |
| 0.9 | True | 100 | 0.9000 | 0.8665 | 0.8775 | 0.8735 | 0.8780 | 0.6570 | 0.4870 | 0.8020 |
| 0.7 | False | 0 | 0.8935 | 0.8475 | 0.8375 | 0.8420 | 0.8410 | 0.8585 | 0.4890 | 0.9010 |
| 0.7 | False | 100 | 0.9000 | 0.8395 | 0.8350 | 0.8270 | 0.8260 | 0.6475 | 0.3970 | 0.8325 |
| 0.7 | True | 0 | 0.8945 | 0.8590 | 0.8515 | 0.9035 | 0.8895 | 0.8785 | 0.3820 | 0.9115 |
| 0.7 | True | 100 | 0.8960 | 0.8600 | 0.8710 | 0.9000 | 0.9105 | 0.6800 | 0.3380 | 0.8300 |

Outcomes: `{"B0": true, "B1": false, "B2": false, "C1": false, "C2": false, "K1": true}`.
