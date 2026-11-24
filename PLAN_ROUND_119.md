# Plan — Round 119: Citation Integrity, End-to-End Manifest Integration, Templates & Lint Cleanup (`v0.115.0`)

**Branch:** `phase103/agent-access-hygiene` (uncommitted per owner instruction)  
**Goal:** Close the final 4 integration and hygiene gaps uncovered after Rounds 103–118 so the entire series is 100% citation-complete, end-to-end manifest-tested, template-documented, and lint-clean.

## Deliverables
1. **Citation integrity (`census/references.py`):** Register all 7 missing manifest citation keys (`bernal2017`, `calonico2014`, `fh`, `imbens_kalyanaraman2012`, `lash2009`, `lin1989`, `nagashima2019`) plus Round 104–109 repair references (`fuller1987`, `korn_graubard1990`, `thompson_sharp1999`), and add an invariant check in `scripts/release_hygiene_check.py` + `tests/test_round119.py` asserting **zero** unresolved manifest citation keys.
2. **End-to-end `run_manifest` integration tests (`tests/test_round119.py`):** Run full `run_manifest` offline (manifest JSON → synthetic frame → `run.json`, `methods.md`, `references.bib`, `bundle.json`) for newly added manifest methods (`agreement`, `designation`, `bias_analysis`, `estimate_effect`) verifying clean JSON serialization, BibTeX generation, and Holm-adjusted hypothesis tables.
3. **Modern manifest templates (`examples/manifests/templates/`):** Add 4 clean, schema-validated example manifests (`causal_estimate_effect.json`, `designation_ppv.json`, `agreement_ccc.json`, `meta_combine_estimates.json`) verified by `validate_manifest(..., resolve=False)` in `tests/test_round119.py`.
4. **Static lint cleanup:** Run `ruff` (or `pyflakes`/AST checks) across all Rounds 103–119 files and clean up any unused imports or warnings.
5. Update `scripts/release_hygiene_check.py` (cover `PLAN_ROUND_103..119.md` + citation invariant), `docs/audits/round119_compatibility.md`, `STATUS.md`, `CHANGELOG.md`, `ROADMAP_BACKLOG.md`, version `0.115.0`, and verify tests + `run_golden.py`.
