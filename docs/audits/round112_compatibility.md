# Round 112 Compatibility Audit (`v0.108.0`)

- **Manifest execution golden (`scripts/run_golden.py`):** byte-identical to pre-Round-103 baseline (`/tmp/r103_run_before.json`).
- **Library changes:**
  - `census/designation.py`: `PPV_INTERVAL_VALIDATED["lower"] = True`; `ppv_intervals=False` remains default.
  - `census/disparity.py`: count-scale `idisp`, `bgv`, `theil`, `mld` now return `validated=True` when `min_group_count >= 100` (and `G <= 6`); counts `< 100` stay exploratory.
  - `census/rdd.py`: `density_test["validated"]` is `True` for continuous running variables with `n >= 1,000` (discrete or smaller `n` stay exploratory).
- **No new MCP tools (81 total), no new manifest methods (24 total), and no new dependencies.**
