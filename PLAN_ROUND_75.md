# Round 75 plan: manifest support for the new methods, tract coordinates, recipes, README

**Goal.** Close the gaps found after Round 74 (owner request, 2026-11-21):
- Rounds 73–74 left three validated methods reachable only from the library or MCP, not from pre-registered
  manifests;
- tract frames without a `Year` column look up the wrong boundary vintage;
- several analysis tools have no recipe.

No new statistics: every method wired here passed its validation already. Version 0.71.0. Branch
`phase75/manifest-methods`.

## 1. Manifest method `multilevel`

- `{"method": "multilevel", "formula": ..., "groups": "county" | ["state", "county"], "args": {...}}`. The
  statistic is `coefficient` (`term`).
- **Two levels** (`groups` a string): `census.multilevel.fit_multilevel` with the manifest's replicates and target.
  `args` may take `target` and `sampling_se` (a manifest variable's SE column). Validated (coverage .89).
- **Three levels** (`groups` = [top, middle]): `census.multilevel3.fit_three_level`, fixed effects validated
  (Round 73).
  - It takes no replicates, `sampling_se` or `target`. The analysis notes that ACS sampling error is not included,
    since the model was validated without it.
  - Variance shares go in the result's diagnostics, with no share intervals (exploratory and slow).
- Validation checks:
  - each group column is a manifest variable or `GEOID`-derived (`state`, `county` from GEOID prefixes: new frame
    columns `state_fips` and `county_fips`, added when a formula or group names them);
  - three-level `groups` has exactly two distinct names;
  - unknown args are refused.
- Methods text; MCP rule text; `get_recipe("preregistered")` lists the method.

## 2. Manifest `"indices"` block

- `"indices": [{"name": "econ_index", "indicators": [...], "method": "loadings" | "pca" | "equal",
  "loadings": {...}, "reverse": [...], "standardize": true}]`.
- Indicators must be ACS manifest variables or derivations, so they have replicates. Context and external
  variables are refused.
- **New run stage** `_build_indices`, after `_derive_replicates`:
  - full-sample means, SDs and weights are fixed;
  - the frame gets the score, plus `_se` / `_method` from the replicate scores (the Round 36/73 construction);
  - replicate rows are appended to the working replicates, so `fit_replicate` refits use replicate index values;
  - `standardize` rescales with the full-sample score mean and SD, fixed in every replicate.
- **Circularity:** an analysis whose outcome is an indicator of an index it uses as a covariate is refused.
- `run.json` records each index's weights, means and SDs.

## 3. Person-years expected counts in manifests

- The derivation `expected_count` gains `person_years: "<external variable>"`. After the external join, expected =
  person_years × Σ_b rate_b × share_b, with the ACS age × sex mix, as in Round 69.
- **Replicate rows** of the derivation are rescaled with each replicate's own band total. If band replicates are
  absent, the derivation's replicate rows are dropped and a note is recorded.
- Validation: `person_years` must name an external variable. No WONDER value with deaths 1–9 is read into it,
  because person-years are population, not counts.

## 4. Tract coordinates (`frame_coordinates`)

- When tract GEOIDs are missing from the chosen boundary vintage and the frame has no `Year`, the engine retries
  the other tract vintage: 2019 for 2010-vintage tracts, 2022 for 2020.
- It uses the retry only when every GEOID is found, and notes the vintage used.
- Otherwise it raises a clear error that names both vintages and asks for a `Year` column.

## 5. Recipes (new)

| Recipe | Covers |
| :--- | :--- |
| `policy_change` | `difference_in_differences` (non-overlapping releases), `interrupted_series` (annual series; 17+ points) |
| `custom_geographies` | `custom_area_mapping`, `aggregate_geographies`, `median_from_distribution`, `apportion_tracts` |
| `dollars` | `adjust_inflation`, `adjust_for_place`, `place_adjust_frame` |
| `spatial_patterns` | `spatial_autocorrelation` (global and LISA), `make_map` / `make_web_map` |
| `cross_release` | `check_variable_concordance`, the crosswalk draft/review tools, `validate_crosswalks` |
| `reporting` | `make_table`, `make_map`, `make_results_bundle`, `generate_codebook` |

- Existing recipes gain `spatial_small_area_estimates` (`small_area`) and `pums_tabulate` (`pums_tests`).
- Each recipe states its tools' validation status as the docstrings and audits give it.

## 6. README

Refresh:
- the recipe list;
- a "what's new since v0.65" paragraph pointing to CHANGELOG;
- the method table rows for manifests;
- check that every claim matches STATUS.

## 7. Tests and acceptance

- **Tests:**
  - `multilevel` two- and three-level manifests validate and run on synthetic frames;
  - an `indices` manifest reproduces `build_index` scores and its replicate SEs equal `build_index` score SEs;
  - the circularity refusal;
  - `person_years` expected counts equal `wonder_reference.expected_counts`;
  - the tract-vintage retry and its error;
  - every new recipe file has numbered steps.
- Goldens byte-identical (no registered manifest uses the new blocks). Full suite.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| `multilevel` method | done | two- and three-level; `state_fips`/`county_fips` |
| `indices` block | done | stage `_build_indices`; matches `build_index` to 1e-10; circularity refusal |
| person-years expected counts | done | stage `_apply_person_years`; equals `expected_counts(person_years=)` |
| tract coordinates | done | 2022 then 2019 retry; clear error |
| recipes | done | six new (25 total); small_area, pums_tests, preregistered updated |
| README | done | release paragraph, recipe table, routing rows, manifest options, tract advisory |
| goldens, suite | done | run golden identical; schema golden: method list only; 2213 passed, 42 skipped |
| exceptions | recorded | see round75_compatibility.md |
