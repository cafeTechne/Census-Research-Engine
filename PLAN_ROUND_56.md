# Round 56 plan: microdata inequality measures with replicate-weight variance

**Goal.** Backlog issue N27 (`ROADMAP_BACKLOG.md` Round 56; STATUS backlog 6, "microdata inequality measures").

The engine has area-level inequality measures (SII, RII, concentration, Round 24) but no person- or
household-level income inequality from PUMS. This round adds the standard measures with the SDR replicate
variance, validated the way Round 49 validated the PUMS models: resampling a synthetic population with the PUMS
design.

The measures are:
- Gini;
- Theil T;
- Atkinson with ε = .5 and ε = 1;
- the log P90/P10 and log P80/P20 ratios;
- the top-decile income share;
- the difference in Gini between two groups.

Version 0.53.0. Baseline: the Round 55 suite (2094 passed, 37 skipped). Branch `phase56/pums-inequality`.
Validation first.

## 1. Frozen core (`census/pums_inequality_core.py`)

For an income vector y and a weight matrix W (n × 81: the full weight and 80 SDR replicates), sort once by y.
Then, for every weight column:
- weighted shares p_i, mean μ, and the Lorenz curve L_i = Σ_{j ≤ i} p_j y_j/μ;
- **Gini** 1 − Σ p_i (L_i + L_{i−1});
- **Theil T** Σ p_i (y_i/μ) ln(y_i/μ);
- **Atkinson** 1 − (Σ p_i (y_i/μ)^{1−ε})^{1/(1−ε)}, and for ε = 1, 1 − exp(Σ p_i ln y_i)/μ;
- **quantiles** by the inverse weighted ECDF (smallest y with cumulative share ≥ q);
- **top-decile share** 1 − L(.9), with L linearly interpolated in the cumulative population share.

SE = √(4/80 Σ(θ_r − θ)²), normal 90% interval. The group difference uses per-replicate differences. Theil,
Atkinson and the quantile ratios need positive incomes; Gini and the top share allow zeros. Negative incomes
are refused.

## 2. Validation (`scripts/pums_inequality_validation.py` → `docs/audits/pums_inequality_validation.md`/`.json`)

**Generator.** Round 32's, unchanged (`scripts/pums_tests_validation.py`: unequal-probability household sample
along a geography, household-correlated person attributes, SDR replicate weights built as the ACS builds them).
Same 8 cells: ρ ∈ {.1, .4} × weight CV ∈ {.3, 1.0} × m ∈ {800, 3000} households. 2,000 draws per cell; seed
`20280201 + cell`.

**Incomes**, from the generator's person income y₁ (lognormal; it depends on A and geography):
- **I1** = y₁;
- **I2** = y₁^1.6 (heavier tail; log SD about 1);
- **I3** = y₁ with zeros where the generator's binary attribute D is true (about 30% of persons; P(N(0,1) > .5244)).

**Targets.** Population values from a reference population of 2,000,000 households (seed `[20280201, 2000000]`,
ρ = .25; marginal distributions do not depend on ρ, weights or m), computed with the same core at unit
weights and committed before the run (`docs/audits/pums_inequality_targets.json`).

**Judged (17).**
- I1 and I2: Gini, Theil T, Atkinson .5 and 1, log P90/P10, log P80/P20, top-decile share.
- I3: Gini and top-decile share.
- I1: Gini(A = 2) − Gini(A = 0).

**Acceptance.** Per measure and income: coverage ≥ .86 in every cell. Failed draws count as non-coverage. A
measure is validated when it passes on every income on which it is judged.

## 3. Engine (only what passes)

- New `census/pums_inequality.py`: `pums_inequality(df, var, weight="person", where=None, by=None, groups=None)`
  returns each measure with its SDR interval and a `validated` flag, and the Gini difference when two groups are
  given. Zero incomes are excluded from Theil, Atkinson and the ratios, with a note; negative incomes are refused.
- MCP: `test_association(kind="inequality", var=..., by=...)`, so there is no new tool and the tool counts stay
  unchanged. Rule text in the PUMS recipe, agent protocol and MCP text.
- STATUS, CHANGELOG, version, compatibility audit; tests (flags = audit; core formulas checked by hand on small
  inputs); goldens identical.
- **Exploratory example:** household income inequality (HINCP, housing weights) in the cached Michigan PUMS
  extract if present, overall and by disability of the reference person; otherwise person earnings.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Core, targets, script, criterion commit | | |
| Results | | |
| Engine, MCP, tests | | |
| Example | | |
| Goldens, final suite | | |
| Exceptions | | |
