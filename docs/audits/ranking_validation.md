# Rank intervals and comparisons with a reference: validation (Round 34)

R1: mean per-area coverage >= .86 and every area >= .80; R2: joint coverage >= .86; R3 judged like R1 (comparison); V1/V2: familywise error <= .13 under the global null; V2: joint coverage >= .86 under the alternative.

Criterion commit: `6286ad9`. 2,000 draws per cell.

| K | SNR | ties | R1 mean / min | R2 joint | R3 mean / min | R1 joint | V1 FWER | V2 FWER | V2 joint |
| ---: | ---: | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 40 | 0.5 | False | 0.9994 / 0.9965 | 0.9985 | 0.7310 / 0.4755 | 0.9765 | 0.0790 | 0.0840 | 0.9015 |
| 40 | 0.5 | True | 0.9994 / 0.9975 | 0.9985 | 0.7662 / 0.4215 | 0.9780 | 0.0830 | 0.1010 | 0.8980 |
| 40 | 2.0 | False | 0.9997 / 0.9975 | 0.9995 | 0.8555 / 0.7745 | 0.9880 | 0.0810 | 0.0815 | 0.9065 |
| 40 | 2.0 | True | 0.9998 / 0.9990 | 1.0000 | 0.8939 / 0.7450 | 0.9920 | 0.0895 | 0.0930 | 0.9055 |
| 145 | 0.5 | False | 0.9998 / 0.9985 | 1.0000 | 0.7031 / 0.3325 | 0.9790 | 0.0900 | 0.0940 | 0.8990 |
| 145 | 0.5 | True | 0.9999 / 0.9985 | 1.0000 | 0.7090 / 0.3270 | 0.9825 | 0.1015 | 0.1090 | 0.9005 |
| 145 | 2.0 | False | 1.0000 / 0.9990 | 1.0000 | 0.8299 / 0.4945 | 0.9950 | 0.0865 | 0.0885 | 0.8960 |
| 145 | 2.0 | True | 1.0000 / 0.9985 | 1.0000 | 0.8333 / 0.4710 | 0.9935 | 0.0920 | 0.0990 | 0.8935 |

Outcomes: `{"R1": true, "R2": true, "R3": false, "V1": true, "V2": true}`.
