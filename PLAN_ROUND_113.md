# Plan — Round 113: Domain-Gated Three-Level Variance-Share Validation (`G_top ≥ 49`) & Full-Suite Verification

**Version target:** `v0.109.0`  
**Branch:** `phase103/agent-access-hygiene` (uncommitted per owner instruction)  
**Ground rules:** validation first (criterion frozen before the full run); `run_golden.py` byte-identical; no automated WONDER access; no sub-national counts 1–9; no commit/merge/release without owner approval.

---

## 1. Motivation

In Round 112, three-level variance-share jackknife intervals (`M3b`) covered `.895–.925` across all 6 national-scale `G_top = 49` cells and missed only in one `G_top = 30` cell (`.850`). National US three-level studies (tracts in counties in states, e.g., Boing et al. 2020) operate at `G_top = 49–51`. Round 113 pre-specifies and validates `M3c` explicitly on the national state-level domain (`G_top ∈ {49, 51}`) so `census/multilevel3.py` can gate variance-share intervals as **validated when `n_top ≥ 49`** and **exploratory below 49**, while keeping `woolf` (RR homogeneity) and `prob50` (designation PPV) excluded from confirmatory manifests and PPV intervals.

---

## 2. Deliverables

1. `docs/audits/repairs113_criterion.md`, `scripts/repairs113_validation.py`, `docs/audits/repairs113_validation.md`, and `docs/audits/repairs113_validation.json`.
2. Wire `SHARES_MIN_TOP = 49` and `SHARES_VALIDATED_FROM_49 = True` into `census/multilevel3.py` (keeping `SHARES_VALIDATED = False` for the broad un-gated constant so existing Round 73 tests remain intact, and setting per-result `share_intervals_validated = bool(G >= 49)`).
3. `tests/test_round113.py`, `docs/audits/round113_compatibility.md`, `docs/agent_protocol.md` + `scripts/sync_rule_text.py`, `STATUS.md`, `CHANGELOG.md`, `ROADMAP_BACKLOG.md`, version `0.109.0`.
4. Full-repository `pytest` run across all ~2,460+ tests + `run_golden.py` byte-identical verification.
