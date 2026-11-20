# Round 60 compatibility and acceptance

Author self-review, not independent; implemented by the maintainer agent at the owner's request.
Worktree `/tmp/census-round60`, branch `phase60/inequality-repairs`, based on defaultBranch `e591fc7`.

## Frozen validation (criterion `60a3b06`, pushed before the full run; 2,000 draws per cell, 8 cells)

| Measure (incomes) | T0 normal (comparison) | T1 transformed | T2 bias-corrected + transformed | Outcome |
| :--- | :--- | :--- | :--- | :--- |
| Atkinson 1 (I1, I2) | .869–.893 | .872–.893 | .860–.885 | T1 validated |
| Atkinson .5 (I1, I2) | .847–.894 | .846–.892 (≥ .871 at 3,000 households) | .841–.882 | T1 with a 7,000-record gate |
| Top-decile share (I1–I3) | .845–.901 | .847–.901 (≥ .872 at 3,000 households) | .846–.892 | T1 with a 7,000-record gate |
| Theil T (I1, I2) | .816–.889 | .820–.889 (I2 at 3,000 households .8595) | .819–.882 | fails |

No failed draws. The SDR bias correction lowered coverage everywhere, so T2 was never chosen. With fresh seeds,
Round 56's normal interval (T0) for Atkinson 1 stayed above .86; Round 56 had .858.

## Engine

- `census/pums_inequality_core.py`: `TRANSFORM`, `transformed_summary`, `bias_corrected` (frozen).
- `census/pums_inequality.py`: `REPAIRED` (measure → record gate). Repaired measures use the logit interval and
  are validated subject to the gate. A new `interval` column names the method.
- Rule text mirrored: `docs/agent_protocol.md`, `mcp_server.py`, MCP core item 10, `docs/recipes/pums_tests.md`,
  the `test_association` docstring.

## Acceptance

- Schema and run goldens: byte-identical.
- New tests: `tests/test_round60.py` (4).
- Full suite: 2121 passed, 37 skipped; 0 failures.
