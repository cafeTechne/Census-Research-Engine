# Plan — Round 118: Pre-Commit Release Hygiene, Packaging Audit & Full Verification (`v0.114.0`)

**Branch:** `phase103/agent-access-hygiene` (uncommitted per owner instruction)  
**Goal:** Run a comprehensive pre-commit release-hygiene & packaging audit across the entire Rounds 103–118 series (`v0.99.0` → `v0.114.0`) so the repository is 100% clean, consistent, and ready for the owner's commit/release decision.

## Deliverables
1. `scripts/release_hygiene_check.py`: automated offline check verifying:
   - Version parity across `census/__init__.py`, `census/pipeline.py`, `CITATION.cff`, and `pyproject.toml` (if present).
   - `scripts/sync_rule_text.py --check` == 0.
   - Bundled price-index and RPP CSV SHA-256 integrity passes.
   - Zero AI-attribution strings in tracked docs/plans/changelog, zero stray temp files in repo root, and all `PLAN_ROUND_103..118.md` + `docs/audits/round103..118_compatibility.md` present.
2. `docs/audits/round103_118_release_summary.md`: executive summary of the entire Rounds 103–118 series (commit-ready release notes).
3. `tests/test_round118.py`: verifies `scripts/release_hygiene_check.py` passes cleanly.
4. Full-repository `pytest` run (~2,500+ tests) + `scripts/run_golden.py` byte-identical verification.
5. Update `STATUS.md`, `CHANGELOG.md`, `ROADMAP_BACKLOG.md`, version `0.114.0` (still **uncommitted** awaiting owner approval).
