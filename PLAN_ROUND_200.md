# Plan — Round 200 (N132): Multi-Component & Island-Aware BYM2 Spatial Disease Mapping (`v0.196.0`)

## 1. Strategic Objective
Extend `census/disease_mapping_core.py` and `census/disease_mapping.py` to support disconnected neighbour graphs (multiple connected components and isolated island counties, such as 50-state+DC national maps with AK/HI/islands or states with island counties) via per-component ICAR scaling (Freni-Sterrantino et al. 2018; Riebler et al. 2016) under opt-in `allow_disconnected=True`, keeping single-component behavior bit-for-bit identical and flagging multi-component fits as exploratory per engine validation rules.

## 2. Exact File Contracts
1. `census/disease_mapping_core.py`: Add `graph_components(n, edges)` and `allow_disconnected: bool = False` on `scaled_icar_eigen()`.
2. `census/disease_mapping.py`: Add `allow_disconnected: bool = False` on `disease_map()`, returning `n_components` and `n_islands`.
3. `tests/test_round200.py` & `docs/audits/round200_compatibility.md`.

## 3. Iteration Log
- *2026-11-27:* Plan drafted and implemented from roadmap item `N132`.
