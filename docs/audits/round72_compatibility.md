# Round 72 compatibility and acceptance

Author self-review, not independent. Worktree `/tmp/census-round72`, branch `phase72/context-sources`, based on
defaultBranch `cd85dee`. No new statistics. Implemented while Round 71's simulation ran, and merged before it, so it
takes version 0.67.0.

## Changes

- `census/context_sources.py`, the four sources and their provenance.
- `build_analysis_frame(context=…)`.
- Manifests: a `"context"` block (`validate_manifest`, `run_manifest` stage `_join_context`, `run.json` `context`).
  Context variables are available to analyses, but they are not external outcomes.
- `list_health_sources(kind="context")`; recipe `context_covariates`; README section; protocol text (generated into
  the MCP instructions).

## Plan items

- **State-wide tract pulls: no change needed.** `build_entities("tract", state)` without counties already makes one
  `tract:*` request per state. The plan assumed otherwise.
- **ERS documentation counts:** not checked. The live check confirms full county coverage and valid codes. A
  comparison of the ERS metro flag with the OMB 2013 delineation file was not run, because this environment has no
  `.xls` reader.
- **CBP check:** the live value for 01001 / 813110 (51) equals Round 69's direct probe.
- **CHR check:** the pinned file's SHA-256 equals Round 66's.

## Acceptance

- Goldens: byte-identical.
- New tests: `tests/test_round72.py` (9: 8 offline, 1 live). The live test passed when run with
  `CENSUS_LIVE_TESTS=1`.
- Full suite: 2179 passed, 38 skipped, 1 failed. The core-profile flat-parameter rule flagged the new nested `context` parameter; it was added to `NESTED_PARAM_EXCEPTIONS` beside `derive`, and the affected test files were rerun (37 passed). The full suite was not rerun for that one-line constant change, because Round 71's simulation was using the CPU.
