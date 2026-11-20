# Round 59 compatibility and acceptance

Author self-review, not independent; implemented by the maintainer agent at the owner's request.
Worktree `/tmp/census-round59`, branch `phase59/spatial-correlations`, based on defaultBranch `721358e`.

## Frozen validation (criterion `669a506`, pushed with the OH/PA targets before the full run; 2,000 draws per cell, 24 cells)

| Problem | Procedure | Coverage (lowest–highest) | Outcome |
| :--- | :--- | :--- | :--- |
| P (MI/NY) + O (OH/PA) | P1 partial, effective n of the residual series | .869–.971 | pass |
| P (MI/NY) | P0 independent-area partial (comparison) | .689–.970 | fails under spatial dependence |
| O (OH/PA) | C1 Spearman / Kendall / Pearson | .891–.918 / .880–.905 / .889–.965 | all pass: Round 48 replicates on OH/PA |
| A (OH/PA) | A3 effective-n α | .901–.933 | pass: replicates on OH/PA |

No failed fits. The OH/PA targets were recomputed with Round 33/36's procedures. Before freezing, the
geometry-aware setup was checked to reproduce Round 33/36's MI/NY setup exactly.

## Engine

- New `census/partial_neff_core.py` (frozen).
- `census/small_spatial.py`: `NEFF_CORRELATION_VALIDATED["partial"] = True`, `OHPA_REPLICATED`.
- `census/correlation.py`: `validated_correlations(method="partial", coords=...)` uses `partial_neff` and is
  validated with one control and replicates. Before this round it returned an exploratory label.
- MCP `correlation_matrix(spatial=True)` therefore covers partial correlations.
- Rule text mirrored: `docs/agent_protocol.md`, MCP core item 10, `docs/recipes/rank_methods.md`,
  `docs/recipes/composite_index.md`.

## Behaviour change

Spatial partial correlations with one control and replicates are now validated rows with an n_eff column,
instead of exploratory rows without a spatial correction.

## Acceptance

- Schema and run goldens: byte-identical.
- New tests: `tests/test_round59.py` (5).
- Full suite: 2117 passed, 37 skipped; 0 failures.
