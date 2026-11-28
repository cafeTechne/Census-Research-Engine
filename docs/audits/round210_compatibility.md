# Round 210 Compatibility Audit — `workflows_geo_helpers.py` Modularization (`v0.206.0`)

- **Date:** 2026-11-27
- **Review status:** author self-review, not independent
- **Summary:** Extracted shared boundary, spatial-weight, replicate-release, and figure-path helpers from `census/workflows_geo.py` into `census/workflows_geo_helpers.py` with 100% re-export parity and dynamic module lookup for monkeypatch safety.
