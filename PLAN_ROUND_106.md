# Round 106 plan: third wave of exploratory-measure repairs (validation-first)

**Goal.** Diagnose and repair five remaining exploratory failures from Rounds 37, 83, 85, 87 and 91 (backlog
N94–N98), each with a concrete statistical fix evaluated **validation-first** (90% coverage ≥ .86; nominal-.10
size ≤ .13). Only candidates passing the fixed criterion are wired into the engine. Version 0.102.0. Both
manifest goldens stay byte-identical.

## 1. Five diagnosed defects and repair candidates (`census/repairs106_core.py`)

1. **PUMS replicate Wald homogeneity under per-measure nulls (Round 83/105; N94):**
   - *Diagnosis:* Round 105's `H2b` (Korn–Graubard Hotelling `F(K - 1, R - K + 1)`) already passed for RR
     (`.102–.126`) and OR (`.104–.129`), while RD failed only because the Round 105 DGP held RR constant across
     varying baseline risks (making RD non-null).
   - *Repair (`H2c`):* verify Hotelling `F(K - 1, R - K + 1)` under separate exact nulls for each measure
     (constant RR, constant OR, constant RD).
2. **Designation PPV predictive interval with rule re-selection (Round 85/105; N95):**
   - *Diagnosis:* Round 105's `Q2b` lifted `prob80` to `.963–.975` but left `point` at `.843–.858` because it held
     the designated set `S` fixed across bootstrap draws, omitting winner's-curse selection variance.
   - *Repair (`Q2c`):* re-apply `S_b = designate(rule, p_b, n, t, P=Pb)` inside every parametric bootstrap draw.
3. **Ecologic / between-area slope with many small areas (Round 87, `ecologic_validation.md`; N96):**
   - *Diagnosis:* With 150 small areas, sample area means `xbar_j` carry within-area sampling variance `s²_j / n_j`,
     attenuating the between-area and ecologic slopes (`.62–.86`).
   - *Repair (`E3`):* Croon / Fuller reliability-corrected between-area slope (`Cov(ybar, xbar) / max(Var(xbar) -
     mean(v_xbar), eps)`) with delete-one-area / SDR replicate intervals.
4. **Lin's concordance correlation coefficient interval (Round 37, `agreement_validation.md`; N97):**
   - *Diagnosis:* Observed Lin's CCC missed `.86` by `0.001` (`.859`) under normal-theory SE.
   - *Repair (`C2`):* delete-one-area jackknife on Fisher-z transformed CCC with `t(n - 2)` critical value.
5. **Annual policy panels with treatment-confounder feedback: parametric g-formula (Round 91/104/105; N98):**
   - *Diagnosis:* Pure IPW (`M1`–`M4`) suffers rare-event weight instability on 51 states, leaving `+0.09` bias
     at duration 1 even with Firth-penalized logit.
   - *Repair (`M5`):* Hernán & Robins (2020) chapter 21 **parametric g-formula** (sequential outcome model
     `Y_t ~ year + A_t + L_t + L_{t-1}` + confounder transition model `L_t ~ L_{t-1} + A_{t-1}`, recursively
     predicting counterfactual durations 1..3 vs never-treated) with delete-one-unit cluster jackknife `t(G - 1)`.

## 2. Validation (`scripts/repairs106_validation.py`, `docs/audits/repairs106_criterion.md`)

- Fixed pass rule: 90% coverage ≥ `.86` in every cell (`H2c` nominal-.10 size ≤ `.13`).
- Write `docs/audits/repairs106_validation.md` and `.json` with frozen SHA-256 hashes.
- Wire only passing repairs into `census/stratified.py`, `census/designation.py`, `census/ecologic.py`,
  `census/agreement.py`, and `census/msm.py`.

## 3. Docs, tests and acceptance

- Update `docs/agent_protocol.md` → `mcp_server.py` (`sync_rule_text.py --check`), `STATUS.md`, `CHANGELOG.md`
  (0.102.0), `ROADMAP_BACKLOG.md` (N94–N98), `docs/audits/round106_compatibility.md`, `tests/test_round106.py`.
- Both goldens byte-identical; tests green.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| Frozen core, criterion, script | done | `repairs106_core.py`, `repairs106_criterion.md`, `repairs106_validation.py` |
| Simulation run & audit | done | `docs/audits/repairs106_validation.md` (62.3s; C2 & M5 pass; H2c/Q2c/E3 fail) |
| Wire passing repairs into engine | done | `agreement.py` (C2 Fisher-z jackknife), `msm.py` (M5 `method="gformula"`) |
| Docs, rule sync, tests, goldens | done | `sync_rule_text.py --check` green; `run_golden` byte-identical |
| Exceptions | none | see `docs/audits/round106_compatibility.md` |
