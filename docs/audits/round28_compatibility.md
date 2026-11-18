# Round 28 compatibility review

Author self-review, not independent. Base: completed Round 27 commit `22a4c96`.
Round 28 is stacked on `phase27/eb-splines` because Round 27 has not merged into
`defaultBranch`. This is the plan's section 0.6 exception; no merge was performed.

Both golden tools ran before and after implementation, without changing their
normalization rules. The snapshot files are in `/tmp/r28-*`.

- `scripts/refactor_golden.py`: 516 snapshots from 12 manifests. The only changes
  are 50 supported-method string occurrences for invalid `no_such_method` analyses.
  `segregation` appears between `regression_calibration` and `simex`. These are the
  validate/create errors for `analyses[0]`, `[1]` or `[2]`; no other schema changes.
- `scripts/run_golden.py`: byte-identical output, 29 scenarios covering all 19
  blocking deviation kinds. Existing scientific values, diagnostics, methods
  text, artifact digests, source/manifest hashes and failure behavior are intact.
  No new example manifest was needed or registered manifest changed.

The optional SMR fields and conditional methods-text renderer live in MethodSpec
metadata, so adding segregation did not introduce method-specific branches into
execution. Its declared group columns participate in common availability checks.
The generic one-sided test step accepts a centered test estimate: new index tests
use estimate-null, while all older hypotheses retain their original behavior.

Independent tests cover the index definitions, the fixed replicate correction,
shared-county contrast covariance, independent-release variance, common-reference
pooling covariance, period units, fixed-E exact-limit invariance, hash/optional-field
behavior, validation gates, undefined groups and strict replicate failure paths.
Frozen validation kernels agree with production calculations. The source/criterion
commits were pushed before their full simulations; their bytes were not retuned.
Computational agreement does not add new coverage claims for contrasts, multigroup
H, high-CV counts or uncertain reference denominators.
