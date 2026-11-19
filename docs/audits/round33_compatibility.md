# Round 33 compatibility and acceptance

Author self-review, not independent; implemented by the maintainer agent at the owner's request.
Worktree `/tmp/census-round33`, branch `phase33/rank-methods`, based on defaultBranch `a441487`.

## Frozen validation

`census/rank_methods.py`, the script, criterion and 400,000-area targets were committed and pushed at
`f660e9c` before the full run (one smoke run, 5 draws per cell, wrote no files). Before freezing, the
plan's Kendall interval was corrected to the Fieller–Hartley–Pearson form, 0.437/(n − 4).

| Procedure | Independent cells | Outcome |
| :--- | :--- | :--- |
| Pearson v1 / v2 | .842–.904 / .892–.965 | v1 failed; v2 selected |
| Spearman v1 | .899–.916 | selected |
| Kendall v1 | .893–.905 | selected |
| Partial v1 / v2 | .858–.905 / .903–.968 | v1 failed; v2 selected |
| Brunner–Munzel B1 | .897–.905 (size .096–.103) | selected |
| Kruskal–Wallis size | .095–.106 | passed |

Spatial (100 km) cells: correlation coverage .60–.89 for every variant (informational).

## Engine

New `census/rank_methods.py` (frozen), `correlation.validated_correlations` (a separate function, so
`correlation_matrix`, manifests and both goldens are unchanged), `compare_groups(method="rank")`,
`census/diagnostics.py`, `fit_replicate` joint inputs now carry GEOIDs (not serialized), MCP
correlation tool methods `kendall`/`partial` with `controls` and `validated_intervals`, recipe
`rank_methods`, mirrored rule text.

## Goldens and suite

See STATUS (Round 33).
