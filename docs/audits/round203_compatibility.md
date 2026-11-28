# Round 203 Compatibility Audit — Multi-Component `spatial_model` & Top-Level Exports (`v0.199.0`)

- **Date:** 2026-11-27
- **Review status:** author self-review, not independent
- **Summary:** Exposed `allow_disconnected=True` in `census/workflows_geo.py:spatial_model` and exported `confounding_adjustment_screen`, `lint_latex`, `compile_latex_pdf`, and `verify_bundle` at top-level `census`.
