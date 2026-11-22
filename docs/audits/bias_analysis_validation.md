# Round 86: probabilistic misclassification bias analysis

Criterion commit: `734cce55b6144649654d2fcbfe3aaf73d7352e81`. 1000 draws per cell, 5000 simulations each; 90% total-error intervals. Author self-review, not independent.

| Kind | True RR | Prior | RR coverage | OR coverage | Uncorrected RR coverage | Discarded simulations |
| :--- | ---: | :--- | ---: | ---: | ---: | ---: |
| outcome_nd | 1.0 | correct | 0.757 | 0.756 | 0.891 | 0.002 |
| outcome_nd | 1.0 | offset | 0.680 | 0.679 | 0.906 | 0.010 |
| outcome_nd | 2.0 | correct | 0.967 | 0.956 | 0.103 | 0.002 |
| outcome_nd | 2.0 | offset | 0.824 | 0.779 | 0.111 | 0.007 |
| outcome_diff | 1.0 | correct | 1.000 | 1.000 | 0.219 | 0.004 |
| outcome_diff | 1.0 | offset | 1.000 | 1.000 | 0.190 | 0.017 |
| outcome_diff | 2.0 | correct | 1.000 | 1.000 | 0.000 | 0.002 |
| outcome_diff | 2.0 | offset | 0.995 | 0.995 | 0.002 | 0.012 |
| exposure_nd | 1.0 | correct | 0.798 | 0.798 | 0.891 | 0.000 |
| exposure_nd | 1.0 | offset | 0.778 | 0.778 | 0.900 | 0.000 |
| exposure_nd | 2.0 | correct | 0.829 | 0.826 | 0.347 | 0.000 |
| exposure_nd | 2.0 | offset | 0.681 | 0.675 | 0.345 | 0.000 |

Outcomes: `{"P1": false}` (offset-prior cells reported only).
