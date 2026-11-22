# Round 86 compatibility and acceptance

Author self-review, not independent. Worktree `/tmp/census-round86`, branch `phase86/bias-analysis`; defaultBranch
(Rounds 82–85) merged in, so the criterion commit `734cce5` (tag `criterion-r86`) stays an ancestor. Version 0.82.0.

## Behaviour changes

- New full-profile tool `bias_analysis` (78 tools); CLI `python -m census tool bias_analysis`.
- `stratified_analysis` pooled RR/OR and the marginal-measure outputs gain an `e_value` field.
- `reporting` recipe section; protocol rule text. No manifest change; goldens expected byte-identical.

## Exceptions

1. **No `sensitivity_analyses` manifest block**: the probabilistic analysis it would register failed validation;
   E-values need no registration. Left for a later round with a repaired interval.
2. **E-value fixtures**: the EValue R package was not available; the published VanderWeele and Ding example and the
   formula identities are the checks.
3. **PUMS two_by_two** does not gain an E-value field yet (its output builder is shared with Round 32's validated
   tables); use `bias_analysis(kind="e_value")` on its risk ratio.
4. **Example priors are illustrative**, not from a validation study (labelled in the example).
