# Round 33 example: rank methods on MI/NY county poverty (exploratory)

**Exploratory; author self-review, not independent. Not registered.** Shows the Round 33
procedures working on real data.

Data: the 145 MI/NY counties, ACS 2018–2022 poverty rate, share aged 65+ (with 80 VRE replicates)
and population, and the metro classes of the Round 31 example (input: `r31_example_outputs.tar.gz`).
Reproduce: `scripts/r33_rank_methods_example.py r31_example_outputs.tar.gz OUT_DIR`.

## Correlations (90% intervals; the correlation of the ACS estimates as observed)

| Pair | Method | r | Interval | Status |
| :--- | :--- | ---: | :--- | :--- |
| poverty, log population | Spearman | −0.11 | −0.25 to 0.03 | validated |
| poverty, log population | Kendall | −0.08 | −0.17 to 0.01 | validated |
| poverty, share 65+ | Pearson with replicates | −0.03 | −0.18 to 0.11 | validated |
| poverty, share 65+ | Pearson without replicates | −0.03 | −0.17 to 0.11 | exploratory |

The replicate-augmented Pearson interval is about 7% wider: in validation the plain Fisher-z
interval under-covered (0.84) for skewed ACS estimates.

## Rank comparisons of groups

- Nonmetro vs large-metro poverty: probability that a nonmetro county's rate exceeds a large-metro
  county's = **0.72** (0.61–0.83); Brunner–Munzel p = 0.002 (validated).
- Kruskal–Wallis across the three metro classes: H = 13.2 on 2 df, p = 0.001; ε² = 0.09.
- These agree with Round 31's model-based ANOVA (joint p = 0.010) and do not depend on the rates'
  skewness.

## Model diagnostics (Round 31 ANCOVA: poverty ~ metro class + share 65+)

Variance inflation factors 1.30–1.42 (no collinearity concern). The most influential county is the
Bronx, NY (Cook's distance 0.22, roughly 2.5× the next, Isabella County, MI). Breusch–Pagan
p = 0.07 and RESET p = 0.14; residual skewness 0.84 (right-skewed). These describe the model and
are not grounds for changing the analysis after seeing results; a registered study would state
in advance how it handles influential areas.

## Limits

Exploratory; counties treated as independent (correlation intervals under-covered badly in
spatially correlated validation cells); correlations of estimates are attenuated by sampling error.
