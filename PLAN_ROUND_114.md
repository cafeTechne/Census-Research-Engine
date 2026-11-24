# Plan — Round 114: Final 4 Pre-Registered Manifest Methods (`v0.110.0`)

**Branch:** `phase103/agent-access-hygiene` (uncommitted per owner instruction)  
**Goal:** Close the last 4 pre-registered manifest gaps in `census/manifest/methods.py` (24 → **28 manifest methods**) so every validated area, panel, and summary-level design in the engine can run confirmatively with full provenance and methods text.

## Deliverables
1. Register 4 new `MethodSpec` entries in `census/manifest/methods.py`:
   - `difference_in_differences`: supports `design ∈ {"two_group", "event", "staggered", "triple", "msm"}` (enforcing `method="gformula"` for confirmatory `msm`, `sun_abraham` or `callaway_santanna` with `se` for `staggered`, and `product="1-year"|"annual"` for annual designs).
   - `interrupted_series`: runs `census.small_spatial.interrupted_series` (`bootstrap_t_cons` validated from 17+ annual points; refuses overlapping 5-year series and exploratory short series in confirmatory manifests).
   - `combine_estimates`: runs `census.evidence.combine_estimates` on an input frame of study estimates/SEs (exposing `pooled`, `prediction_interval`, `meta_regression`, and `egger_test`; confirmatory manifests enforce `k ≥ 10` for PI/meta-reg/Egger and validated HKSJ/truncated-KH for `pooled`).
   - `bias_analysis`: runs `census.bias_analysis.e_value` or `misclassification(..., sd=...)` (exposing deterministic `e_value` and Round 105 validated probabilistic misclassification `corrected_rr` / `corrected_or`).
2. Update `docs/agent_protocol.md` (sync via `scripts/sync_rule_text.py`), `tests/test_round114.py`, `docs/audits/round114_compatibility.md`, `STATUS.md`, `CHANGELOG.md`, `ROADMAP_BACKLOG.md`, version `0.110.0`, and verify `run_golden.py` remains byte-identical.
