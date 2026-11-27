# Round 121 Compatibility Audit (`v0.116.0`)

- **Code changes:** `census/rdd.py` discrete-bandwidth fallback for large-sample integer running variables when `ik_bandwidth` pilot $h_1$ falls below the grid spacing (frozen `census/rdd_core.py` untouched).
- **Study artifacts:** `scripts/r121_medicare_rdd_study.py`, `docs/studies/r121_medicare_rdd_study.md`, `tests/test_round121.py`.
- **Legacy manifest goldens:** Unchanged (byte-identical).
