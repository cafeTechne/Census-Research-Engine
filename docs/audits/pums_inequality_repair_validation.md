# PUMS inequality repairs: validation (Round 60)

Round 56 generator, cells, incomes and targets. T0 Round 56 normal interval (comparison); T1 transformed SDR interval (log Theil, logit Atkinson and top share); T2 SDR bias correction then T1. Pass: coverage >= .86 in every cell on every income; else a 7,000-record gate if every m = 3000 cell passes.

Criterion commit: `60a3b06`. 2,000 draws per cell.

| Income | Measure | Procedure | Lowest cell | Lowest m = 3000 cell | Highest cell | Failed |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: |
| I1 | theil_t | T0 | 0.8630 | 0.8770 | 0.8890 | 0 |
| I1 | theil_t | T1 | 0.8645 | 0.8745 | 0.8895 | 0 |
| I1 | theil_t | T2 | 0.8565 | 0.8675 | 0.8820 | 0 |
| I1 | atkinson_0.5 | T0 | 0.8775 | 0.8795 | 0.8940 | 0 |
| I1 | atkinson_0.5 | T1 | 0.8785 | 0.8800 | 0.8920 | 0 |
| I1 | atkinson_0.5 | T2 | 0.8680 | 0.8735 | 0.8815 | 0 |
| I1 | atkinson_1 | T0 | 0.8825 | 0.8840 | 0.8910 | 0 |
| I1 | atkinson_1 | T1 | 0.8850 | 0.8855 | 0.8910 | 0 |
| I1 | atkinson_1 | T2 | 0.8715 | 0.8740 | 0.8855 | 0 |
| I1 | top10_share | T0 | 0.8675 | 0.8830 | 0.8915 | 0 |
| I1 | top10_share | T1 | 0.8680 | 0.8845 | 0.8905 | 0 |
| I1 | top10_share | T2 | 0.8620 | 0.8730 | 0.8850 | 0 |
| I2 | theil_t | T0 | 0.8160 | 0.8535 | 0.8750 | 0 |
| I2 | theil_t | T1 | 0.8200 | 0.8595 | 0.8760 | 0 |
| I2 | theil_t | T2 | 0.8190 | 0.8515 | 0.8680 | 0 |
| I2 | atkinson_0.5 | T0 | 0.8470 | 0.8695 | 0.8885 | 0 |
| I2 | atkinson_0.5 | T1 | 0.8465 | 0.8715 | 0.8890 | 0 |
| I2 | atkinson_0.5 | T2 | 0.8415 | 0.8635 | 0.8820 | 0 |
| I2 | atkinson_1 | T0 | 0.8690 | 0.8775 | 0.8930 | 0 |
| I2 | atkinson_1 | T1 | 0.8720 | 0.8780 | 0.8930 | 0 |
| I2 | atkinson_1 | T2 | 0.8600 | 0.8715 | 0.8805 | 0 |
| I2 | top10_share | T0 | 0.8455 | 0.8715 | 0.8885 | 0 |
| I2 | top10_share | T1 | 0.8475 | 0.8720 | 0.8885 | 0 |
| I2 | top10_share | T2 | 0.8460 | 0.8625 | 0.8825 | 0 |
| I3 | top10_share | T0 | 0.8745 | 0.8885 | 0.9015 | 0 |
| I3 | top10_share | T1 | 0.8760 | 0.8885 | 0.9010 | 0 |
| I3 | top10_share | T2 | 0.8610 | 0.8835 | 0.8925 | 0 |

| Measure | Validated procedure | Record gate |
| :--- | :--- | :--- |
| atkinson_0.5 | T1 | 7000 |
| atkinson_1 | T1 | None |
| theil_t | None | None |
| top10_share | T1 | 7000 |

Outcomes: `{"atkinson_0.5": ["T1", 7000], "atkinson_1": ["T1", null], "theil_t": [null, null], "top10_share": ["T1", 7000]}`.
