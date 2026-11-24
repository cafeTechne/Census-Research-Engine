# Plan — Round 110: Synthetic-Control Conformal (`T_pre ≥ 15`) & WHO Mean-Difference SNR Gate + Manifest/Routing Parity

**Version target:** `v0.106.0`  
**Branch:** `phase103/agent-access-hygiene` (uncommitted per owner instruction)  
**Ground rules:** validation first (criterion frozen before the full run; failed candidates stay exploratory); `run_golden.py` byte-identical; no automated WONDER access; no sub-national counts 1–9; no commit/merge/release without owner approval.

---

## 1. Motivation

1. **Synthetic-control conformal inference (`S3`, Round 78):** In Round 78, Chernozhukov–Wüthrich–Zhu (2021) conformal intervals for synthetic control covered `.87–.95` with `T_pre = 15` pre-periods, but remained exploratory only because `T_pre ≥ 15` was not a pre-set gate (and `T_pre = 9` under-covered at `.73–.86`). Round 110 pre-specifies and validates the `T_pre ≥ 15, N_donors ≥ 25` conformal interval gate across AR(1) serial correlation `ρ ∈ {0.0, 0.3, 0.7}` and treatment effects `{0.0, -2.0}`.
2. **WHO mean differences `mdm_w` / `mdb_w` under clear signal-to-noise (`W2`, Round 94 / Round 104):** In Rounds 94 and 104, `mdm_w` and `mdb_w` failed only when between-group spread was small relative to sampling error (folded-normal bias on $|y_g - \bar{y}|$). When between-group spread clearly exceeds sampling error (`SNR = (max(r) - min(r)) / median_se ≥ 4.0` and `max_cv ≤ 0.15`), folded-normal bias vanishes. Round 110 pre-specifies and validates `W2` across `G ∈ {4, 6}`, `CV ∈ {0.05, 0.15}`, `SNR ∈ {4.0, 8.0}`.
3. **Manifest & routing parity:** Add `joinpoint` (Round 77/109) and `demography` (Round 101 Chiang II `e0`/`e65`) to `census/manifest/methods.py` (22 → **24 manifest methods**), and expand `docs/agent_routing.md` / `tests/test_agent_routing.py` to **40 offline-tested rows (`R1–R40`)**.

---

## 2. Deliverables

1. **Frozen criterion, core & harness:** `docs/audits/repairs110_criterion.md`, `census/repairs110_core.py`, `scripts/repairs110_validation.py`.
2. **Validation audit:** `docs/audits/repairs110_validation.md` and `docs/audits/repairs110_validation.json`.
3. **Wire passing repairs only:**
   - `S3` → `census/staggered.py` (`SYNTHETIC_CONFORMAL_VALIDATED = True`, `SYNTHETIC_MIN_PRE = 15`, `SYNTHETIC_MIN_DONORS = 25`; `conformal_validated` flag on `synthetic_control` while keeping `validated` for placebo test conservative).
   - `W2` → `census/inequality_monitoring.py` (`MD_SNR_VALIDATED`, `MD_MIN_SNR = 4.0`, `MD_MAX_CV = 0.15`; `mdm_w`/`mdb_w` validated when `snr >= 4.0` and `max_cv <= 0.15`).
4. **Manifest & routing parity:** `joinpoint` and `demography` in `census/manifest/methods.py`, plus `R38–R40` in `docs/agent_routing.md` and `tests/test_agent_routing.py`.
5. **Tests, docs & verification:** `tests/test_round110.py`, `docs/audits/round110_compatibility.md`, `docs/agent_protocol.md` + `scripts/sync_rule_text.py`, `STATUS.md`, `CHANGELOG.md`, `ROADMAP_BACKLOG.md`, version `0.106.0`, pytest + `run_golden.py` check.
