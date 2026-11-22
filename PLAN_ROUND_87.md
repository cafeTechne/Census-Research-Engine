# Round 87 plan: ecologic versus individual-level associations

**Goal.** Backlog N64. Chapter 9 of *Foundations of Epidemiology* warns that ecologic (area-level) associations do
not describe individuals (the ecologic fallacy), and nearly every engine analysis is ecologic. PUMS lets the engine
measure the gap for a given question. It can estimate the same exposure–outcome association:
- within areas (individual level);
- between areas (ecologic);
- and as a contextual effect: the area mean's association beyond the individual's own exposure.

Version 0.83.0. Branch `phase87/ecologic`. Validation first.

## 1. Methods (frozen core `census/ecologic_core.py`)

- **C1: within, between and contextual decomposition on PUMS**, with PUMAs as areas.
  - Linear (and logit for binary outcomes) models with the individual exposure centred on its PUMA mean, plus the
    PUMA mean itself: within = the centred slope; between = the slope on the PUMA mean; contextual = between −
    within.
  - SDR replicate SEs.
- **C2: the ecologic regression of PUMA-aggregated outcome on PUMA-aggregated exposure** (what an ACS-only analysis
  would estimate), compared with C1's within slope.
  - The gap and its interval are the "ecologic bias" for this question.
- **Interpretation rule:** a contextual effect is an area-level association, not proof of an area cause.
  Composition and omitted individual confounders remain.

## 2. Validation (`scripts/ecologic_validation.py`)

- **Population:** Round 32's PUMS generator extended with PUMA-like clusters (30–150 clusters with realistic sizes).
- **Truth:** individual slopes, and contextual effects of 0 and .5 × within, with cluster-level confounding on and
  off.
- **Outcomes:** continuous and binary.
- **Records:** 5,000 and 30,000.
- **Draws:** 1,000 per cell.
- **Pass:** coverage ≥ .86 for within, between, contextual and the C2 − C1 gap in every cell.

## 3. Engine (only what passes)

- **Tool option `pums_regression(..., ecologic_check="<exposure>")`**, or a new tool if the parameters do not fit
  (decided at implementation, with flat parameters for small models).
- **Agent rule (protocol, recipes, MCP):** when a user draws an individual-level conclusion from an area-level
  result, route to the ecologic check, or state the ecologic fallacy explicitly.
- **Recipe:** `pums_tests` section "Area versus individual associations", cross-linked from the reporting and
  regression recipes.

## 4. Example and acceptance

- **Example (exploratory):** MI income-to-poverty ratio and disability.
  - The within-PUMA individual association against the PUMA-level ecologic association and the contextual effect.
  - The same in OH as the replication state.
- STATUS, CHANGELOG, compatibility audit, tests, goldens, suite.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Core, script, criterion | done | `ecologic_core.py`; tag `criterion-r87` |
| Results | done | logit decomposition passes; identity-scale decomposition and ecologic gap fail (exploratory) |
| Engine, tool, recipe | done | `pums_regression(ecologic_check=...)`; `pums_tests` section; protocol rule |
| Example | done | `r87_ecologic_example.md` (MI and OH) |
| Goldens, suite | done | both byte-identical; 2279 passed, 42 skipped |
| Exceptions | listed | `round87_compatibility.md` |
