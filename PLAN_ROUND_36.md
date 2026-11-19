# Round 36 plan: composite indices, internal consistency and typologies

**Goal.** Public-health work often summarises several ACS measures in one deprivation index, then
reports quintiles. The engine has no index builder, and an index of noisy estimates is itself
noisy. This round (regime A of `ROADMAP_STATISTICS.md`):

- **(A)** validates per-area index-score intervals and internal-consistency (Cronbach's α) intervals
  under ACS-type error;
- **(B)** ships `census/composite_index.py` and an MCP tool `build_index` (full profile): first
  principal component or equal weights, fixed full-sample standardisation and loadings, replicate
  SEs, quintiles with their stability, α, and an optional typology with replicate stability;
- **(C)** runs one exploratory MI/NY county index (Round 21b's ACS deprivation measures).

Version 0.33.0. Baseline: 1940 passed, 37 skipped. Ground rules as Round 31 (branch
`phase36/composite-index`; validation first; the maintainer agent implements and merges; releases wait).

## 1. Procedures

Indicators x₁…x_k per area, oriented so higher = more deprived; full-sample means m and SDs s;
z = (x − m)/s; loadings l: the first principal component of corr(z) (sign: positive sum) or equal
weights 1/√k. Score = z·l. Everything (m, s, l) is fixed at its full-sample value in every replicate.

| ID | Quantity | Interval |
| :--- | :--- | :--- |
| S1 | an area's score | score ± z·SE, SE from the 80 replicate scores (fixed m, s, l) |
| A1 | Cronbach's α of the k standardised indicators | Feldt: (1 − α)/(1 − α̂) ~ F(n − 1, (n − 1)(k − 1)) |
| A2 | α | A1 on the log(1 − α) scale with the replicate variance of log(1 − α̂) added |

Informational: the probability that an area stays in its quintile across replicates; the adjusted
Rand index between the full-sample k-means typology and the replicate typologies.

## 2. Validation (`scripts/index_validation.py` → `docs/audits/index_validation.md`/`.json`)

- 145 MI/NY counties (Round 30 coordinates); independent or spatial (100 km) fields.
- A latent deprivation field f; five indicators xⱼ = λⱼ f + √(1 − λⱼ²) εⱼ with λ = (.8, .7, .6, .7, .5);
  observed = true + error with per-area lognormal SEs at reliability 0.9 or 0.7; replicates from
  `census.simulation.make_replicates` (cross-correlation 0.2).
- **Targets:** S1: each area's score computed from its *true* indicators with the same m, s and l
  (the index the area would get without sampling error); α: the population α of the observed
  indicators, from a 400,000-area reference sample per cell.
- Cells: reliability {0.9, 0.7} × field {independent, 100 km} × weights {PCA, equal}: 8 cells;
  2,000 draws; seed `20270121 + cell`.
- **Acceptance (pre-set):** S1: mean per-area 90% coverage ≥ .86 and every area ≥ .80, per weighting;
  A1/A2: 90% coverage ≥ .86 in every independent cell (spatial cells informational). Selection:
  A1 if it passes, else A2.

## 3. Engine and tool

`build_index(frame, indicators, replicates=None, method="pca"|"equal", reverse=(), outcome=None,
typology_k=None)`: refuses an `outcome` that is also an indicator (circularity) and fewer than three
indicators; returns scores with intervals (validated with replicates; exploratory without),
loadings and explained variance, α with the selected interval, quintiles with stability, and the
typology with its stability (descriptive). MCP `build_index(input_path, indicators, replicates_path,
...)` in the full profile; recipe `composite_index`; mirrored rule text.

## 4. Example, tests, acceptance

Example: an MI/NY county deprivation index from Round 21b's ACS measures (poverty, no bachelor's
degree, no vehicle, housing cost burden), cached inputs; scores, quintile stability, α and a
4-group typology. Tests: PCA loadings against `numpy.linalg.eigh`; α against the formula; Feldt
interval by hand; score SEs by hand; circularity refusal; tool offline. Goldens unchanged; full
suite; STATUS, CHANGELOG, version 0.33.0, section 8.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Criterion commit, targets | `e86907d` | Pushed before the full run. |
| S1 / A1 / A2 results | Passed | S1 both weights; A1 selected; α under-covers with spatial dependence. |
| Engine, tool, tests | Done | build_index library and MCP tool; 6 tests. |
| Example | Done | Construct-validity warning (NYC); α 0.40. |
| Goldens, final suite | | |
| Exceptions | None | |
