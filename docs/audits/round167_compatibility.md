# Round 167 Compatibility Audit (`v0.162.0`)

- **Scope:** Modularized `census/replicate.py` (`1,443` → `1,283` lines) by extracting derived replicate-statistic algebra and wide-frame helpers into `census/replicate_stats.py` with full re-export parity on `census.replicate`.
- **Backward Compatibility:** Zero behavioral change; all callers and replicate tests work identically.
- **Review Note:** Author self-review, not independent.
