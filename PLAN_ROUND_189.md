# Plan — Round 189 (Track 1): Full-Repository Stabilization, Regression Gate & `v0.185.0` Release Prep (`v0.185.0`)

## 1. Strategic Objective
Run a comprehensive, stone-unturned stabilization audit across the entire repository (every test file in `tests/` and `layer_b_openscholar/tests/`, golden manifest parity, `sync_rule_text.py --check`, `release_hygiene_check.py`, `doctor`, and `git status` hygiene), expand routing `R85–R88`, and prepare a clean, review-ready `v0.185.0` release candidate (awaiting explicit owner approval before committing/tagging/pushing).

## 2. Exact Verification & Stabilization Checklist
1. **Full Repository Pytest Run:** Execute `.venv/bin/python -m pytest -q` across the entire `tests/` directory AND `layer_b_openscholar/tests/` (excluding only opt-in `CENSUS_LIVE_TESTS=1` network tests). Fix any regression uncovered.
2. **Legacy Golden & Verification Contract Gates:**
   - `tests/test_track_a_manifest_parity.py`
   - `tests/test_track_b_bibtex_bundle.py`
   - `tests/test_proposition_verification.py`, `tests/test_verification_contract.py`, `tests/test_workflows_verification.py`, `tests/test_verification_release.py`
   - `tests/test_agent_routing.py`, `tests/test_mcp.py`, `tests/test_mcp_profiles.py`, `tests/test_mcp_round7.py`
3. **Version & Hygiene Consolidation (`0.185.0`):**
   - Expand `docs/agent_routing.md` with `R85–R88` (88 rows total).
   - Extend `scripts/release_hygiene_check.py` through Round 189 (`range(126, 190)`).
   - Sync version `0.185.0` across `census/__init__.py`, `census/pipeline.py`, `CITATION.cff`, `CHANGELOG.md`, and `STATUS.md`.
   - Confirm zero AI-attribution strings, zero secrets, zero untracked temporary junk in `git status`.
4. **Release Readiness Summary (`docs/audits/v0185_release_readiness.md`):**
   - Document exact test counts, file change breakdown (`git status --short`), and the exact `git add` / `git commit` / `git tag v0.185.0` commands ready for the owner's go-ahead.

## 3. Acceptance Gates
1. Full repository test suite passes with 0 failures.
2. `scripts/release_hygiene_check.py` exits `0` (`"ok": true`, `version: "0.185.0"`).
3. `python -m census doctor` exits `0` (`"ok": true`).
4. No `git commit` or `git tag` executed until the owner explicitly approves.

## 4. Iteration Log
- *2026-11-27:* Plan drafted.
- *2026-11-27:* Ran full-repository `pytest` sweep (`2,571 passed`, caught 26 regressions from prior monolith extractions and missing `@mcp.tool()` on `generate_codebook` / `TOOL_SOURCES` entries / rule-text test paths). Fixed all 26 regressions (`26 passed in 8.33s`; `2,597` total passing, `0` failures). Expanded `docs/agent_routing.md` (`R85–R88`, 88 rows), extended `scripts/release_hygiene_check.py` through Round 189, synced version `0.185.0`, verified `doctor` + `release_hygiene_check.py` + `99` contract/Round 185–189 tests, and wrote `docs/audits/v0185_release_readiness.md`. Working tree left uncommitted awaiting owner approval.
