# Round 33 plan: rank correlation, rank-based group tests and model diagnostics (area data)

**Goal.** `correlation_matrix` already reports Pearson and Spearman coefficients with Fisher-z
intervals and, separately, replicate SEs; neither interval was validated under ACS sampling error,
and Kendall, partial correlation and rank-based group comparisons do not exist. This round:

- **(A)** validates rank and partial correlation intervals and two rank-based group procedures on
  area data with ACS-type error (Round 31 geometry and generators);
- **(B)** ships the passing procedures in `correlation_matrix` (methods `kendall`, `partial`;
  validated flags) and `compare_groups(method="rank")`, and adds descriptive model diagnostics to
  `fit_model` output;
- **(C)** runs one exploratory MI/NY example.

Version 0.30.0 (Round 32 is 0.29.0). Baseline: 1922 passed, 37 skipped. Ground rules as Round 31
(branch `phase33/rank-methods`; validation first; the maintainer agent implements and merges;
releases wait for the owner).

## 1. Procedures

For n areas with observed x, y (and a control z): r the coefficient on the observed estimates;
v_rep the replicate variance of atanh(r) (r recomputed on each of the 80 replicate sets, 4/80 Σ).

| ID | Coefficient | Interval for atanh(r) |
| :--- | :--- | :--- |
| P1 / P2 | Pearson | SE² = 1/(n − 3) / plus v_rep |
| S1 / S2 | Spearman | SE² = 1.06/(n − 3) / plus v_rep |
| K1 / K2 | Kendall τ_b | SE² = 0.437/(n − 4) (Fieller, Hartley and Pearson 1957) / plus v_rep |
| Q1 / Q2 | partial Pearson given z | SE² = 1/(n − 4) / plus v_rep |

Group rank procedures (two groups; areas): **B1** probability of superiority p̂ = P(X > Y) + ½P(X = Y)
with the Brunner–Munzel variance and t(df_BM) interval; **B2** the same with v_rep of p̂ added.
**KW** Kruskal–Wallis test for k = 4 groups (scipy), iid reference; reported as a test only.

## 2. Validation (`scripts/rank_validation.py` → `docs/audits/rank_validation.md`/`.json`)

- 145 MI/NY counties, fixed coordinates from `docs/audits/im_acs_beta_star.json`; fields independent
  or spatial (range 100 km), as Round 31.
- True values: (x, y, z) Gaussian fields transformed to skewed marginals (exp(0.5·field)); corr(x, y)
  ∈ {0, 0.4}; z correlated 0.5 with x. Observed = true + error with per-area lognormal SEs scaled to
  reliability ∈ {0.9, 0.7}; replicates from `census.simulation.make_replicates`.
- **Targets:** the population value of each coefficient **on the observed estimates** (the naive
  estimand, as Round 30 C1), from one 400,000-area reference sample per cell, committed with the
  criterion. Coverage of the error-free coefficient is reported (informational; attenuation expected).
- Groups (B, KW): fixed per cell as Round 31's urbanicity groups; under the null the true outcome is
  identically distributed in every group, but group 2's SEs are 1.5× group 1's (rural areas are
  noisier), so p = 0.5 exactly; alternatives (power) shift group 2 by 0.3 SD.
- **Cells:** corr {0, 0.4} × reliability {0.9, 0.7} × field {independent, 100 km}: 8 cells; 2,000
  draws each; seed `20261231 + cell`.
- **Acceptance (pre-set):** intervals: 90% coverage ≥ 0.86 in every independent-field cell, per
  procedure; KW: nominal-.10 size in [.07, .13] in independent null cells; B1/B2 also report size
  of the p = 0.5 test. Spatial cells are informational (independence is assumed). Selection: the
  "1" variant if it passes, else the "2" variant, per coefficient.

## 3. Engine

1. `correlation_matrix`: methods `kendall` and `partial` (with `controls`), interval per the
   selected variant (replicate-augmented when selected and replicates exist), `validated` per pair
   and method, notes on the naive estimand and independence. Pearson/Spearman numbers are unchanged
   when the "1" variant is selected; otherwise the interval changes and is documented.
2. `compare_groups(..., method="rank")`: two groups → probability of superiority with the selected
   interval; k ≥ 3 → Kruskal–Wallis test (validated or exploratory per the audit) plus ε².
3. `census/diagnostics.py`: for OLS fits, variance inflation factors, Cook's distance (top five
   areas), Breusch–Pagan and RESET p-values, residual skewness; attached to `fit_model` and
   `compare_groups` outputs as "diagnostics (information only, never a gate)". No manifest change.
4. Docs mirrored (methods text if manifests can request the new methods, protocol, recipe
   `regression_sampling_error` or a new `rank_methods` recipe, MCP text).

## 4. Example (`docs/studies/r33_rank_methods_example.md`)

Exploratory: MI/NY counties, ACS 2018–2022 (the v0.26.0 attachment, ACS columns only): Spearman,
Kendall and partial (controlling for the share aged 65+) correlation of poverty with population;
probability of superiority of nonmetro over metro poverty; diagnostics of the Round 31 ANCOVA.

## 5. Tests, acceptance, commits

Tests: coefficients equal scipy (`spearmanr`, `kendalltau`, partial via residuals); interval
formulas by hand; Brunner–Munzel p̂ and variance equal `scipy.stats.brunnermunzel`'s internals
(statistic and df); flags equal the audit; diagnostics equal statsmodels (`variance_inflation_factor`,
`het_breuschpagan`, `linear_reset`, `OLSInfluence`). Goldens unchanged unless a manifest path
changes (then only additive). Full suite, STATUS, CHANGELOG, version 0.30.0. Commits as Round 31.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Criterion commit, targets | `f660e9c` | Pushed before the full run. |
| Correlation / partial / B / KW results | Done | Spearman/Kendall v1, Pearson/partial v2, B1, KW pass; Pearson/partial v1 fail. |
| Engine, diagnostics, tests | Done | validated_correlations (separate function: correlation_matrix and manifests unchanged), rank compare_groups, diagnostics; 8 tests. |
| Example | Done | Uses the Round 31 example frame. |
| Goldens, final suite | | |
| Exceptions | Recorded | Kendall interval form corrected to Fieller-Hartley-Pearson before the freeze; manifest correlation intervals left for a later round (backlog). |
