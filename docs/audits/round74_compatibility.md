# Round 74 compatibility and acceptance

Author self-review, not independent. Worktree `/tmp/census-round74`, branch `phase74/replication-suite`.
- The branch was started on defaultBranch `09b2464` while Rounds 71 and 73 were in progress, then rebased onto
  them.
- No new statistics. Version 0.70.0.

## Live run (`replication_suite.md`)

All five reruns agree with their original audits:

| Replication | Result |
| :--- | :--- |
| A | max \|D − CHR\| 2.8e-14 over the same 2,055 counties |
| B | max 4.8e-6 (the Round 66 JSON stores estimates to 5 decimals) |
| C | 0 over the 6 slopes |
| D | 2.1e-14 |
| E | 1.1e-10 |

There were no disagreements, so section 3 of the plan (reporting a cause, fixing an engine route) was not needed.

## Engine routes compared with the original hand scripts

- **A** uses `segregation_indices` and the CHR file through `context_sources.fetch_chr_additional`. That file's
  SHA-256 equals Round 66's pin.
- **B** uses `test_association(kind="inequality")`.
  - That route refuses negative incomes, so the spec's variable `(HINCP > 0) * HINCP * ADJINC / 1000000` sets
    negatives to zero, as Round 66's primary did.
  - An offline test checks that this equals the hand clipping.
- **C** uses `fit_model` and the `spatial_regression` workflow, with islands dropped as in Round 67.
  - The frame carries `Year = 2018`, so the representative points match the 2018 tract vintage.
  - Without it, `frame_coordinates` defaults to 2022 boundaries and the SCPC call fails on retired GEOIDs. The
    rerun found this pitfall; it is not an engine bug.
- **D's ERS values** now come from the ERS GIS service (Round 72) instead of Round 69's hashed JSON. The result is
  identical.

## Plan deviations and exceptions

1. **Specs, not study manifests.** The plan named manifests rerun with `run_manifest`. The manifest method registry
   has no PUMS Gini, no three-level variance shares and no state-FE spatial error model with constructed design
   columns, so these replications cannot be expressed as manifests without new manifest methods.
   - Each spec instead lists the MCP calls (`engine_route`), and the runner executes the same workflow functions.
   - No new MCP tool was added, as the plan required.
   - Registered manifests are untouched.
2. **The live test covers A, B, C and E.** D needs the owner's WONDER exports; its rerun was done locally and is in
   the report.
3. The report includes D's coefficients. They derive from county death counts of at least 10 and contain no count
   from 1 to 9.

## Acceptance

- Goldens: byte-identical.
- New tests: `tests/test_round74.py`. Offline: 21 passed with `test_mcp_profiles`. Live (`CENSUS_LIVE_TESTS=1`): 4
  parametrized reruns.
- Full suite: goldens byte-identical; 2203 passed, 42 skipped; 0 failures; live reruns 4 passed.
