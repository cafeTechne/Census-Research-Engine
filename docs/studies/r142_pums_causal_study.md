# Round 142 Study Report: Observational AIPW/IPW Effect of College Attainment (BA+) on Working-Age Poverty (MI & OH PUMS, 2019–2023)

**Pre-registration Protocol SHA-256:** `f50e60b5e06a2a93f6de61083b05497726943a3d8a5a9906b476bfdc38ddbf7c`  
**Script:** [r142_pums_causal_study.py](file:///home/hobo/Projects/US-Census-5-Year-ACS-Data-Batch-Downloader/scripts/r142_pums_causal_study.py)  
**Data:** ACS 5-Year 2019–2023 person PUMS (working-age adults 25–64; deterministic $N = 25{,}000$ analysis sample per state from $N = 244{,}125$ in MI and $N = 280{,}493$ in OH), controlling for `AGEP`, `female`, `disabled`, and `nonwhite`.

## Empirical Results (90% Confidence Intervals, Risk-Difference Scale)

| Metric | Michigan (`26`, Primary) | Ohio (`39`, Replication) |
| :--- | :---: | :---: |
| BA+ Share (`SCHL >= 21`) | `33.34%` | `34.19%` |
| Crude Poverty Rate (BA+ vs. No BA+) | `3.71%` vs. `13.88%` (`-10.17` pp) | `3.51%` vs. `13.71%` (`-10.20` pp) |
| **AIPW ATE** (`estimate_effect`, validated) | **`-8.84` pp** (`-9.46`, `-8.23`) | **`-8.89` pp** (`-9.50`, `-8.29`) |
| **IPW ATE** (`estimate_effect`, validated) | **`-8.84` pp** (`-9.45`, `-8.22`) | **`-8.89` pp** (`-9.49`, `-8.28`) |
| **Overlap-Weighted ATO** (`weights="overlap"`) | **`-8.41` pp** (`-8.97`, `-7.86`) | **`-8.44` pp** (`-8.99`, `-7.89`) |
| Positivity (`limited_overlap` / `share_outside`) | `False` (`0.00%`) | `False` (`0.00%`) |

## Key Findings
1. **Tight Cross-State Replication & Estimator Concordance:** Controlling for age, sex, disability, and race/ethnicity, college attainment is associated with an `-8.84` percentage-point lower working-age poverty probability in Michigan and `-8.89` percentage points in Ohio. AIPW and IPW agree to within `0.01` percentage points in both states, and overlap-weighted ATO is `-8.41` / `-8.44` pp.
2. **Strong Overlap / Positivity:** `0.00%` of observations fall outside the positivity overlap region in either state (`limited_overlap = False`), confirming both AIPW and IPW are validated for this specification.

## Review & Limitations
- **Review status:** Author self-review, not independent.
- **Limitations:** Cross-sectional observational PUMS data; unmeasured confounding (e.g., family socioeconomic background, cognitive/non-cognitive skills) is not controlled, so estimates reflect covariate-adjusted associations under conditional exchangeability rather than randomized causal effects.
