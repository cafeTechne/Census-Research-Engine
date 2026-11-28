# Round 202 Compatibility Audit — Reusable `confounding_adjustment_screen`, 100 Routing Rows & `v0.198.0` Sync

- **Date:** 2026-11-27
- **Review status:** author self-review, not independent
- **Summary of changes:**
  - Added reusable `census.standardize.confounding_adjustment_screen()` (crude vs. confounder-adjusted Poisson GLM with HC3 SEs, `% change-in-estimate`, and Simpson's-paradox `sign_flipped` flag).
  - Expanded `docs/agent_routing.md` to **100** rows (`R98–R100`), closed `N131` and `N132` in `ROADMAP_BACKLOG.md`, extended `scripts/release_hygiene_check.py` through Round 202, and synced version `0.198.0`.
