# Round 73 plan: three-level models, loading-weighted indices, indirect standardization

**Goal.** Backlog N51. Three methods the replications needed and built by hand. Version 0.69.0. Branch
`phase73/methods`. Validation first for the two that produce intervals.

## 1. Three-level multilevel models (was N46)

**Method.** `fit_multilevel(..., groups=["state", "county"])`: nested random intercepts (tract in county in state)
via statsmodels `MixedLM` (groups = top level, variance component = middle level). It returns:
- fixed effects;
- the three variances and their shares;
- intervals.

**Interval candidates** (frozen core `census/multilevel3_core.py`):
- **M1:** fixed-effect Wald interval with Satterthwaite-type df from the top-level count (fixed slopes).
- **M2:** parametric bootstrap percentile intervals for the variance shares (199 resamples).
- **M3:** cluster (top-level) bootstrap percentile intervals for the shares.

**Validation** (`scripts/multilevel3_validation.py`):
- nested designs with 30 and 49 top-level units, 20–60 middle units each, 10–30 bottom units each;
- true shares (.70, .11, .19), Round 68's estimates, and (.50, .25, .25);
- a fixed covariate at the bottom level;
- 1,000 draws per cell;
- **pass:** ≥ .86 in every cell, per procedure.

**MCP:** `multilevel_model(groups=[…])`. **Manifests:** `multilevel` gains a groups list.

## 2. Loading-weighted indices

**Method.** `build_index(method="loadings", loadings={"var": w, …})`: a published factor-weighted index (e.g.
Monnat's distress index):
- each component standardized across the frame, then weighted and summed, then optionally standardized;
- per-area replicate intervals as in Round 36, with the loadings held fixed (they are published constants).

**Validation:**
- Round 36's per-area score coverage design with fixed loadings (.9, .8, .6, .5) and reliabilities .7/.9;
- 2,000 draws;
- **pass:** ≥ .86 mean per-area coverage in every cell, with ≥ 90% of areas ≥ .80 (Round 36's rule).

## 3. Indirect standardization helper (no new inference)

`expected_counts(frame, reference, population_table="B01001", person_years=None)`:
- **reference:** a national age × sex rate table, e.g. the WONDER national file parsed by the existing reader;
- it maps WONDER's ten-year bands to the ACS B01001 age lines, pooling WONDER "< 1" and "1–4" into ACS "Under 5"
  with population weights, as Round 69 did by hand;
- `person_years` optionally rescales to a WONDER county person-years column, so the ACS gives the age × sex mix
  only;
- the output feeds the existing `indirect_standardize` and SMR code. No new interval: SMR intervals keep their
  validated Round 24/55 routes.

**Check:** Round 69's expected deaths are reproduced exactly from the same cached inputs, a numeric equality test.
The WONDER rule holds: no hidden 1–9 count is used or output.

## 4. Docs and acceptance

- Recipes (small_area for three-level models, composite_index for loadings, health_inequality for expected
  counts); protocol text generated into MCP; STATUS, CHANGELOG, version, compatibility audit; tests (flags =
  audit).
- **Example:** Replication E rerun through `multilevel_model(groups=…)` with share intervals (descriptive).
- Goldens byte-identical; full suite.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Cores, scripts, criterion commit | done | criterion `e97e9fc` (tag `criterion-r73`); M2 dropped before the run |
| Three-level results | done | M1 passed .904–.913; M3 screening .88–.98 (exploratory) |
| Loadings-index results | done | LI passed: mean .897–.899, every area ≥ .878 |
| Expected-counts helper | done | reproduces Round 69 expected deaths (max rel. diff 7.8e-16) |
| Engine, tests, example | done | `multilevel_model(groups=[...])`, `build_index(method="loadings")`; `tests/test_round73.py` (8); `r73_three_level_example.md` |
| Goldens, final suite | done | goldens byte-identical; 2195 passed, 38 skipped |
| Exceptions | recorded | M2 dropped; M3 screening; person-years library-only; share_intervals added (round73_compatibility.md) |
