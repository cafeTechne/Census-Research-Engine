# Round 74 plan: replication suite

**Goal.** Backlog N52. The five published replications (Rounds 66–69) become manifests an agent can rerun through MCP,
plus an engine regression check that the engine still reproduces them. Needs Rounds 72–73: context sources, the
three-level model, the loadings index and expected counts. Version 0.70.0. Branch `phase74/replication-suite`. No
new statistics.

## 1. Replication manifests (`docs/replications/<id>.json`)

| id | Target | Engine route after Rounds 72–73 | Data |
| :--- | :--- | :--- | :--- |
| `chr_segregation` | CHR 2025 county Black/White D (A) | `segregation` method (naive D, CHR's B11002 groups) + `context` `chr_additional` v141 for the comparison | public |
| `state_gini` | Census B19083 (B) | `test_association(kind="inequality")` per state | public |
| `nc_ice` | Mitchell et al. 2022 (C) | derived ICE variables; `fit_replicate` OLS and `spatial_regression` error; the Round 71 tract interval where validated | public |
| `le_variance` | Boing et al. 2020 headline (E) | `multilevel` with three levels | public |
| `monnat_d` | Monnat 2018 Model 4 (D) | `expected_counts`, `build_index(method="loadings")`, `context` cbp/ers, spatial error | **owner's WONDER exports** (local only) |

- Each manifest records the published target, the pre-set rule copied from its Round 66–69 criterion, and the
  original audit's result.
- They are not registered studies: these replications were already registered and reported in Rounds 66–69.
  They are labelled "replication reruns".

## 2. Runner and regression check

- `scripts/run_replications.py [--only id]` runs each manifest and compares its headline with the original audit.
  The tolerances are fixed here:

  | Replication | Tolerance |
  | :--- | :--- |
  | A | exact (max \|diff\| < 1e−6 against CHR) |
  | B | each state's Gini within .0005 of Round 66 |
  | C | each of the 6 slopes within .001 of Round 67 |
  | E | each share within 0.1 point of Round 68 |
  | D | the economic distress coefficient within .05 of Round 69 |

- It writes `docs/audits/replication_suite.md`. A manifest needing absent data (WONDER for D, or a missing CHR
  file) is reported as **skipped**, never failed and never fetched automatically for WONDER.
- **Tests:** offline unit tests check that every manifest validates and that the runner's comparisons work. The
  full run is a live check (`CENSUS_LIVE_TESTS=1`).
- **MCP:** recipe `get_recipe("replications")` lists the manifests and how to rerun one with `run_manifest`. No new
  tool.

## 3. Disagreements

If a rerun differs from its original audit beyond tolerance, the round does **not** change the earlier result:
- the difference is reported with its cause (engine route versus hand script);
- the engine route is fixed if it is wrong;
- a mismatch that remains is a reportable exception in the compatibility audit.

## 4. Docs and acceptance

- README "Replications" section (what was replicated, outcomes, how to rerun); STATUS; CHANGELOG; version;
  compatibility audit.
- Goldens byte-identical; full suite; the runner's live report is attached to the PR description.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Manifests | | |
| Runner and tolerances | | |
| Live run report | | |
| Docs, tests | | |
| Goldens, final suite | | |
| Exceptions | | |
