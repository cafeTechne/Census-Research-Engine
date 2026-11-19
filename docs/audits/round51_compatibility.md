# Round 51 compatibility and acceptance

Author self-review, not independent; implemented by the maintainer agent at the owner's request.
Worktree `/tmp/census-round51`, branch `phase51/negative-replicates`, based on defaultBranch `dbad2ab`.

## Frozen validation (criterion `2837bfb`, pushed before the full run; 2,000 draws per cell)

The criterion commit also froze the SMR policy argument in `census/standardize.py` (default `"refuse"`
during the run). An accidentally tracked `.venv` symlink was untracked in the next commit (`e236fee`); it is
not a pinned file.

**A. Segregation, clipped replicates.** Round 50's design with Gaussian replicates (about 4% of populated
tract-group cells in the two-group design and 2.6% in the three-group design had a negative replicate).

| Variant | Clipped validated range | Affected county-draws: coverage (ρ 0; ρ −.3) | Clip validated |
| :--- | :--- | :--- | :--- |
| D bias-corrected | to .50 | .9040; .9060 | to .50 |
| Isolation bias-corrected | to .50 | .9029; .9072 | to .50 |
| H bias-corrected | to .50 | .9645; .9666 | to .50 |
| Three-group H bias-corrected | to .50 | .9880; .9907 | to .50 |
| Isolation naive | to .30 | .8478; .8481 | failed |
| H naive | to .30 | .8606; .8512 | failed |
| D naive, three-group H naive | none | — | failed (as in Round 50) |

**B. SMR, negative band replicates.** 33–73% of draws had a negative band replicate. Accept: .903–.922 in all
eight cells; clip: .891–.917. Both pass. No draw was refused.

## Engine

- `census/segregation.py`: `segregation_replicate(..., negative_replicates=None)`, default `"clip"`
  (`DEFAULT_NEGATIVE_REPLICATES`); `"refuse"` keeps the strict policy. Clipped values feed only the index
  refits; count SEs, `max_count_cv` and `noise_level` use the unclipped replicates. New `CLIP_RANGES`
  (equal to the audit, tested) and a `clipped_replicates` column; a county with a clipped cell is validated
  only inside `CLIP_RANGES` (the Round 28 max-CV path does not apply to it).
- `census/standardize.py`: `indirect_standardize(..., negative_replicates=None)`, default `"accept"`
  (`SMR_NEGATIVE_REPLICATES_VALIDATED = {"accept": True, "clip": True}`). Every replicate expected count must
  still be positive.
- Manifests: `segregation` and `smr` pass `"refuse"` unless `args.negative_replicates` opts in (`"clip"`;
  `"accept"`/`"clip"` for SMR). Method text describes the opted-in policy.
- Rule text mirrored: `docs/agent_protocol.md`, `docs/recipes/segregation.md`,
  `docs/recipes/health_inequality.md`, MCP core item 13 and the full-profile text in `mcp_server.py` (which
  also still described the Round 28 defaults and gate; corrected).

## Behaviour changes

- Library calls that raised on negative replicate estimates now return results (segregation: clipped; SMR:
  used as published), with notes. Pass `negative_replicates="refuse"` for the old behaviour.
- Two older tests that asserted the library refusal now pass `"refuse"` explicitly (`tests/test_round28.py`,
  `tests/test_round24.py`); the SMR test also checks the new default.

## Acceptance

- Schema and run goldens: byte-identical to `dbad2ab`.
- New tests: `tests/test_round51.py` (8).
- Full suite: 2066 passed, 37 skipped; 0 failures.
