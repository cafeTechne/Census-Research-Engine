# Replications: rerun the published replications

Goal: rerun one of the five published findings the engine replicated in Rounds 66–69, and check that the current
engine still reproduces its original audit (Round 74). These are **replication reruns**, not new registered studies.
The registered results stay those of Rounds 66–69.

1. Pick a spec in `docs/replications/`:

   | id | Finding | Data |
   | :--- | :--- | :--- |
   | `chr_segregation` | CHR 2025 county Black/White dissimilarity (A) | public |
   | `state_gini` | Census B19083 state Gini from PUMS (B) | public |
   | `nc_ice` | Mitchell et al. 2022, NC tract life expectancy and ICE (C) | public |
   | `le_variance` | Boing et al. 2020, tract/county/state shares of life-expectancy variation (E) | public |
   | `monnat_d` | Monnat 2018 Model 4, county drug-related mortality and economic distress (D) | the owner's WONDER exports |

2. Read the spec. It records:
   - `published` and `target`: what was replicated;
   - `rule`: the pre-set rule from the original criterion;
   - `original`: the original audit, its criterion commit and its headline values;
   - `engine_route`: the MCP calls that reproduce it, for example `test_association(kind="inequality", ...)` for
     B, or `fit_model` and `spatial_regression(model="error")` for C;
   - `tolerance`: the fixed rerun tolerance.
3. Rerun:
   - one spec: `scripts/run_replications.py --only <id>`;
   - all five: `scripts/run_replications.py`, which writes `docs/audits/replication_suite.md`.

   In Python, `census.replications.run("<id>")` returns `{"status": "agrees" | "differs" | "skipped", ...}`. An
   agent can follow the `engine_route` calls step by step instead.
4. Read the status:
   - **agrees**: within tolerance of the original audit;
   - **differs**: report the difference and its cause (an engine route versus the original hand script). It never
     changes the registered result, and an engine route that turns out wrong is fixed;
   - **skipped**: input data are absent. `monnat_d` needs the owner's manual CDC WONDER exports in
     `external_data/wonder/`. WONDER is never fetched automatically (`docs/data/wonder_exports.md`).
5. For new published findings, register a new replication: write the rule before the comparison, as Rounds 66–69
   did (`get_recipe("preregistered")`).
