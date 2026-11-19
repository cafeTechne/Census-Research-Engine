# Round 36 compatibility and acceptance

Author self-review, not independent; implemented by the maintainer agent at the owner's request.
Worktree `/tmp/census-round36`, branch `phase36/composite-index`, based on defaultBranch `9a378fb`.

## Frozen validation

`census/index_core.py`, script, criterion and α targets committed and pushed at `e86907d` before the
full run (one smoke run, 10 draws per cell, no files); 2,000 draws in each of 8 cells.

| Procedure | Result |
| :--- | :--- |
| S1 score intervals, PCA weights | Passed: mean .898, every area ≥ .879 |
| S1 score intervals, equal weights | Passed: mean .898–.899, every area ≥ .874 |
| A1 Feldt α interval (selected) | Passed in independent cells (.891–.912); spatial cells .58–.67 |
| A2 Feldt + replicate variance | Passed in independent cells (.934–.977) |

## Engine

`census/composite_index.py` (`build_index`), MCP tool `build_index` (full profile), recipe
`composite_index`, mirrored rule text. No manifest change.

## Goldens and suite

See STATUS (Round 36).
