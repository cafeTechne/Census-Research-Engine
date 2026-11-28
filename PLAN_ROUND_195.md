# Plan — Round 195: Flagship Manuscript Neural Claim-Grounding Audit, Routing `R92–R94` & `v0.191.0` Hygiene Sync

## 1. Strategic Objective
Run `layer_b_openscholar.claim_grounder` with `BAAI/bge-small-en-v1.5` via `venv-neural` on the live Samsung 850 EVO SSD corpus against 5 core empirical claims from the Round 188 flagship manuscript (`docs/audits/r195_manuscript_claim_grounding.md`), expand `docs/agent_routing.md` with `R92–R94` (**94** rows total), extend `scripts/release_hygiene_check.py` through Round 195, and sync version `0.191.0`.

## 2. Exact File Contracts
1. `docs/audits/r195_manuscript_claim_grounding.md`: Live neural grounding audit for 5 flagship manuscript claims.
2. `docs/agent_routing.md`: Append `R92–R94` (94 rows total).
3. `scripts/release_hygiene_check.py`: Extend audit check through Round 195 (`range(126, 196)`).
4. Version sync `0.191.0`: `census/__init__.py`, `census/pipeline.py`, `CITATION.cff`, `CHANGELOG.md`, `STATUS.md`.
5. `tests/test_round195.py` & `docs/audits/round195_compatibility.md`.

## 3. Acceptance Gates
1. `docs/audits/r195_manuscript_claim_grounding.md` generated with `neural_active` / `BAAI/bge-small-en-v1.5`.
2. `scripts/release_hygiene_check.py` exits `0` with `"ok": true`, `"version": "0.191.0"`.
3. `pytest -q tests/test_round190.py tests/test_round191.py tests/test_round192.py tests/test_round193.py tests/test_round194.py tests/test_round195.py tests/test_agent_routing.py layer_b_openscholar/tests/` passes with 0 failures.

## 4. Iteration Log
- *2026-11-27:* Plan drafted.
- *2026-11-27:* Ran live SSD `BAAI/bge-small-en-v1.5` claim-grounding audit on 5 flagship manuscript claims (`docs/audits/r195_manuscript_claim_grounding.md`), expanded `docs/agent_routing.md` (`R92–R94`, 94 rows), extended `scripts/release_hygiene_check.py` through Round 195, and synced version `0.191.0`.
