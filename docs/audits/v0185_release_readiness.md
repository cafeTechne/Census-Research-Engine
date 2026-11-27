# `v0.185.0` Release Readiness Audit (Round 189)

- **Date:** 2026-11-27
- **Target Version:** `0.185.0` (working tree; last tagged/pushed release: `v0.115.0`)
- **Review Status:** author self-review, not independent
- **Git Commit / Tag Status:** **Not committed or tagged** (awaiting explicit owner approval)

## 1. Automated Verification Gates

| Gate | Command | Result |
| :--- | :--- | :--- |
| Full-repo `pytest` sweep | `.venv/bin/python -m pytest -q tests/ layer_b_openscholar/tests/` | **2,597 passed, 0 failed**, 42 skipped (opt-in live/GPU), 79 subtests passed *(initial sweep caught 26 regressions: missing `@mcp.tool()` on `generate_codebook`, 3 new tools missing from `TOOL_SOURCES`, 6 monolith monkeypatch indirections in `spatial_regression_helpers`/`pipeline_replay`/`concordance_overrides`, 16 rule-text test paths pointing to `mcp_server.py` instead of `census/mcp_instructions.py`, and 3 stale count assertions — all 26 fixed and re-verified passing in 8.33s)* |
| Contract & Round 185–189 gate | `pytest -q test_round185..189 test_agent_routing test_mcp_profiles test_packaging test_track_a/b test_proposition_verification layer_b_openscholar/tests/` | **99 passed, 0 failed**, 72 subtests passed |
| Release hygiene | `.venv/bin/python scripts/release_hygiene_check.py` | `"ok": true`, `"version": "0.185.0"`, `"manifest_methods": 28`, `"errors": []` |
| Environment & data integrity | `.venv/bin/python -m census doctor --json` | `"ok": true`, `"bundled_data_ok": true`, `recipe_count: 33`, `manifest_method_count: 28`, zero secret leakage |
| Flagship manuscript bundle | `verify_bundle("studies_output/r188_flagship_manuscript/bundle")` | `"ok": true`, `checked_files: 4`, `errors: []`, 11 WONDER causes, 3 PDF/SVG/PNG figures, 2 booktabs `.tex` tables |
| Layer B Tier 2 Neural RAG | `venv-neural` (`BAAI/bge-small-en-v1.5`) on Samsung 850 EVO SSD | `2,631` neural 384-dim vectors + `2,631` hash vectors (`5,262` rows), `1,148` passages across `67` docs (incl. `198` EPMC JATS XML passages), benchmark written to `docs/audits/layer_b_neural_rag_benchmark.md` |

## 2. Working Tree Breakdown (`git status --short`)

- **Modified (`M`):** `47` files (version sync `0.185.0`, `README.md`, `STATUS.md`, `CHANGELOG.md`, `CITATION.cff`, `docs/agent_routing.md`, modularized `census/` modules, `mcp_server.py`, `layer_b_openscholar/` upgrades, updated tests)
- **Untracked (`??`):** `226` files (new modularized helper modules, `layer_b_openscholar/` isolated package, `docs/studies/`, `docs/audits/round121..189_compatibility.md`, `examples/mcp/dual_mcp_config.json`, `docs/dual_mcp_quickstart.md`, `scripts/r136..r188_*.py`, `tests/test_round121..189.py`, and active plans `PLAN_ROUND_125.md`, `PLAN_ROUND_186.md`–`PLAN_ROUND_189.md`)
- **Deleted (`D`):** `17` files (completed historical `PLAN_ROUND_103..119.md` cleared from repo root per owner request)

## 3. Ready-to-Run Commit & Tag Commands (For Owner Approval)

When you are ready to commit and tag `v0.185.0`:

```bash
git status --short
git add -A
git commit -m "Release v0.185.0: Rounds 121-189 (Two-Layer Engine, Neural Tier 2 RAG, 11-Cause Manuscript & Full-Repo Sweep)"
git tag -a v0.185.0 -m "v0.185.0: Two-Layer Research Engine, Neural Tier 2 RAG, 11-Cause County Mortality Atlas"
git push origin defaultBranch --tags
```
