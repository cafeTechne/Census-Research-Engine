# Multivariate group tests and count-model slopes: validation (Round 39)

V1: nominal-.10 size in [.07,.13] in every multivariate cell; counts: 90% coverage of the family's naive-target slope >= .86 (poisson, negbin all cells; zip low-count cells with structural zeros); failures count as rejections / non-coverage; V0 informational.

Criterion commit: `0686bc0`. 2,000 draws per cell.

| Outcomes | Design | V1 size .10 | V0 Pillai (iid) size .10 | failures |
| ---: | :--- | ---: | ---: | ---: |
| 2 | oneway4 | 0.0900 | 0.0915 | 0 |
| 2 | ancova4 | 0.0995 | 0.0895 | 0 |
| 3 | oneway4 | 0.0985 | 0.0925 | 0 |
| 3 | ancova4 | 0.1005 | 0.0955 | 0 |

| E median | gamma shape | zero share | Poisson HC3 | NB2 HC3 | ZIP | failures |
| ---: | :--- | ---: | ---: | ---: | ---: | :--- |
| 100 | None | 0.0 | 0.8550 | 0.8865 | 0.0015 | {'poisson': 0, 'negbin': 0, 'zip': 1997} |
| 100 | None | 0.2 | 0.8525 | 0.9005 | 0.3570 | {'poisson': 0, 'negbin': 0, 'zip': 1155} |
| 100 | 2.0 | 0.0 | 0.8405 | 0.8845 | 0.2000 | {'poisson': 0, 'negbin': 0, 'zip': 1517} |
| 100 | 2.0 | 0.2 | 0.8130 | 0.8970 | 0.2880 | {'poisson': 0, 'negbin': 0, 'zip': 1273} |
| 10 | None | 0.0 | 0.8605 | 0.8890 | 0.1065 | {'poisson': 0, 'negbin': 0, 'zip': 1745} |
| 10 | None | 0.2 | 0.8670 | 0.8890 | 0.8395 | {'poisson': 0, 'negbin': 0, 'zip': 0} |
| 10 | 2.0 | 0.0 | 0.8075 | 0.8885 | 0.7805 | {'poisson': 0, 'negbin': 0, 'zip': 66} |
| 10 | 2.0 | 0.2 | 0.8415 | 0.8865 | 0.8345 | {'poisson': 0, 'negbin': 0, 'zip': 1} |

Outcomes: `{"V1": true, "negbin": true, "poisson": false, "zip": false}`.
