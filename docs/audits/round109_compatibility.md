# Round 109 Compatibility Audit (`v0.105.0`)

- **Manifest execution golden (`scripts/run_golden.py`):** byte-identical to pre-Round-103 baseline (`/tmp/r103_run_before.json`).
- **Manifest method registry (`census/manifest/methods.py`):** 20 → **22 methods** (added `rdd` and `disease_map`). Schema golden differs only in supported-method/statistic messages; existing manifests are unaffected.
- **Backward compatibility:**
  - `census.ecologic.ecologic_check(...)`: existing `VALIDATED_FROM`, `identity`, and `logit` keys are unchanged; additive `ecologic_fuller` key reports Round 109's validated Fuller ($\alpha = 4$) ecologic slope gated at `areas ≥ 50, median_area_n ≥ 80`.
  - `census.joinpoint.joinpoint(...)`: existing `VALIDATED` and `aapc` keys are unchanged; additive `aapc_bootstrap_t` key reports Round 109's validated bootstrap-$t$ AAPC interval gated at `T ≥ 15, events ≥ 200, k ≤ 1`.
- **No new MCP tools (81 total; 16 `core`, 17 `core_spatial`) and no new dependencies.**
