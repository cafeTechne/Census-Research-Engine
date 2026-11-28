# Round 200 Compatibility Audit — Multi-Component & Island-Aware BYM2 (`N132`, `v0.196.0`)

- **Date:** 2026-11-27
- **Review status:** author self-review, not independent
- **Summary of changes:**
  - Added `graph_components()` and `allow_disconnected=True` per-component ICAR scaling (Freni-Sterrantino et al. 2018) in `census/disease_mapping_core.py` and `census/disease_mapping.py`.
  - Default `allow_disconnected=False` preserves 100% backward compatibility with existing single-component tests; multi-component fits report `n_components`, `n_islands`, and remain tagged `validated: False` with an explicit note.
