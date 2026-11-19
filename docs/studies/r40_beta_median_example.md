# Round 40 example: poverty by metro class and age structure, beta and median models (exploratory)

**Exploratory; author self-review, not independent. Not registered.** Round 31 example frame (145
MI/NY counties, ACS 2018–2022). Model: poverty ~ metro class (reference nonmetro) + share aged 65+.
Reproduce: `scripts/r40_beta_median_example.py r31_example_outputs.tar.gz OUT_DIR`.

| Term | Beta (log-odds of the mean share; 90% CI) | Median regression (points) | OLS (points; Round 31 ANCOVA) |
| :--- | :--- | :--- | :--- |
| Large metro | −0.33 (−0.47 to −0.20); odds ratio 0.72 | −3.0 (−4.9 to −1.2) | −3.3 (−4.7 to −1.9) |
| Other metro | −0.17 (−0.26 to −0.08); odds ratio 0.84 | −1.7 (−3.2 to −0.2) | −2.0 (−3.2 to −0.8) |
| Share 65+ (per point) | −0.015 (−0.025 to −0.004) | −0.09 (−0.23 to 0.06) | −0.17 (−0.28 to −0.06) |

- The metro-class gaps agree across the three models.
- The age-structure slope does not: the median model's slope is half the OLS slope and its interval
  includes zero. The OLS association with the share 65+ is driven by the tails (Round 33 found the
  Bronx the most influential county), not by the typical county.
- The beta model keeps predictions inside (0, 1) and gives odds ratios for the mean share.

Limits: exploratory; counties treated as independent; naive target (covariate sampling error not corrected).
