# Round 46 exploratory example: Round 29 mortality slopes corrected for poverty's sampling error

**Status: exploratory example, not a registered study. Author self-review, not independent.** The
registered Round 29 results are unchanged; this sits beside them and the Round 44 NB2 post hoc.

Script: `scripts/r46_rc_example.py` (reads the verified Round 29 bundles; HTTP blocked; WONDER
disclosure audit passed in both regions; coefficients only, no counts). Outputs archived outside the repo
(`/tmp/r46_example_outputs.tar.gz`, sha256 `f36c5e62…146118a`).

**Why this example rather than the planned one.** The plan proposed county child poverty on income and
unemployment, fitted as a binomial model with regression calibration. Binomial regression calibration
failed its validation (.851 in one cell, `docs/audits/glm_correction_validation.md`) and is
exploratory, so the example uses NB2, which passed (.887–.918): the Round 29 H1–H3 SMR models
(deaths with expected deaths as the exposure, poverty % and a state term). It compares the naive NB2-HC3
slope (Round 44) with NB2 regression calibration of poverty's ACS sampling error (200 row-bootstrap
resamples, seed 46). Poverty is the only covariate treated as error-prone. Expected deaths are held fixed.

| Region | Hypothesis | Naive NB2-HC3, 90% CI | Regression calibration (NB2), 90% CI |
| :--- | :--- | :--- | :--- |
| MI/NY | H1 premature, all causes | 0.0293 (0.0233, 0.0353) | 0.0311 (0.0243, 0.0378) |
| MI/NY | H2 drug overdose | 0.0362 (0.0220, 0.0503) | 0.0381 (0.0216, 0.0547) |
| MI/NY | H3 heart disease | 0.0172 (0.0125, 0.0220) | 0.0179 (0.0129, 0.0229) |
| OH/PA | H1 premature, all causes | 0.0388 (0.0325, 0.0452) | 0.0422 (0.0350, 0.0494) |
| OH/PA | H2 drug overdose | 0.0726 (0.0593, 0.0859) | 0.0773 (0.0623, 0.0923) |
| OH/PA | H3 heart disease | 0.0211 (0.0156, 0.0267) | 0.0233 (0.0173, 0.0292) |

Poverty's estimated reliability is .932 in MI/NY and .929 in OH/PA. As expected at that reliability, the
correction raises every slope by 4–10% and widens its interval slightly. No interval reaches zero.

**Limits.** The validation assumed independent areas. Round 30 found Round 29's H2 not robust to spatial
dependence, and regression calibration does not address dependence. Only poverty's error is corrected.
These are coefficients on the log-SMR scale per percentage point of poverty.
