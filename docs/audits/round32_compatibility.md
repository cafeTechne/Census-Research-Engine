# Round 32 compatibility and acceptance

Author self-review, not independent; implemented by the maintainer agent at the owner's request.
Worktree `/tmp/census-round32`, branch `phase32/pums-tests`, based on defaultBranch `5f094be`.
No WONDER access; no private-checkout edits; no GitHub CI.

## Frozen validation

Procedures (`census/pums_tests.py`), script, criterion and the 2,000,000-household reference
targets were committed and pushed at `d65d034` before the full run; one smoke run (10 draws per
cell) wrote no files. The full run used exactly 2,000 draws in each of 8 cells.

| Procedure | Result |
| :--- | :--- |
| T0 Pearson (design-blind) | Failed as expected: size .126–.535 |
| T1 first-order Rao–Scott | Passed 2 × 2 (.097–.115) and 3 × 4 (.099–.114); **selected** |
| T2 second-order Rao–Scott | Passed both tables |
| T3 design Wald F | Passed 2 × 2; failed 3 × 4 (up to .147) |
| M1 z / M2 t(80) / M3 design F | All passed; M1 and M3 selected |
| I1–I5 differences, OR, RR, mean and median differences | All passed (coverage .877–.913) |
| P1 Wald proportion | Failed (.848 in one cell) |
| P2 Korn–Graubard | Passed (.902–.947); **selected** |

## Engine

- `census/pums_tests.py` is unchanged since the criterion commit (its `VALIDATED` placeholder is not
  used). Validation status lives in `census/pums_inference.py` (fixed constants, tested against
  the audit JSON).
- New MCP tool `test_association` (full and core; core cap now 16), recipe `pums_tests`, rule text
  in `docs/agent_protocol.md`, the MCP instructions and the core profile.
- **Found by the example and added after the run:** medians of heaped values (reported dollar
  amounts at round numbers) can have identical replicate medians, so the SDR SE is 0. The
  validation used continuous values. `compare_medians` now reports `heaping_share` (weight exactly
  at a group's median) and labels the result exploratory when it exceeds 2% or the SE is 0.
- No manifest change.

## Goldens and suite

Both goldens byte-identical to v0.28.0 (no manifest or model-path change). Suite: see STATUS
(Round 32).
