# Round 29 under negative binomial errors: post hoc sensitivity (Round 44)

**Post hoc; author self-review, not independent. Registered results are unchanged.** Script
`scripts/r44_posthoc_r29.py`, criterion `docs/audits/ohpa_revalidation_criterion.md` (commit `09ecd91`, pushed
before the run). Input: the released `r29_study_outputs.tar.gz` (SHA-256 `a9bebd585fb6d703…`), verified
by manifest hash and file checksums, network blocked.

Why: Round 29 fitted Poisson with HC3 standard errors, and Round 39 found that interval under-covers
(.81–.87) with strong overdispersion. NB2 with HC3 passed (.885–.901).

Slope of log mortality on poverty (percentage points), one-sided p-values Holm-adjusted across H1–H3.
Registered: Poisson HC3 plus ACS replicate variance (conservative target). P0: Poisson HC3, model SE
only (population target). P1: NB2-HC3 (population target). Holds = Holm p < .10.

## MI/NY (registered study)

| Hypothesis | Registered b (SE), Holm p | P0 b (SE), Holm p | P1 NB2 b (SE), Holm p | NB2 alpha | Reading |
| :--- | :--- | :--- | :--- | ---: | :--- |
| H1 | 0.0270 (0.0055), 1.4e-06 | 0.0270 (0.0055), 1.3e-06 | 0.0293 (0.0036), 9.4e-16 | 0.017 | holds |
| H2 | 0.0384 (0.0152), 0.011 | 0.0384 (0.0152), 0.011 | 0.0362 (0.0086), 1.3e-05 | 0.105 | holds |
| H3 | 0.0132 (0.0060), 0.014 | 0.0132 (0.0060), 0.014 | 0.0172 (0.0029), 2e-09 | 0.017 | holds |

P2 (exploratory): H2 with the 13 suppressed counties as counts in [1, 9]: b = 0.0383
(SE 0.0114), one-sided p = 0.00038, close to the complete-case estimate. No hidden count
is estimated or reported. WONDER disclosure audit: passed.

## OH/PA (registered replication)

| Hypothesis | Registered b (SE), Holm p | P0 b (SE), Holm p | P1 NB2 b (SE), Holm p | NB2 alpha | Reading |
| :--- | :--- | :--- | :--- | ---: | :--- |
| H1 | 0.0350 (0.0048), 1.8e-13 | 0.0350 (0.0047), 9.7e-14 | 0.0388 (0.0039), 1.5e-23 | 0.016 | holds |
| H2 | 0.0588 (0.0049), 2.2e-33 | 0.0588 (0.0047), 9.3e-36 | 0.0726 (0.0081), 3e-19 | 0.109 | holds |
| H3 | 0.0228 (0.0041), 1.1e-08 | 0.0228 (0.0041), 9e-09 | 0.0211 (0.0034), 1.5e-10 | 0.017 | holds |

P2 (exploratory): H2 with the 3 suppressed counties as counts in [1, 9]: b = 0.0587
(SE 0.0042), one-sided p = 3.1e-45, close to the complete-case estimate. No hidden count
is estimated or reported. WONDER disclosure audit: passed.

## Reading

Every hypothesis that held as registered also holds under NB2, in MI/NY and in the OH/PA replication, so
the Round 39 caveat does not change Round 29's conclusions. NB2 slopes are similar. P0 matches the
registered SEs closely, so ACS replicate variance adds little there; NB2's smaller HC3 SEs come from its
weighting (its variance grows with the square of the mean, so the largest counties count less than under
Poisson). These are post hoc checks; the registered conservative results remain the study's results.

## Exception (recorded, no results seen)

The first post hoc run stopped before producing any output: statsmodels' default optimizer for the NB2
alpha (BFGS) did not converge for OH/PA premature deaths (Newton returned NaN for H1/H3 in both regions):
large counts with little overdispersion. The estimator is unchanged; `census.count_models` now retries
with Nelder–Mead polished by BFGS when BFGS fails (results equal the frozen core whenever BFGS converges;
`tests/test_round44.py`). The run was then repeated unchanged.

Supporting coefficients (`r44_posthoc_outputs.tar.gz`, coefficients only) are a release attachment.
