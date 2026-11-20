# Round 64 compatibility and acceptance

Author self-review, not independent; implemented by the maintainer agent at the owner's request.
Worktree `/tmp/census-round64`, branch `phase64/agent-access`, based on defaultBranch `526bb1d`.
No new statistics and no simulation.

## Changes

| Item | Change |
| :--- | :--- |
| CLI (N40) | `_WORKFLOW_TOOLS` gains the nine missing shared workflows and `interrupted_series` |
| MCP (N41) | New tool `interrupted_series` (full profile; 70 → 71 tools). `fit_model(censored=...)` routes model `negbin` to `fit_censored_negbin` and refuses every other model or method |
| Rule text (N42) | 16 protocol paragraphs marked; `scripts/sync_rule_text.py` writes them into `mcp_server.py`. The protocol versions replace five stale MCP copies. The protocol's Round 35 paragraph gains the Round 53 calibration sentence that only the MCP copy had, and the Round 63 gate |
| Core text (N43) | The `build_analysis_frame` core description named `batch_download`, which `core` lacks; now `download_table`. A test enforces the rule |
| Routing (N43) | `docs/agent_routing.md` (15 rows) and `tests/test_agent_routing.py`; two tasks in `scripts/local_model_eval.py` (offline expectations OK) |

## Behaviour changes

- MCP clients see one more tool in the full profile. The core profiles are unchanged (16 and 17 tools).
- The full-profile server instructions now carry the protocol's wording for the copied passages, so they are longer
  and current.
- Registered manifests and both goldens are unchanged.

## Acceptance

- Schema and run goldens: byte-identical.
- New tests: `tests/test_agent_routing.py` (18).
- Full suite: 2155 passed, 37 skipped; 0 failures. A first run failed one older test (`test_round43`: non-core tools in core text must be marked `[full]`); the new text now uses that mark and the new test accepts it.
