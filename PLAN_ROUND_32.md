# Round 32 plan: design-based tests for PUMS microdata

**Goal.** Add survey-correct tests to the PUMS path (regime B of `ROADMAP_STATISTICS.md`).
`census.pums` already estimates counts, means, proportions, medians, crosstabs and regressions
with successive-difference replication (SDR: 80 replicate weights, Var = 4/80 Σ(θᵣ − θ)²). It has
no tests of association, no odds or risk ratios, and only Wald intervals for proportions. This
round:

- **(A)** validates design-based tests and intervals on a synthetic survey with household
  clustering, unequal weights and SDR replicate weights built the way the ACS builds them;
- **(B)** ships the passing procedures in `census/pums_tests.py` and an MCP tool `test_association`;
- **(C)** runs one exploratory example on real MI PUMS.

Version 0.29.0 (Round 31 is 0.28.0). Baseline suite: 1908 passed, 37 skipped.

**Non-goals.** No area-level rank tests (Round 33). No weighted quantile regression (Round 40).
No Woodruff quantile intervals this round (medians keep the SDR SE; Woodruff is a later option).

## 0. Ground rules

As Round 31 (branch `phase32/pums-tests`, worktree `/tmp/census-round32`; validation first with
the criterion committed and pushed before the full run; smoke runs ≤ 20 draws write no files;
`[skip ci]`; no attribution; no WONDER). Owner standing instruction (2026-11-18): the maintainer
agent implements, self-reviews and merges; releases wait for the owner.

## 1. Procedures

Notation: n unweighted persons, w the full weight, w⁽ʳ⁾ the 80 replicate weights, θ an estimate
and Vᵣ = 4/80 Σᵣ(θᵣ − θ)(θᵣ − θ)ᵀ its SDR covariance.

**Independence in an r × c table** (q = (r − 1)(c − 1)): weighted cell shares pᵢⱼ;
θ = the q interaction contrasts pᵢⱼ − pᵢ.p.ⱼ (i < r, j < c); V₀ their covariance under simple
random sampling of n at independence (multinomial, delta method); δₖ the eigenvalues of
V₀⁻¹Vᵣ (design effects).

| ID | Statistic | Reference |
| :--- | :--- | :--- |
| T0 | Pearson X² from weighted shares and n (ignores the design) | χ²(q); comparison only |
| T1 | first-order Rao–Scott X²/δ̄ | χ²(q) |
| T2 | second-order Rao–Scott X²/(δ̄(1 + a²)), a² = Σ(δₖ − δ̄)²/(q δ̄²) | χ²(q/(1 + a²)) |
| T3 | design Wald W = θᵀVᵣ⁻¹θ, F = (80 − q + 1)/(80 q)·W | F(q, 80 − q + 1) |

**k-group means** (domains of a categorical variable; q = k − 1): differences from the first
group with their joint SDR covariance; T3's F form (named **M3**) and, for k = 2, the z test
(**M1**) and t(80) (**M2**).

**Intervals** (90%, normal unless stated):

| ID | Quantity | Interval |
| :--- | :--- | :--- |
| I1 | difference of two domain proportions | θ ± z·SDR SE |
| I2 | log odds ratio of a 2 × 2 table | log θ ± z·SDR SE, exponentiated |
| I3 | log relative risk | as I2 |
| I4 | difference of two domain means | θ ± z·SDR SE |
| I5 | difference of two domain medians (existing weighted median) | θ ± z·SDR SE |
| P1 | one proportion, Wald (existing) | p ± z·SDR SE, clipped to [0, 1] |
| P2 | one proportion, Korn–Graubard | Clopper–Pearson at the effective n* = p(1 − p)/SE², df-adjusted with 80 replicate df; n* capped at n |

## 2. Validation (`scripts/pums_tests_validation.py` → `docs/audits/pums_tests_validation.md`/`.json`)

- **SDR factors:** a Hadamard matrix of order 80 (Paley construction, q = 79), as the ACS uses.
  Sampled households are sorted by a geography coordinate; household k in that order gets rows
  (k mod 80, (k + 1) mod 80) and factor fᵣ = 1 + 2^(−3/2)·(H[row₁, r] − H[row₂, r]); persons inherit
  their household's replicate weights. A test checks the Hadamard property and the factor formula.
- **Sample generator (each draw generates the sample directly from a superpopulation):**
  - geography coordinate g ~ U(0, 1) for every population household; selection probability
    π ∝ exp(σ_w·z(g)) with a smooth field z, so weights 1/π vary with geography (weight CV set by
    σ_w); household size 1 + Poisson(1.5);
  - person attributes share a household effect with intra-class correlation ρ, plus a smooth
    trend in g: categorical A (3 levels) and B (4 levels) from independent latent variables
    (so A ⟂ B in the population: the null for every independence test), a binary C, and income
    y = exp(10.5 + 0.6·latent) (lognormal);
  - the expected sample has m households; the population size is large enough (N = 50·m) that
    finite-population corrections are negligible and not applied (as the ACS does not).
