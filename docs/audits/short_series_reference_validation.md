# Short interrupted series and estimated reference populations: validation (Round 55)

I: AR(1) series of 15-25 points; I2 Round 48 bootstrap-t (comparison), I3 bootstrap-t at a bias-corrected AR coefficient, I4 EWC HAR t test; validated down to the smallest n where both changes cover >= .86 for both phi there and at every larger n. R: SMR with an estimated reference population; R1 adds the population SE, R0 does not; R1 passes with >= .86 in all eight cells.

Criterion commit: `dd6d6b7`. 2,000 draws per cell.

| n | phi | I2 level / slope | I3 level / slope | I4 level / slope | Failed (I2/I3/I4) |
| ---: | ---: | :--- | :--- | :--- | :--- |
| 15 | 0.3 | 0.8820 / 0.8715 | 0.8785 / 0.8800 | 0.7200 / 0.7020 | 0/0/0 |
| 15 | 0.6 | 0.8800 / 0.8460 | 0.8885 / 0.8570 | 0.6985 / 0.6185 | 0/0/0 |
| 20 | 0.3 | 0.8755 / 0.8810 | 0.8790 / 0.8875 | 0.6585 / 0.6985 | 0/0/0 |
| 20 | 0.6 | 0.8780 / 0.8575 | 0.8820 / 0.8675 | 0.6550 / 0.6165 | 0/0/0 |
| 25 | 0.3 | 0.8930 / 0.8860 | 0.8895 / 0.8895 | 0.6825 / 0.7080 | 0/0/0 |
| 25 | 0.6 | 0.8830 / 0.8720 | 0.8840 / 0.8765 | 0.6505 / 0.6315 | 0/0/0 |

| Reference deaths | Population CV | E | R1 | R0 | Refused (R1/R0) | O = 0 |
| ---: | ---: | ---: | ---: | ---: | :--- | ---: |
| 50 | 0.02 | 10 | 0.8960 | 0.8960 | 2/2 | 0 |
| 50 | 0.02 | 100 | 0.8945 | 0.8940 | 2/2 | 0 |
| 50 | 0.08 | 10 | 0.8930 | 0.8910 | 0/0 | 0 |
| 50 | 0.08 | 100 | 0.8920 | 0.8795 | 1/1 | 0 |
| 500 | 0.02 | 10 | 0.9080 | 0.9075 | 0/0 | 0 |
| 500 | 0.02 | 100 | 0.9010 | 0.8995 | 0/0 | 0 |
| 500 | 0.08 | 10 | 0.9010 | 0.8925 | 0/0 | 0 |
| 500 | 0.08 | 100 | 0.9040 | 0.8630 | 0/0 | 0 |

Outcomes: `{"I2_min_n": 25, "I3_min_n": 20, "I4_min_n": null, "R0": true, "R1": true}`.
