# Plan — Round 206: Multi-Component & Island BYM2 Finite-Sample Simulation Calibration (`v0.202.0`)

## 1. Strategic Objective
Empirically calibrate the multi-component & island-aware BYM2 (`allow_disconnected=True`, Round 200 / N132) estimator in `census/simulation_multicomponent_bym2.py` across a 4-component graph (two 4×4 lattices + 2 isolated islands, 34 areas) measuring 90% CI coverage on connected components vs. isolated islands, exceedance calibration, and RMSE reduction over raw SMRs.

## 2. Exact File Contracts
1. `census/simulation_multicomponent_bym2.py`: `build_multicomponent_graph()`, `run_multicomponent_bym2_calibration(n_draws=30, seed=206)`.
2. `tests/test_round206.py` & `docs/audits/round206_compatibility.md`.
3. Version sync `0.202.0` + `scripts/release_hygiene_check.py` through Round 206.

## 3. Iteration Log
- *2026-11-27 (Cron #1):* Plan drafted and implemented strictly inside the sandbox.
