# Plan — Round 203: Wire Multi-Component BYM2 & Confounding Screen into Layer A Workflows (`v0.199.0`)

## 1. Strategic Objective
Expose Round 200's `allow_disconnected=True` multi-component BYM2 directly through `census/workflows_geo.py:spatial_model` (skipping artificial `_bridge_components` when `allow_disconnected=True`) and export `confounding_adjustment_screen` cleanly from `census/__init__.py` so Python/CLI/agent callers have first-class access.

## 2. Exact File Contracts
1. `census/workflows_geo.py`: Add `allow_disconnected: bool = False` to `spatial_model()`.
2. `census/__init__.py`: Export `confounding_adjustment_screen` and `lint_latex` / `compile_latex_pdf`.
3. `tests/test_round203.py` & `docs/audits/round203_compatibility.md`.

## 3. Iteration Log
- *2026-11-27:* Plan drafted and implemented as Batch 1 of the unattended pure-engine sprint.
