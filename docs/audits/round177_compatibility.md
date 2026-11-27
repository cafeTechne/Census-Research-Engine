# Round 177 Compatibility Audit (`v0.172.0`)

- **Scope:** Modularized `census/spatial.py` (`1,222` → `818` lines) by extracting spatial regression and known-variance correction helpers into `census/spatial_regression_helpers.py` with full re-export parity on `census.spatial`.
- **Backward Compatibility:** Zero behavioral change; all spatial autocorrelation, LISA, and spatial regression tests pass unchanged.
- **Review Note:** Author self-review, not independent.
