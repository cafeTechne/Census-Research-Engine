# Plan — Round 109: Fuller Ecologic Slope & Joinpoint AAPC Repairs + Manifest Parity (`rdd`, `disease_map`)

**Version target:** `v0.105.0`  
**Branch:** `phase103/agent-access-hygiene` (uncommitted per owner instruction)  
**Ground rules:** validation first (criterion frozen before the full run; failed candidates stay exploratory); `run_golden.py` byte-identical; no automated WONDER access; no sub-national counts 1–9; no commit/merge/release without owner approval.

---

## 1. Motivation

1. **Fuller (1987) $\alpha$-modified Croon/Fuller ecologic slope (`E3d`):** Round 108's `E3c` passed 11/12 cells (`.870–.905`) and missed only `ICC = 0.05, J = 150, n_j = 80` (`.853`, bias `+0.135`) due to $O(1/J)$ upward ratio bias in $1 / (s_{xx} - \overline{v}_x)$. Adding Fuller's (1987, Theorem 2.5.1) $\alpha = 4$ denominator modification `den = max(sxx - mv + 4 * mv / J, sxx / J)` removes this finite-sample bias.
2. **Joinpoint AAPC bootstrap-$t$ interval (`J3c`, Round 77):** Round 77's AAPC intervals failed (`.75–.92`) because delta-method SEs treat estimated joinpoint locations as fixed and percentile bootstraps under-cover at $T = 15\text{–}20$. Round 109 tests a parametric residual bootstrap that re-estimates joinpoint locations in every draw and pairs the bootstrap SE with $t(n - 2k - 2)$ critical values.
3. **Manifest parity for Rounds 96/98/104/105 validated methods:** Add `rdd` (Round 98/105 sharp/fuzzy RDD with continuous CCT CER bandwidth or discrete replicate weights) and `disease_map` (Round 96/104 BYM2 `method="B3"` gated at `median E ≥ 30` without suppressed counts) to `census/manifest/methods.py` (20 → **22 manifest methods**).

---

## 2. Deliverables

1. **Frozen criterion, core & harness:** `docs/audits/repairs109_criterion.md`, `census/repairs109_core.py`, `scripts/repairs109_validation.py`.
2. **Validation audit:** `docs/audits/repairs109_validation.md` and `docs/audits/repairs109_validation.json`.
3. **Wire passing repairs only:**
   - `E3d` → `census/ecologic.py` (`ecologic_corrected_slope`, gated at `median_area_n ≥ 80, areas ≥ 50`).
   - `J3c` → `census/joinpoint.py` (`aapc_bootstrap_t`).
4. **Manifest methods:** `rdd` and `disease_map` in `census/manifest/methods.py` (confirmatory manifests refuse exploratory configurations).
5. **Tests, docs & verification:** `tests/test_round109.py`, `docs/audits/round109_compatibility.md`, `docs/agent_protocol.md` + `scripts/sync_rule_text.py`, `STATUS.md`, `CHANGELOG.md`, `ROADMAP_BACKLOG.md`, version `0.105.0` (`census/__init__.py`, `census/pipeline.py`, `CITATION.cff`), pytest + `run_golden.py` check.
