# Plan — Round 108: Multi-Confounder Parametric G-Formula, Realistic-Regime Gated Repairs & Manifest Parity

**Version target:** `v0.104.0`  
**Branch:** `phase103/agent-access-hygiene` (uncommitted per owner instruction)  
**Ground rules:** validation first (criterion frozen before the full run; failed candidates stay exploratory); `run_golden.py` byte-identical; no automated WONDER access; no sub-national counts 1–9; no commit/merge/release without owner approval.

---

## 1. Motivation

1. **Multi-confounder parametric g-formula (`M5b`):** Round 106 validated the parametric g-formula (`method="gformula"`) for annual policy panels with one time-varying confounder (`p = 1`, coverage `.883–.920`). Real policy panels routinely require **2–3 correlated time-varying confounders** (e.g., unemployment, poverty, uninsurance) with mutual VAR(1) dynamics and treatment-confounder feedback. Extending `gformula_point` / `gformula_jackknife` to vector $L_t \in \mathbb{R}^p$ removes the single-confounder restriction in `census/msm.py`.
2. **Realistic-regime gated repairs (`E3c`, `S2b`):**
   - `E3c` (Croon/Fuller reliability-corrected ecologic/between-area slope): Round 107 achieved `.880–.905` across all `n_j ≥ 80` cells (typical real PUMAs have `n_j ≥ 100`–`500` records) and missed only `J=150, n_j=40`. Round 108 validates `E3c` across the PUMA regime `n_j ∈ {80, 150, 300}`, `J ∈ {50, 150}`, `ICC ∈ {0.05, 0.15}`.
   - `S2b` (Shannon entropy diversity with SDR replicate bias correction): Round 107 achieved `.886` (`G=4`) and `.904` (`G=6`) at `n_resp = 200` (typical tracts have `n ≥ 200` respondents). Round 108 validates `S2b` across `G ∈ {4, 6}`, `n_resp ∈ {150, 200, 400}`.
3. **Manifest parity for Rounds 104–107 validated methods:** Add `designation` (Round 85/107 FH posterior + validated `prob80`/`point` PPV intervals) and `agreement` (Round 37/48/106 bias, observed Bland–Altman limits, quintile kappa, and validated observed Lin's CCC) to `census/manifest/methods.py` (18 → **20 manifest methods**).

---

## 2. Deliverables

1. **Frozen criterion, core & harness:** `docs/audits/repairs108_criterion.md`, `census/repairs108_core.py`, `scripts/repairs108_validation.py`.
2. **Validation audit:** `docs/audits/repairs108_validation.md` and `docs/audits/repairs108_validation.json`.
3. **Wire passing repairs only:**
   - `M5b` → `census/msm.py` (`method="gformula"` supports any `p >= 1` time-varying confounders).
   - `E3c` → `census/ecologic.py` (`ecologic_corrected`, gated at `median_area_n ≥ 80, areas ≥ 50`).
   - `S2b` → `census/spatial_models.py` (`diversity_index(..., method="sdr_bc")`, gated at `n_resp ≥ 150`).
4. **Manifest methods:** `designation` and `agreement` in `census/manifest/methods.py` (confirmatory manifests refuse exploratory sub-measures).
5. **Tests, docs & verification:** `tests/test_round108.py`, `docs/audits/round108_compatibility.md`, `docs/agent_protocol.md` + `scripts/sync_rule_text.py`, `STATUS.md`, `CHANGELOG.md`, `ROADMAP_BACKLOG.md`, version `0.104.0` (`census/__init__.py`, `census/pipeline.py`, `CITATION.cff`), pytest + `run_golden.py` check.
