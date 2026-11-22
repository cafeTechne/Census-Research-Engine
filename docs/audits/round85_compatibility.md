# Round 85 compatibility and acceptance

Author self-review, not independent. Worktree `/tmp/census-round85`, branch `phase85/designation`; defaultBranch
(Rounds 82–84) merged in, so the criterion commit `61fa47a` (tag `criterion-r85`) stays an ancestor. Version 0.81.0.

## Behaviour changes

- New full-profile tool `designation_accuracy` (77 tools); CLI `python -m census tool designation_accuracy`.
- `small_area` recipe section; protocol rule text. No manifest change; goldens expected byte-identical.

## Exceptions

1. **Rule accuracy is exploratory** although the expected values agreed with the realized values within about .01
   on average: the pre-set criterion also required the PPV predictive interval to cover (it ignored the shared
   Fay–Herriot parameter uncertainty and under-covered on tracts). The tool reports expected values without that
   interval.
2. **Q3 (top-k overlap)** is reported in the audit only; the tool does not offer rank designations.
3. **The direct probability** is shown in a separate column labelled exploratory, for comparison only.
