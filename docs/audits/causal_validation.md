# Treatment effects, instrumental variables and mediation: validation (Round 41)

90% coverage >= .86: treatment in reliability 1.0 and 0.9 cells; 2SLS in all IV cells; mediation in the exact-mediator cell; failures count as non-coverage; other cells informational.

Criterion commit: `b7464e5`. 2,000 draws per cell.

| Kind | Reliability | Instrument reliability | Coverage | Bias |
| :--- | ---: | ---: | :--- | :--- |
| treatment | 1.0 |  | T1 0.8935, T2 0.8960, T3 0.8955 | T1 -0.008, T2 -0.007, T3 -0.007 |
| treatment | 0.9 |  | T1 0.8960, T2 0.8960, T3 0.8985 | T1 +0.004, T2 +0.004, T3 +0.005 |
| treatment | 0.7 |  | T1 0.8875, T2 0.8855, T3 0.8895 | T1 +0.002, T2 +0.002, T3 +0.002 |
| iv | 0.9 | 0.9 | I0 0.8025, I1 0.8815 | I0 -0.054, I1 -0.003 |
| iv | 0.9 | 0.7 | I0 0.8185, I1 0.8840 | I0 -0.049, I1 +0.002 |
| iv | 0.7 | 0.9 | I0 0.3075, I1 0.9000 | I0 -0.151, I1 +0.002 |
| iv | 0.7 | 0.7 | I0 0.3000, I1 0.9070 | I0 -0.152, I1 +0.002 |
| mediation | 1.0 |  | S1 0.8760, S2 0.8910 | S1 -0.001, S2 -0.001 |
| mediation | 0.8 |  | S1 0.6905, S2 0.7245 | S1 -0.046, S2 -0.046 |

Outcomes: `{"I1": true, "S1": true, "S2": true, "T1": true, "T2": true, "T3": true}`.

**Design limitation (found after the run; results unchanged).** In the treatment cells the two
confounders affect treatment in opposite directions (0.5Z₁ − 0.5Z₂) and the outcome in the same
direction, so the residual confounding left by their sampling errors largely cancels. The good
coverage at reliability 0.7 therefore does **not** show robustness to error-prone confounders; the
engine says so, and a design where the biases add (same-sign effects) is backlog.
