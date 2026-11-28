# Round 208 Compatibility Audit — `doctor --deep` Invariant Self-Check (`v0.204.0`)

- **Date:** 2026-11-27
- **Review status:** author self-review, not independent
- **Summary:** Added `deep=True` / `--deep` to `doctor_report()` and `python -m census doctor`, checking 1:1 MCP tool ↔ `TOOL_SOURCES` parity, recipe doc parity, and `metadata/manifest.json` integrity.
