# Round 89 compatibility and acceptance

Author self-review, not independent. Worktree `/tmp/census-round89`, branch `phase89/causal-spec` (from Round 88).
Version 0.85.0. The checks are exact graph algorithms, so there was no simulation criterion.

## Behaviour changes

- **Manifest blocks** `causal_question` and `dag`. Without them, validation and methods text are unchanged, so
  registered manifests and goldens are byte-identical.
- **`estimate_effect`** gains `causal_question` and `dag`. **`difference_in_differences`** gains `causal_question`.
  Successful results gain `causal_assessment`, and the summary gains one sentence: either "Label: associational (no
  causal question specified)" or the specification problems.
- **`stratified_analysis`** results gain `classification_basis`, and `ROLE_NOTE` gains a sentence. The label values
  themselves are unchanged.

## Exceptions

1. **The plan's "confirmatory manifests refuse, exploratory manifests warn"** is implemented as validation errors
   for every manifest, since all are pre-registered, unless it carries `exploratory: true`. Those manifests get the
   findings in methods text.
2. **Round 83's label is not renamed.** Its values stay ("confounder", ...) for compatibility. The new
   `classification_basis` field and the note mark it associational.
3. **DiD takes no `dag`.** In DiD the design (parallel trends) handles confounding, not covariate adjustment. A DAG
   for time-varying confounders belongs with Round 91 (marginal structural models).

## Acceptance

- Goldens: run and schema snapshots byte-identical to Round 88.
- Full suite: 2313 passed, 42 skipped, 13 warnings, 72 subtests; 0 failures.
