# Round 68 plan: replication E (tract, county and state shares of life-expectancy variation)

**Goal.** Replication target E, chosen by the owner on 2026-11-20 as a headline-only replication: the paper is not
open access, so only its published summary numbers are used. Version 0.64.0. Branch `phase68/le-variance`.

## Target

Boing, Boing, Cordes, Kim and Subramanian (2020), *PNAS* 117(30):17688–17694. From the published abstract and the
Harvard press release:
- 65,662 tracts in 3,020 counties in 48 states plus DC;
- of the total geographic variation in life expectancy at birth, 70.4% lies between tracts (within counties),
  10.7% between counties (within states) and 19.0% between states.

**Assumptions, because the methods section could not be read:**
- the data are USALEEP 2010–2015 (its coverage, 48 states plus DC without Maine and Wisconsin, matches the
  paper's);
- the model is a three-level random-intercept null model of e(0) in years.

The report states these assumptions.

## Specification

- USALEEP A files for every covered state and NYC; every tract with an `e(0)`, including fully predicted tracts.
- Tract within county (GEOID[:5]) within state (GEOID[:2]).
- REML mixed model, e(0) = μ + u_state + v_county + e_tract (statsmodels `MixedLM`: groups = state, variance
  component = county).
- Shares = each variance over their sum.
- The engine's `multilevel_model` is two-level only, so this round uses statsmodels directly and records the gap
  (N46).

## Rule (fixed before the fit)

- **Replicated** if each share is within ±5 percentage points of the published value **and** the order is tract >
  state > county.
- **Partly replicated** if the order holds but a share is off by more than 5 points.
- **Not replicated** otherwise.
- The tract and county counts are reported against 65,662 and 3,020.
- **Secondary (descriptive):** the same shares for ln(e0), and for 2-level models (tract in county; tract in
  state).

## Simulation

None. The shares are point decompositions, and no engine interval is used or validated. The planned three-level
coverage study waits until the engine has a three-level method (N46).

## Docs

Report `docs/studies/r68_replication_le_variance.md`; STATUS, CHANGELOG, version, compatibility audit; tests;
goldens byte-identical.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Data and criterion | | |
| Fit and result | | |
| Report, tests | | |
| Goldens, final suite | | |
| Exceptions | | |
