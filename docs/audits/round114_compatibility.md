# Round 114 Compatibility Audit (`v0.110.0`)

- **Manifest execution golden (`scripts/run_golden.py`):** byte-identical to pre-Round-103 baseline (`/tmp/r103_run_before.json`).
- **Manifest method registry (`census/manifest/methods.py`):** 24 → **28 methods** (added `difference_in_differences`, `interrupted_series`, `combine_estimates`, `bias_analysis`). Schema golden differs only in supported-method/statistic messages; existing manifests are unaffected.
- **No new MCP tools (81 total) and no new dependencies.**
