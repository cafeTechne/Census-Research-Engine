# Round 70 compatibility and acceptance

Author self-review, not independent. Worktree `/tmp/census-round70`, branch `phase70/env-progress`, based on
defaultBranch `9f0c0f2`. No new statistics.

## Changes

| Item | Change |
| :--- | :--- |
| N47 `.env` | `census/env.py` `load_environment()`; used by `census/api.py` and `mcp_server.py`; docs in README and `docs/claude_setup.md` |
| N48 checkpoints | `run_manifest(checkpoint=True)` (library, MCP, CLI); `_Checkpoint` in `census/manifest/run.py` |
| N48 progress | `census/progress.py`; lines in `run_manifest` (per analysis), `run_batch` (every 25 requests when no callback is given) and `fit_replicate` refits (every 20) |

## Exceptions to the plan

- **MCP progress notifications are deferred.** The tools are synchronous functions run by FastMCP; forwarding to the
  async context needs a wrapper per tool. `census.progress.set_callback` is the hook for that later. Stderr lines
  already appear in MCP server logs.
- **Pickle instead of JSON for checkpoints.** Results are `ModelResult` and other objects holding DataFrames, which
  JSON cannot store without loss. A checkpoint is reused only when its key (manifest hash, analysis spec, data
  hash) matches. The docstring says never to resume from a folder you did not create.
- **Regression-calibration refits have no progress line.** Their bootstrap loop lives in a different code path;
  that is left for a later round.
- **A behaviour note:** with `checkpoint=True` the `.checkpoint` folder is kept when an analysis failed, so a rerun
  reuses the finished ones.

## Acceptance

- Goldens: byte-identical (checkpoints and progress are opt-in or stderr-only).
- New tests: `tests/test_round70.py` (8).
- Full suite: 2171 passed, 37 skipped; 0 failures. A first run failed one core-profile description budget (the new `checkpoint` docstring text); shortened and rerun.