- **Targets for intervals:** computed before the full run from one reference population of
  2,000,000 households from the same generator (unweighted population values), committed with the
  criterion (like Round 30's β*).
- **Alternatives for intervals and power:** I1–I5 use non-null contrasts (C's prevalence and y's
  mean depend on A; the A × B independence null is kept for T0–T3).
- **Cells:** ρ ∈ {0.1, 0.4} × weight CV ∈ {0.3, 1.0} × m ∈ {800, 3,000} households: 8 cells,
  2,000 draws each. Seed `20261225 + cell`; nested in that order.
- **Statistics per draw:** independence 2 × 2 (A collapsed to 2 levels × C; q = 1) and 3 × 4
  (A × B; q = 6); k = 3 means of y by A (M3) and the two-group version (M1, M2); I1–I5 for A's
  first two levels; P1/P2 for a rare proportion (prevalence 0.03) within a small domain (one A
  level and m/8 households on average).
- **Acceptance (pre-set):**
  - tests: nominal-.10 size within [.07, .13] in every cell, per procedure and table/design;
  - intervals: 90% coverage ≥ 0.86 in every cell, per procedure;
  - selection: for independence, the simplest passing of T1, T2, T3 (in that order) per table size;
    for k means, M3 if it passes; for two groups, M1 then M2;
  - a procedure whose computation fails (singular Vᵣ, undefined ratio) counts as a rejection or
    a non-coverage; failure counts are reported.
- **Informational:** T0's size (expected to be far above .10), power, mean δ̄ and a², interval widths.

## 3. Engine (`census/pums_tests.py`, built on `census.pums` internals)

1. `independence_test(df, row, col, weight="person", where=None)`: the selected procedure plus the
   others as labelled diagnostics; returns the table of weighted shares with SDR SEs, q, δ̄, a²,
   statistic, df, p, `validated`, notes (minimum expected count, flagged cells).
2. `two_by_two(df, exposure, outcome, ...)`: difference of proportions, odds ratio and relative risk
   with intervals; refuses empty cells (no continuity correction).
3. `compare_means(df, var, by, ...)` and `compare_medians(df, var, by, ...)` (two groups for
   medians): domain estimates, differences with intervals, the omnibus test for k ≥ 3.
4. `proportion_interval(df, var, where, method="korn_graubard" | "wald")`: the validated default.
5. Small-sample flags reuse `census.pums` (fewer than 30 records, CV above 30%): flagged, not
   suppressed. Validation status from the audit flags (fixed constants, tested against the audit).
6. **MCP tool `test_association`** (full and core; core cap 16): `state`, `year`, `kind` =
   `"independence" | "two_by_two" | "means" | "medians" | "proportion"`, `row`/`col` or `var`/`by`,
   `where`, `weight`, `product`. Guided summary and next step; validated vs exploratory stated.
   Recipe `pums_tests`. Rule text mirrored in `docs/agent_protocol.md`, the MCP instructions and
   the core profile text.

## 4. Exploratory example (`docs/studies/r32_pums_tests_example.md`)

Exploratory; author self-review, not independent. Michigan 2018–2022 5-year PUMS (download through
`census.pums.fetch_pums`; public file, no key):
- disability (DIS) × health insurance type (private only / public only / both / none), adults 19–64;
- poverty (POVPIP < 100) by disability: difference, odds ratio and relative risk;
- personal earnings by disability (means and medians), adults 25–64 with earnings;
- the share uninsured among disabled adults in one small PUMA (Korn–Graubard vs Wald).
Archive `r32_example_outputs.tar.gz` (results only, no microdata; key-scanned).

## 5. Tests (`tests/test_round32.py`)

Hadamard and SDR factor checks; Pearson X² equals `scipy.stats.chi2_contingency` (no correction)
on unweighted data with unit weights; δ's equal 1 when replicate covariance equals the SRS
covariance (constructed case); Rao–Scott and Wald statistics against hand computations; OR/RR and
their SEs against hand computations; Korn–Graubard equals Clopper–Pearson when n* = n and
df = ∞-equivalent; refusals (empty cell, single category, too few records); flags match the
audit; MCP tool success and failure paths offline (fixture data).

## 6. Acceptance

Goldens unchanged (no manifest change expected); full suite baseline + new tests, 0 failures;
STATUS validation rows, roadmap status, studies table; CHANGELOG; version 0.29.0; section 8.

## 7. Commits

1. Script, criterion and reference targets (pushed before the full run). 2. Full run and audit.
3. Engine, tool and tests. 4. Example. 5. Docs, STATUS, version, CHANGELOG, section 8.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Criterion commit, targets | `d65d034` | Pushed before the full run. |
| T / M / I / P results | Done | T1 (and T2) passed; T3 failed 3x4; M1/M2/M3, I1–I5, P2 passed; P1 failed. |
| Engine, tool, tests | Done | `pums_inference`, `test_association` (core), recipe; 14 tests. |
| Example | Done | MI 2019–2023 PUMS (single PUMA vintage); medians of heaped earnings flagged. |
| Goldens, final suite | Done | Goldens identical; 1922 passed, 37 skipped, 0 failures. |
| Exceptions | Recorded | Example uses 2019–2023 (2018–2022 splits PUMA vintages); heaping guard added after the example. |
