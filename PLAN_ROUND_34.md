# Round 34 plan: ranking areas and comparisons with a reference

**Goal.** County rankings drive public-health decisions and are easily over-read: two counties whose
estimates differ by less than their MOEs cannot be ordered. This round (regime A of
`ROADMAP_STATISTICS.md`):

- **(A)** validates rank intervals and many-versus-reference comparisons under ACS-type error;
- **(B)** ships the passing procedures in `census/ranking.py` and an MCP tool `rank_areas`;
- **(C)** runs one exploratory example (Michigan counties' poverty).

Version 0.31.0. Baseline: 1930 passed, 37 skipped. Ground rules as Round 31 (branch
`phase34/ranking`; validation first; the maintainer agent implements and merges; releases wait).

## 1. Procedures

K areas with estimates x̂ᵢ and standard errors sᵢ (from replicates, or MOE/1.645).

**Rank intervals** (Klein, Wright and Wieczorek 2020, *Annals of Applied Statistics* 14(2)): area i's
rank interval is [1 + #{j: x_j significantly below x_i}, K − #{j: x_j significantly above x_i}],
from two-sided z tests of x̂ᵢ − x̂ⱼ with SE √(sᵢ² + sⱼ²) (independent areas):

| ID | Multiplicity | Guarantee |
| :--- | :--- | :--- |
| R1 | Bonferroni over the K − 1 comparisons of area i | each area's interval covers its true rank |
| R2 | Bonferroni over all K(K − 1)/2 pairs | all intervals cover jointly |
| R3 | parametric bootstrap percentile (draw x̂ ~ N(x̂, s²), 2,000 times) | comparison only |

Ranks are 1 = highest. Ties in true values count as covered if the interval contains any rank the
tied group occupies.

**Many versus a reference** (each area against the state value S = Σ wⱼ xⱼ, which contains the areas'
own errors): dᵢ = x̂ᵢ − Ŝ with covariance from the replicates (or the exact formula from sᵢ and
the weights). **V1** Holm over the K z tests; **V2** simultaneous max-|z| (Monte Carlo from the
joint normal, 20,000 draws, fixed seed) with simultaneous intervals.

## 2. Validation (`scripts/ranking_validation.py` → `docs/audits/ranking_validation.md`/`.json`)

- Areas: K = 145 (MI/NY counties) and K = 40 (a fixed subset). SEs: the per-county pattern of the
  ACS poverty-rate SEs is mimicked by lognormal SEs (log-SD 0.6).
- True values: Normal with spread τ; signal-to-noise τ/median(s) ∈ {0.5, 2}; tie structure: none,
  or half the areas in groups of 5 sharing a true value. Estimates x̂ = x + N(0, s²).
- Reference: weights wᵢ ∝ lognormal population (log-SD 1); global null for V1/V2 FWER: every
  true value equal to the state value; alternative (coverage): the untied true values.
- Cells: K {40, 145} × SNR {0.5, 2} × ties {no, yes}: 8 cells, 2,000 draws; seed `20270107 + cell`.
- **Acceptance (pre-set, nominal 90%):** R1 mean per-area coverage ≥ .86 and every area's coverage
  ≥ .80; R2 joint coverage ≥ .86; R3 informational; V1 and V2 familywise error ≤ .13 under the
  global null; V2 joint coverage of the simultaneous intervals ≥ .86 under the alternative.
  Failures count as non-coverage.

## 3. Engine and tool

1. `census/ranking.py`: `rank_intervals(estimates, se, joint=False, level=.90, labels)`;
   `compare_to_reference(estimates, replicates or se+weights, reference, method="holm"|"simultaneous")`.
   Non-numeric (suppressed) values are excluded and listed, never ranked (WONDER rule).
2. MCP tool `rank_areas` (full profile only; core stays at 16): `input_path`, `variable`,
   `replicates_path` or `se_col`/`moe_col`, `kind` = `"ranks" | "versus_reference"`, `joint`,
   `reference` (`"weighted_mean"` with `weights`, or a number), `higher_is_better`. Guided summary:
   how many areas are distinguishable from the top/bottom; validated vs exploratory.
3. Recipe `rank_areas`; mirrored rule text. No manifest change.

## 4. Example, tests, acceptance

- Example (`docs/studies/r34_ranking_example.md`): Michigan's 83 counties, ACS 2018–2022 poverty
  rate (from the v0.26.0 attachment, ACS columns): individual and joint rank intervals; counties
  that differ from the statewide rate (Holm and simultaneous), the state rate built from the same
  county counts and replicates.
- Tests: rank intervals by hand on a small example; R1 ⊆ … ⊇ R2 nesting; reference covariance
  equals the exact formula and replicate estimate on synthetic data; flags equal the audit;
  suppressed values excluded; MCP tool offline.
- Goldens unchanged; full suite; STATUS, CHANGELOG, version 0.31.0, section 8.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Criterion commit | `6286ad9` | Pushed before the full run. |
| R1 / R2 / R3 / V1 / V2 results | Done | R1, R2, V1, V2 passed; R3 failed (not exposed). |
| Engine, tool, tests | Done | census.ranking, rank_areas (full profile), recipe; 5 tests. |
| Example | Done | Michigan counties; 34 differ from the state rate. |
| Goldens, final suite | | |
| Exceptions | None | |
