# Plan — Round 111: Confirmed-Method Correctness, Edge-Case Hardening & Adversarial Stress-Test Audit

**Version target:** `v0.107.0`  
**Branch:** `phase103/agent-access-hygiene` (uncommitted per owner instruction)  
**Ground rules:** honest validation & stress-test reporting; fix every real numerical/edge-case bug uncovered; `run_golden.py` byte-identical; no commit/merge/release without owner approval.

---

## 1. Motivation

Before attempting the final wave of repairable exploratory measures (Round 112), we audit our **confirmed/validated** methods (especially the 16 newly validated methods/extensions from Rounds 104–110 and the 9 new manifest methods) along three axes:
1. **Independent mathematical & reference cross-checks:** Verify analytical identities, limiting cases, invariances (scale, shift, permutation), and agreement with `scipy`/`statsmodels` references.
2. **Numerical & edge-case error-proofing:** Fuzz every confirmed entry point with NaNs/Infs, constant/collinear columns, zero/negative SEs or counts, boundary 0/1 proportions, tiny samples, and zero-cell 2×2 tables. Fix any unhandled crash, silent `NaN`, or false `validated=True` flag.
3. **Out-of-DGP adversarial stress testing:** Measure empirical coverage/size under heavy-tailed $t_3$ errors, heteroscedasticity, unbalanced cluster sizes, overdispersed counts, extreme survey weights, and mild nonlinearity (`scripts/confirmed_stress_audit.py` → `docs/audits/confirmed_stress_audit.md`), documenting exact robustness vs. breakdown limits.

---

## 2. Deliverables

1. `tests/test_round111.py`: mathematical/reference cross-checks + adversarial edge-case battery across all confirmed Rounds 104–110 methods and manifest runners.
2. Targeted hardening fixes in `census/*.py` for every edge-case bug uncovered by `tests/test_round111.py`.
3. `scripts/confirmed_stress_audit.py`, `docs/audits/confirmed_stress_audit.md`, and `docs/audits/confirmed_stress_audit.json`.
4. `docs/audits/round111_compatibility.md`, `STATUS.md`, `CHANGELOG.md`, `ROADMAP_BACKLOG.md`, version `0.107.0`, pytest + `run_golden.py` check.
