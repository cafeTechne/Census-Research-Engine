# Plan — Round 212: Unattended Engine Sprint Final Regression Gate & `v0.208.0` Readiness

## 1. Strategic Objective
Close out the 7-hour unattended pure-engine sprint (Rounds 203–212, `v0.199.0` → `v0.208.0`) with a comprehensive contract + round regression sweep, `doctor --deep --json` (85 == 85 MCP/TOOL_SOURCES parity), `release_hygiene_check.py`, routing `R110` (110 rows total), and a clean evening summary in `docs/audits/unattended_engine_sprint_log.md` awaiting owner commit/tag approval.

## 2. Exact File Contracts
1. `docs/agent_routing.md`: Append `R110` (110 rows total).
2. `scripts/release_hygiene_check.py`: Extend through Round 212 (`range(126, 213)`).
3. Version sync `0.208.0`: `census/__init__.py`, `census/pipeline.py`, `CITATION.cff`, `CHANGELOG.md`, `STATUS.md`.
4. `tests/test_round212.py`, `docs/audits/round212_compatibility.md`, and final `docs/audits/unattended_engine_sprint_log.md`.

## 3. Iteration Log
- *2026-11-27 (Cron #7, 7:16 PM EST):* Final sprint gate executed strictly inside the sandbox; zero git commits/tags run.
