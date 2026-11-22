# Round 73 criterion: three-level models and fixed-loading indices

Committed before the full run. Author self-review, not independent. Frozen with `validate_pins`:
- `scripts/methods73_validation.py`;
- `census/multilevel3_core.py` and `census/loadings_index_core.py` (new);
- `census/index_core.py`, `census/simulation.py` and Round 36's `scripts/index_validation.py` (unchanged);
- this file.

**Seen before this commit:**
- one smoke run (2/1/3 draws), which only checked that the script runs;
- timing probes of a three-level fit: 1.1–3.6 s at 6,000–9,800 rows.

## ML: three-level random-intercept models (backlog N51, was N46)

- **Design:** G_top ∈ {30, 49} top units, each with 10–30 middle units, each with 5–15 bottom units (unbalanced;
  drawn once per cell). True variance shares (bottom, middle, top) ∈ {(.70, .11, .19) (Round 68's published split),
  (.50, .25, .25)}, total variance 1. A bottom-level covariate x ~ N(0, 1) has slope .5. Four cells.
- **M1:** REML (statsmodels MixedLM), Wald interval for the slope with t(G_top − 1).
  - 1,000 draws per cell. **Pass: coverage ≥ .86 in every cell.**
- **M3:** variance-share intervals from a delete-one-top-unit jackknife on the logit scale.
  - **Screening only:** 100 draws per cell (each draw needs G_top refits). It is reported but stays exploratory
    whatever the result; a pass would justify a full validation later.
- **M2 (parametric bootstrap) dropped from the plan before any run.** 199 refits per draw are infeasible at 1–3.5 s
  per fit. A probe showed MixedLM's covariance of the variance parameters is NaN for the top level, so a
  delta-method interval is not available either.

## LI: indices with fixed published loadings

- Round 36's design: MI/NY geometry, five indicators, reliability {.9, .7} × field range {0, 100} km, correlated
  ACS-like errors, 80 replicates. The fixed loadings (.9, .8, .6, .5, .7) replace estimated weights.
- 2,000 draws per cell.
- **Pass (Round 36's S1 rule):** mean per-area 90% coverage ≥ .86 **and** every area ≥ .80, in every cell.

Seeds: ML `[20281301 + cell, draw]`; LI `[20281311 + cell, draw]`. Failed fits count as non-coverage.

## Engine (only what passes)

- **M1 passes:** `multilevel_model(groups=["state", "county"])` (three levels) reports validated fixed-effect
  intervals. Share intervals are reported as exploratory.
- **LI passes:** `build_index(method="loadings", loadings={...})` gives validated per-area intervals.
- **The expected-counts helper has no interval and needs no validation.** Its check is numeric: Round 69's
  expected-deaths construction is reproduced exactly.
