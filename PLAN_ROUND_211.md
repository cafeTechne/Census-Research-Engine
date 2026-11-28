# Plan — Round 211: Expose `confounding_screen` via Layer A MCP/CLI, Routing `R104–R109` & `v0.207.0` Sync

## 1. Strategic Objective
Expose `census.standardize.confounding_adjustment_screen()` as a first-class Layer A workflow tool (`confounding_screen`) across `census/workflows_reporting.py`, `census/workflows_inference.py`, `mcp_server.py` (**85** tools), `census/references.py:TOOL_SOURCES` (**85 == 85** parity), and `python -m census tool confounding_screen`, expand `docs/agent_routing.md` to **109** rows (`R104–R109`), and sync `0.207.0`.

## 2. Exact File Contracts
1. `census/workflows_reporting.py`: Add `confounding_screen(...)`.
2. `census/workflows_inference.py`: Re-export `confounding_screen`.
3. `mcp_server.py`: Register `workflows_inference.confounding_screen`.
4. `census/references.py`: Register `"confounding_screen"` in `TOOL_SOURCES`.
5. `census/__main__.py`: Add `confounding_screen` to `_WORKFLOW_TOOLS`.
6. `README.md` & `STATUS.md`: Sync exact tool count (`85`).
7. `docs/agent_routing.md`: Append `R104–R109` (109 rows total).
8. `tests/test_round211.py`, `docs/audits/round211_compatibility.md`, and `0.207.0` version/hygiene sync.

## 3. Iteration Log
- *2026-11-27 (Cron #6):* Plan drafted and implemented strictly inside the sandbox.
