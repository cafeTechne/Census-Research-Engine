# Round 45 compatibility and acceptance

Author self-review, not independent; implemented by the maintainer agent at the owner's request.
Worktree `/tmp/census-round45`, branch `phase45/count-repairs`, based on defaultBranch `0277372`.

## Frozen validation (criterion `0c368dd`, pushed before the full run; 2,000 draws per cell)

| Procedure | Coverage | Outcome |
| :--- | :--- | :--- |
| K1a interval-censored NB2 | .8690–.8980 | Passed |
| K1b censored Poisson (Round 42) | .8265–.8625 | comparison |
| K1c complete-case NB2-HC3 | .8305–.8775 | comparison |
| K2a IM-8 NB2 (full-sample α) | .8955–.9090 | Passed |
| K2b IM-8 Poisson | .8940–.9045 | Passed |
| K2c pooled NB2-HC3 | .7950–.8840 | comparison (fails with spatial correlation) |
| K3a NB2-HC3, noisy exposure fixed | .8875–.8910 | Passed |
| K3b Poisson HC3, noisy exposure fixed | .8325–.8550 | comparison |

## Engine

`census/count_repairs_core.py` (frozen); `missing_censored_its.fit_censored_negbin`;
`count_models.fit_count_model(spatial="clusters", coords, within_states)` with `SPATIAL_VALIDATED`; MCP
`fit_model(model="negbin", spatial="clusters")`; `spatial_clusters.within_state_points` and the
`within_states` option of `assignment_for_frame`, `spatial_clusters` and `fit_spatial_eiv` (default off:
existing assignments unchanged). Rule text mirrored; recipe `external_health_outcome`. Exploratory example
`docs/studies/r45_count_example.md` (coefficients only; WONDER audit passed). No manifest change.

## Goldens and suite

See STATUS (Round 45).
