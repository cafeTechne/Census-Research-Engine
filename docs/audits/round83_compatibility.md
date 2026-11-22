# Round 83 compatibility and acceptance

Author self-review, not independent. Worktree `/tmp/census-round83`, branch `phase83/stratified`, based on
defaultBranch after Round 82. Version 0.79.0.

## Behaviour changes

- New full-profile tool `stratified_analysis` (76 tools); CLI `python -m census tool stratified_analysis`.
- New recipe `confounding` (26 recipes); the core `get_recipe` description names it (693 of 700 characters).
- Manifest validation gains the optional `covariables` block (`census/manifest/covariables.py`). Registered
  manifests do not use it, so goldens are expected byte-identical.

## Exceptions

1. **Recipe name** `confounding` instead of `confounding_and_effect_modification` (the core description budget).
2. **Effect modifiers in manifests** are checked (they must enter through an interaction), but stratum-specific
   hypotheses are not generated automatically: hypotheses name the interaction coefficient or a stratified analysis.
3. **No WONDER county-by-age example**: the owner's exports have no county x age deaths. The PUMS example ran.
4. **Homogeneity tests:** the Woolf RR test and the PUMS replicate Wald test failed their size criterion; they are
   reported with `validated: false`, and labels resting on them are exploratory. No gate was pre-stated for tests.
