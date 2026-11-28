# Plan — Round 202: Reusable `confounding_adjustment_screen`, Routing `R98–R100` (100 Rows) & `v0.198.0` Sync

## 1. Strategic Objective
Promote the crude-vs.-adjusted Poisson confounding diagnostic from a one-off study script into a reusable, tested Layer A engine function (`census.standardize.confounding_adjustment_screen()`), expand `docs/agent_routing.md` to **100** rows (`R98–R100`), close `N131` and `N132` in `ROADMAP_BACKLOG.md`, extend `scripts/release_hygiene_check.py` through Round 202, and sync version `0.198.0`.

## 2. Exact File Contracts
1. `census/standardize.py`: Add `confounding_adjustment_screen(...)` computing crude vs. confounder-adjusted Poisson rate ratios (HC3 SEs), percentage change-in-estimate (`cie_pct`), and Simpson's-paradox `sign_flipped` flag.
2. `docs/agent_routing.md`: Append `R98–R100` (100 rows total).
3. `scripts/release_hygiene_check.py`: Extend through Round 202 (`range(126, 203)`).
4. Version sync `0.198.0`: `census/__init__.py`, `census/pipeline.py`, `CITATION.cff`, `CHANGELOG.md`, `STATUS.md`, `ROADMAP_BACKLOG.md`.
5. `tests/test_round202.py` & `docs/audits/round202_compatibility.md`.

## 3. Iteration Log
- *2026-11-27:* Plan drafted and implemented.
