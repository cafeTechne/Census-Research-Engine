# Round 176 Compatibility Audit (`v0.171.0`)

- **Scope:** Modularized `census/geo_crosswalk.py` (`1,263` → `968` lines) by extracting panel harmonization and wide-row apportionment helpers into `census/geo_crosswalk_io.py` with full re-export parity on `census.geo_crosswalk`.
- **Backward Compatibility:** Zero behavioral change; all crosswalk and tract harmonization tests pass unchanged.
- **Review Note:** Author self-review, not independent.
