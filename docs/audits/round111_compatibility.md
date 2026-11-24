# Round 111 Compatibility Audit (`v0.107.0`)

- **Manifest execution golden (`scripts/run_golden.py`):** byte-identical to pre-Round-103 baseline (`/tmp/r103_run_before.json`).
- **Hardening fixes:** strictly defensive edge-case guards in `census/agreement.py` (identical series `x == y`), `census/repairs106_core.py`, and `census/repairs109_core.py` (constant `x`); zero behavior change on valid non-degenerate inputs.
- **No new MCP tools (81 total), no new manifest methods (24 total), and no new dependencies.**
