# Round 47 exploratory example: instrumented poverty slopes and calibrated treatment effects

**Status: exploratory example, not a registered study. Author self-review, not independent.**

Script: `scripts/r47_causal_example.py`. It reads the verified Round 29 bundle (MI/NY), the Round 31
county frame (metro class, share aged 65+ with replicate SEs) and the cached 2011–2015 tract tables
(read-only). HTTP is blocked. The WONDER disclosure audit passed. The outputs are coefficients only,
archived outside the repo (`/tmp/r47_example_outputs.tar.gz`, sha256 `2b748327…08cce910c`).

The outcome is the log SMR (deaths over expected deaths) for H1–H3. Counties whose counts are hidden or
zero are excluded, which leaves 132 counties for H2, so these are complete-case fits.

## (a) Poverty 2018–2022, instrumented by poverty 2011–2015

The two releases do not share any sample years, so their sampling errors are independent. Poverty in
2011–2015 is summed from the cached tract tables. The model includes a state term. The two releases
correlate .874.

| | n | First-stage F | Naive OLS | 2SLS, 90% CI | Anderson–Rubin, 90% |
| :--- | ---: | ---: | :--- | :--- | :--- |
| H1 premature, all causes | 145 | 570.5 | 0.0291 | 0.0311 (0.0240, 0.0382) | (0.0251, 0.0372) |
| H2 drug overdose | 132 | 665.7 | 0.0309 | 0.0290 (0.0129, 0.0451) | (0.0129, 0.0450) |
| H3 heart disease | 145 | 570.5 | 0.0176 | 0.0174 (0.0119, 0.0229) | (0.0115, 0.0234) |

The instrument is very strong, so the 2SLS and AR intervals nearly agree. The instrumented slopes are
close to the naive ones and to the Round 46 calibrated slopes (H1 0.0311), as expected at a poverty
reliability of about .93.

**Exclusion restriction.** Poverty in 2011–2015 must affect 2018–2022 mortality only through current
poverty. That is doubtful for chronic causes such as heart disease. This is an illustration, not a
causal claim.

## (b) Effect of metro status on the log SMR, adjusting for poverty and share 65+

There are 67 metro and 78 nonmetro counties. Both confounders carry ACS SEs.

| | Plain AIPW, 90% CI | Calibrated AIPW, 90% percentile bootstrap |
| :--- | :--- | :--- |
| H1 | −0.183 (−0.411, 0.045) | −0.166 (−0.353, 0.038) |
| H2 | 0.111 (−0.099, 0.321) | 0.125 (−0.085, 0.342) |
| H3 | −0.081 (−0.137, −0.025) | −0.077 (−0.141, −0.015) |

Both confounders are measured precisely at the county level, so calibration changes the estimates by
only 0.004–0.017. Only H3 excludes zero, under both methods.

**Assumptions.** These readings assume no unmeasured confounding and independent counties, and the
independence assumption is known to fail for this outcome (Round 30). The share 65+ comes from a
different ACS extract than poverty.
