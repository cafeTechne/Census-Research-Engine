# Round 79 plan: Oaxaca–Blinder and Fairlie decompositions on PUMS

**Goal.** Backlog N56. How much of a group gap is explained by composition, and how much remains? Examples are
uninsured rates by race/ethnicity and earnings by sex or disability. The standard tools are the Oaxaca–Blinder
decomposition (linear outcomes) and Fairlie (2005) (binary outcomes). Survey-correct SEs come from the 80 PUMS
replicate weights (SDR), as in Rounds 32/49. Version 0.75.0. Branch `phase79/decomposition`. Validation first.

## 1. Methods (frozen core `census/decomposition_core.py`)

- **O1: Oaxaca–Blinder.**
  - Twofold with the pooled reference (Neumark 1988; Jann 2008); also threefold (endowments, coefficients,
    interaction).
  - Detailed contributions per covariate, with categorical covariates normalised (Yun 2005) so that results do not
    depend on the omitted category.
- **F1: Fairlie** nonlinear decomposition for logit/probit outcomes.
  - A pooled-sample model, randomised matching order with 100 orderings, and the mean over orderings.
- **Interval:** SDR replicate-weight variance: refit on each of the 80 replicate weights, with 4/80 Σ(θ_r − θ)².
  The comparison interval uses design-blind model SEs, reported as exploratory only.
- **Groups:** two mutually exclusive groups defined by PUMS codes, using Round 76's group-definition helper.

## 2. Validation (`scripts/decomposition_validation.py`)

- **Population:** a synthetic finite population of PUMA-like clusters with known coefficients, sampled with the
  ACS-like design and replicate weights from Rounds 32/49.
- **Cells:** group sizes 300, 1,000 and 5,000; 3 and 8 covariates; one categorical with 5 levels; true explained
  shares .2 and .6.
- **Pass:** coverage of the total explained part, the unexplained part and each detailed contribution is ≥ .86 in
  every cell. Detailed contributions with small groups may fail; they are then gated by group size, as with the
  PUMS 30-record flag.
- **Draws:** 1,000 per cell.

## 3. Engine (only what passes)

- **Tool:** `test_association(kind="decomposition", outcome=..., by=..., covariates=[...], model="linear"|"logit")`
  in the full profile, or a new `decompose_gap` tool if the parameters do not fit `test_association` (decided at
  implementation; flat parameters for small models).
- **Recipe:** `pums_tests` gets a "decomposing a gap" section with the interpretation rule: "explained" is
  statistical composition, not a causal effect.

## 4. Example and acceptance

- **Example (exploratory):** the Michigan uninsured gap between Black and White adults aged 19–64, explained by
  age, income-to-poverty, employment and education (PUMS 2019–2023).
- STATUS, CHANGELOG, compatibility audit, tests, goldens, suite.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Core, script, criterion | done | `decomposition_core.py`, `decomposition_validation.py`; criterion `9e52bb4` (tag `criterion-r79`) |
| Results | done | O1 totals from 300 records; O1 detailed and F1 from 1,000 |
| Engine, tool, recipe | done | `census/decomposition.py`; tool `decompose_gap` (74 tools); `pums_tests` section |
| Example | done | `r79_decomposition_example.md`: MI uninsured gap 2.54 points, explained 2.73 (Fairlie) |
| Goldens, suite | done | both goldens byte-identical; 2239 passed, 42 skipped |
| Exceptions | listed | `round79_compatibility.md` |
