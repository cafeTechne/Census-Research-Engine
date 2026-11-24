# Round 110 Compatibility Audit (`v0.106.0`)

- **Manifest execution golden (`scripts/run_golden.py`):** byte-identical to pre-Round-103 baseline (`/tmp/r103_run_before.json`).
- **Manifest method registry (`census/manifest/methods.py`):** 22 → **24 methods** (added `joinpoint` and `demography`). Schema golden differs only in supported-method/statistic messages; existing manifests are unaffected.
- **Validation discipline:** `S3` (synthetic-control conformal at `T_pre ≥ 15`) and `W2` (WHO `mdm_w`/`mdb_w` SNR gate) failed their pre-set criteria (`docs/audits/repairs110_validation.md`) and were **not** promoted; `census/staggered.py` and `census/inequality_monitoring.py` remain unchanged.
- **Agent routing:** `docs/agent_routing.md` and `tests/test_agent_routing.py` expanded from 37 to **40 offline-tested rows (`R1–R40`)**; `docs/agent_protocol.md` synced to `mcp_server.py`.
- **No new MCP tools (81 total; 16 `core`, 17 `core_spatial`) and no new dependencies.**
