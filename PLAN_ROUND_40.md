# Round 40 plan: beta and median regression for area data

**Goal.** Most ACS outcomes are shares in (0, 1), and many are skewed. Linear models can predict
outside (0, 1) and are driven by outliers. This round validates two families (regime A of
`ROADMAP_STATISTICS.md`):

- **beta regression** (logit mean, constant precision; statsmodels `BetaModel`) for shares;
- **median regression** (statsmodels `QuantReg`, q = 0.5) for skewed outcomes;

and ships them as `fit_model(model="beta" | "median")`. Version 0.37.0. Baseline: 1963 passed, 37
skipped. Ground rules as Round 31 (branch `phase40/beta-median`; validation first; the maintainer
agent implements and merges; releases wait).

**Deferred (backlog):** ordinal and multinomial logit and weighted quantile regression for PUMS
(statsmodels' `OrderedModel`, `MNLogit` and `QuantReg` take no survey weights; they need weighted
estimating equations first), GEE for tracts within counties, and penalised splines.

## 1. Procedures (naive target: the coefficient on the ACS estimates as observed)

| ID | Model | Interval (90%) |
| :--- | :--- | :--- |
| B1 | beta regression, ML | model-based SE (inverse Hessian) |
| B2 | beta regression, ML | sandwich (HC0) SE |
| B3 | beta regression, ML | B2 plus the ACS replicate variance (80 refits) |
| Q1 | median regression | statsmodels' kernel (Hall–Sheather) SE |
| Q2 | median regression | Q1 plus the ACS replicate variance (80 refits) |

## 2. Validation (`scripts/beta_median_validation.py` → `docs/audits/beta_median_validation.md`/`.json`)

- 145 MI/NY counties, independent areas. True covariate x (Gaussian) observed with error at
  reliability 0.9 or 0.7 (lognormal per-area SEs, replicates).
- Beta cells: true share μ = expit(−1.5 + 0.4x), outcome ~ Beta(μφ, (1 − μ)φ) with φ = 30, observed
  with sampling error SE = c·√(μ(1 − μ)) with c ∈ {0.02, 0.05} (clipped to [0.001, 0.999]); replicates.
- Median cells: y = 1 + 0.5x + skewed noise (centred lognormal, σ = 0.8), observed with sampling
  error (reliability 0.9 of y's variance) and replicates.
- Targets: each procedure family's slope on the observed covariate from a 400,000-area reference per
  cell (computed before freezing).
- Cells: beta 4 (reliability × c), median 2 (reliability); 1,000 draws (replicate refits are costly);
  seed `20270218 + cell`.
- **Acceptance:** 90% coverage ≥ .86 in every cell of the family; selection: the first passing of
  B1, B2, B3 and of Q1, Q2.

## 3. Engine, example, tests

`census/regression_families.py`: `fit_beta(formula, frame, replicates)` and `fit_median(...)` with the
selected interval and validated flags; MCP `fit_model(model="beta"|"median")`. Recipe update; mirrored
rule text. Example: MI/NY county poverty share (beta) and median household income (median
regression) on the share aged 65+ and metro class (Round 31 frame / R21b measures). Tests against
statsmodels; flags against the audit. Goldens unchanged; full suite; STATUS, CHANGELOG, version 0.37.0.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Criterion commit, targets | `d5c9b02` | Pushed before the full run. |
| B1–B3 / Q1–Q2 results | Done | B2 and Q1 selected; B1 failed. |
| Engine, tests | Done | regression_families; MCP routing; 4 tests. |
| Example | Done | Poverty models compared. |
| Goldens, final suite | | |
| Exceptions | None | |
