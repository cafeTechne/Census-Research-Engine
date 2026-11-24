# Plan — Round 112: Final Repairable Exploratory Wave

**Version target:** `v0.108.0`  
**Branch:** `phase103/agent-access-hygiene` (uncommitted per owner instruction)  
**Ground rules:** validation first (criterion frozen before the full run; failed candidates stay exploratory); `run_golden.py` byte-identical; no automated WONDER access; no sub-national counts 1–9; no commit/merge/release without owner approval.

---

## 1. Motivation

Following Round 111's confirmed-method hardening and stress-test audit, Round 112 runs pre-specified full validations on the **5 genuinely repairable exploratory candidates** remaining in `census/*.py`:
1. **`M3b`** — Three-level variance-share jackknife intervals (`census/multilevel3.py`: previously only screened on 100 draws).
2. **`Q2e-lower` & `Q2e-prob50`** — Designation PPV parametric bootstrap intervals with Li–Lahiri positive-$A$ floor for `rule="lower"` and `rule="prob50"` (`census/designation.py`, complementing Round 107's validated `prob80` and `point`).
3. **`D2`** — Count-scale disparity indices (`idisp`, `bgv`, `theil`, `mld`, `census/disparity.py`) via parametric Poisson bootstrap gated at `min_events ≥ 100`.
4. **`R2_dens`** — RDD manipulation/density test (`census/rdd.py`: `rdd_core.density_test`) formal null-size validation across Uniform, Normal, and Beta(2,2) densities.
5. **`W3_rr`** — Stratified count RR homogeneity test (`census/stratified.py`: score/Cochran–Q test on log-RR gated at `min_cases ≥ 15`).

---

## 2. Deliverables

1. `docs/audits/repairs112_criterion.md`, `census/repairs112_core.py`, `scripts/repairs112_validation.py`.
2. `docs/audits/repairs112_validation.md` and `docs/audits/repairs112_validation.json`.
3. Wire **only** candidates that pass their pre-set criterion into `census/multilevel3.py`, `census/designation.py`, `census/disparity.py`, `census/rdd.py`, and/or `census/stratified.py`.
4. `tests/test_round112.py`, `docs/audits/round112_compatibility.md`, `docs/agent_protocol.md` + `scripts/sync_rule_text.py`, `STATUS.md`, `CHANGELOG.md`, `ROADMAP_BACKLOG.md`, version `0.108.0`, pytest + `run_golden.py` check.
