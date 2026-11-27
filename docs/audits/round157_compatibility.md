# Round 157 Compatibility Audit (`v0.152.0`)

- **Scope:** Modularized `census/manifest/methods.py` (`2,480` → `2,247` lines) by extracting causal/epidemiologic method handlers into `census/manifest/methods_epi.py` with full re-export parity on `census.manifest.methods`.
- **Backward Compatibility:** Zero behavioral change; all 28 manifest methods, citation keys, and Track A parity tests pass unchanged.
- **Review Note:** Author self-review, not independent.
