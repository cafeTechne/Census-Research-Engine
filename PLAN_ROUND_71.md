# Round 71 plan: tract-level spatial inference

**Goal.** Backlog N49. No tract-level spatial interval is validated:
- Round 67 found SCPC under-covers on North Carolina tracts when fields correlate over 100 km (.75 at ρ̄ .05,
  .81 at .10; it holds at 0–20 km);
- HC3 is far worse (.12–.26);
- the spatial error ML slope interval passed on national counties in Round 69 (.908/.881) but was never tried on
  tracts.

Version 0.67.0. Branch `phase71/tract-spatial`. Validation first.

## 1. Candidates (frozen core in `census/tract_spatial_core.py`; SCPC core unchanged)

- **T1:** spatial error ML (spreg `ML_Error`) slope interval, queen contiguity on cartographic tracts.
- **T2:** SCPC with stronger benchmarks, ρ̄ ∈ {.20, .30}. At tract density a 100 km field has a high average
  pairwise correlation, so ρ̄ .05/.10 assumed too little dependence.
- **T3:** SCPC with the benchmark fixed by **distance** rather than average correlation: c̄ is set so that the
  benchmark range is 100 km whatever the tract density. A grid over weaker correlation stays, as in the original.
- **T4:** HC3 (comparison only).

## 2. Validation (`scripts/tract_spatial_validation.py` → `docs/audits/tract_spatial_validation.md`/`.json`)

- **Geometries:**
  - NC 2018 tracts (2,192, Round 67's file);
  - Michigan 2020 tracts, a test state with a different shape (built from cartographic boundaries,
    representative points).
- **Design:** Round 22's linear generator (y = 1 + .5x + error; x and the error are exponential-covariance fields)
  with ranges {0, 20, 50, 100} km, plus one binomial cell at 100 km (trials lognormal, median 3,900).
- **Draws:** 1,000 per cell (T1 is slow: about 5 s per fit at n ≈ 2,000); seeds `[20281201 + cell, draw]`.
- **Pass:** coverage ≥ .86 in every cell of both geometries. A candidate that passes only for ranges ≤ 50 km is
  validated with that stated scope and a note.
- **Interval length** is reported for every candidate. Among passing candidates the engine default is the
  shortest median length.

## 3. Residual-dependence warning (no validation needed; a diagnostic)

`fit_model` (replicate OLS/GLM, SCPC) and `fit_scpc` compute Moran's I of the residuals on a k = 6 nearest-neighbour
graph of representative points. Large tract frames (over 5,000 rows) use a 5,000-row random subsample with a
fixed seed. When the permutation p < .01 and the interval used is not a validated spatial one:
- the result gains `spatial_dependence: {"moran_i": …, "p": …}`;
- a note names the validated spatial route for that geography (county: SCPC; tract: the Round 71 result).

No interval changes. Goldens: the run golden contains no tract fits; check that the county fits in the golden
produce no new note. If one does, record it and update the golden in a separate commit with the reason.

## 4. Engine (only what passes)

- `fit_model(spatial="sem")` and `"scpc_distance"` (if they pass) route to the validated tract procedure. Tract
  GEOIDs (11 digits) get it as the recommended spatial interval; Round 67's exploratory note is updated.
- Manifests: `fit_replicate` `args.spatial_tract` (opt-in), refused for county GEOIDs.
- Rule text mirrored (protocol → generated MCP text; regression recipe; core item 9).
- Tests: flags equal the audit; the warning fires on a simulated spatially correlated frame and not on an
  independent one.

## 5. Example

Replication C's OLS slopes re-estimated with the validated tract interval (descriptive; the registered
replication result does not change). Archive `/tmp/r71_example_outputs.tar.gz`.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Core, script, criterion commit | done | criterion `f947f64` (verified in git); deviation: no binomial cell |
| Results | done | SCPC .20/.30/distance pass every cell; SEM .63–.89 and HC3 fail |
| Warning | done | `census/residual_dependence.py`; `fit_model(spatial_check=)` |
| Engine, tests | done | tract default rho_bar .20; manifest tract benchmarks; SEM tract note; `tests/test_round71.py` (9) |
| Example | done | `docs/audits/r71_tract_example.md` (SCPC 3–6x wider than HC3, all slopes positive) |
| Goldens, final suite | done | goldens byte-identical; 2185 passed, 38 skipped; 2 Round 61 tests updated (rerun clean) |
| Exceptions | recorded | no sem/scpc_distance routes; spatial_scpc reused instead of spatial_tract; see round71_compatibility.md |
