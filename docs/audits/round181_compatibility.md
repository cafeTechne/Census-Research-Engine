# Round 181 Compatibility Audit (`v0.176.0`)

- **Scope:** Modularized `census/pums.py` (`1,159` → `921` lines) by extracting PUMS regression and PUMA geography helpers into `census/pums_stats.py` with full re-export parity on `census.pums`.
- **Backward Compatibility:** Zero behavioral change; all PUMS tests and studies pass unchanged.
- **Review Note:** Author self-review, not independent.
