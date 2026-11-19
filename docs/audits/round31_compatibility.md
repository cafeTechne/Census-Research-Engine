# Round 31 compatibility and acceptance

Author self-review, not independent; implemented by the maintainer agent at the owner's
request (2026-11-18). Worktree `/tmp/census-round31`, branch `phase31/omnibus-groups`, based on
defaultBranch `a2da51c`. No WONDER access, no private-checkout edits (the owner's
`external_data` was symlinked into the worktree only for the golden runs and removed after), no
GitHub CI.

## Frozen validation

Candidates (`census/omnibus.py`), script and criterion were committed and pushed at `3e3094a`
before the full run; two smoke runs (4 and 20 draws per cell) wrote no files. One pre-freeze change
was made after the first smoke run: W4 cells where the engine refuses the design (a tested group
absent from a cluster) are reported as not applicable instead of counted as rejections, because
the engine never produces a p-value for them. The full run used exactly 2,000 null and 500
alternative draws in each of 36 cells.

| Procedure | Passed (model / family) | Failed |
| :--- | :--- | :--- |
| W0 χ² Wald (Round 27) | none | all (comparison row) |
| W1 F(q, n−p) | none | linear too conservative (.056–.070); GLM factor oversized (.12–.16) |
| W2 HC2 + HTZ F | none | as W1; GLM splines under-sized (.004–.024) |
| W3 wild score bootstrap | OLS factor (.098–.110); binomial and Poisson splines (.072–.103) | GLM factor (.108–.168); OLS splines (.065) |
| W4 IM-8 Hotelling | OLS factor; Poisson factor (.093–.103, applicable cells) | binomial (twoway fits fail); all splines (spatial cells .48–.65) |
| P1 Holm pairwise | OLS, binomial, Poisson (FWER .046–.117) | — |
| P2 simultaneous | OLS (FWER .067–.070) | binomial, Poisson (.12–.16) |

## Engine changes

- New `census/joint_tests.py` (selection flags fixed from the audit; tested by
  `test_validated_flags_equal_the_fixed_full_run`) and manifest statistic `joint_test`
  (`variable` or `term`, two-sided only). Confirmatory refusals (unvalidated model/family, fewer than
  145 areas, population target with replicates) are recorded as `hypothesis_not_tested` deviations.
- `census.splines.joint_wald` (χ²) is unchanged and stays exploratory, so existing results and both
  goldens keep their numbers.
- Confirmatory `cr` splines are allowed for binomial/Poisson `fit_replicate` analyses whose
  hypotheses are all `joint_test`; OLS splines remain refused.
- `fit_replicate` results carry `joint_inputs` (an attribute, not serialized).
- New `census/group_compare.py` and MCP tool `compare_groups` (full and core profiles; the core
  tool cap is now 15, per `ROADMAP_STATISTICS.md` section 4); recipe `group_comparison`.
- Deviation from the plan: `compare_groups` is not a separate manifest method. Manifests have no
  categorical variable source yet, so manifest group tests use `fit_replicate` with a group term
  in the formula and `joint_test` on that term.

## Goldens

- Execution golden (`scripts/run_golden.py`): byte-identical to v0.27.0.
- Schema golden (`scripts/refactor_golden.py`): the only change is the "supported statistics"
  message for `fit_replicate`, which now lists `joint_test` (84 changed lines, all that message).

## Suite

Baseline at v0.27.0: 1886 passed, 37 skipped. Final: 1908 passed, 37 skipped, 54 subtests; 0 failures
(22 new tests in `tests/test_round31.py`).
