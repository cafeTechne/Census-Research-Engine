# Round 197 Compatibility Audit — Age-Structure & Urban-Rural Confounding Study (`N128`, `v0.193.0`)

- **Date:** 2026-11-27
- **Review status:** author self-review, not independent
- **Summary of changes:**
  - Created `scripts/r197_age_urban_mortality_confounding.py` testing `% age 65+` (from cached 2024 ACS `B17001` VRE) and `log(population density)` adjustment across all 11 CDC WONDER 2018–2022 county mortality causes in MI+OH and NY+PA.
  - Wrote `docs/studies/r197_age_urban_confounding_study.md`, sealed bundle via `verify_bundle`, and verified via `tests/test_round197.py`.
