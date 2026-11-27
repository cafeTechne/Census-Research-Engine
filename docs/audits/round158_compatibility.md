# Round 158 Compatibility Audit (`v0.153.0`)

- **Scope:** Modularized `census/models.py` (`1,432` → `1,025` lines) by extracting `fit_eiv`, `simex`, `cluster_labels`, `_cluster_jackknife`, and `_design_deviations` into `census/models_eiv.py` with full re-export parity on `census.models`.
- **Backward Compatibility:** Zero behavioral change; all callers and tests importing from `census.models` work identically.
- **Review Note:** Author self-review, not independent.
