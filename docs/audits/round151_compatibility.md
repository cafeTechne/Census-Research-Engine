# Round 151 Compatibility Audit (`v0.146.0`)

- **Scope:** Modularized `census/validation.py` (`2,496` → `1,890` lines) by extracting extended validation checks (`F6–F8`, `F10–F11` and helpers) into `census/validation_extended.py` with full re-export parity on `census.validation`.
- **Backward Compatibility:** Zero behavioral change; all validation tests and callers importing from `census.validation` work identically.
- **Review Note:** Author self-review, not independent.
