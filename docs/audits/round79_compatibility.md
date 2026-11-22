# Round 79 compatibility and acceptance

Author self-review, not independent. Worktree `/tmp/census-round79`, branch `phase79/decomposition`; defaultBranch
(Rounds 76–78) merged in so the criterion commit `9e52bb4` (tag `criterion-r79`) stays an ancestor. Version 0.75.0.

## Behaviour changes

- New full-profile tool `decompose_gap` (74 tools); CLI `python -m census tool decompose_gap`.
- New library modules `census/decomposition.py` and `census/decomposition_core.py`. No manifest change; goldens
  expected byte-identical.

## Exceptions

1. **A new tool rather than `test_association(kind="decomposition")`**, as the plan allowed: the decomposition
   needs two group conditions, covariate and categorical lists and a model, which do not fit `test_association`'s
   flat parameters.
2. **Fairlie orderings:** validation used 10 per draw (conservative, stated in the criterion); the engine uses 100.
3. **Size gate** on the smaller group's unweighted record count (the criterion named group B, the smaller group in
   the design).
4. **Group definitions** are two PUMS conditions checked for overlap; Round 76 has no reusable PUMS group helper.
5. **No design-blind comparison interval** is offered (the plan listed it as exploratory only).
