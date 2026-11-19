# Round 43 compatibility and acceptance

Author self-review, not independent; implemented by the maintainer agent at the owner's request.
Worktree `/tmp/census-round43`, branch `phase43/routing-housekeeping`, based on defaultBranch `5756709`.
No new statistics and no simulation: every routed method keeps the validation it already had.

| Item | Change | Validation it relies on |
| :--- | :--- | :--- |
| M1 | `correlation_matrix` `args.interval: "validated"` → `correlation.validated_correlations`; p-value from the atanh-scale interval; exploratory pairs refused in confirmatory runs | Round 33, `rank_validation.md` |
| M2 | `fit_replicate` `args.model: "negbin"` → `count_models.fit_count_model` (NB2-HC3), population target; WONDER suppression handling unchanged | Round 39, `manova_counts_validation.md` |
| M3 | `fit_eiv` `args.spatial: "clusters" \| "error"` → `spatial_eiv.fit_spatial_eiv` (G1/G2); > 2 error-prone covariates refused in confirmatory runs | Round 35, `spatial_eiv_validation.md` |
| Bundle | Saturated `fit_replicate`: NaN model SEs/intervals/p-values plus a note; coefficient plot clamps non-finite whiskers | STATUS backlog 7 |
| H1 | Core instructions 12,480 → under 4,000 characters; test bound 8,000; non-core tools marked `[full]` | — |
| H2 | Tool counts: 70 full, 16 core, 17 core_spatial (README, STATUS, `docs/local_models.md`), tested | — |
| H3–H5 | `estimate_effect` argument checks; single imputation loop (equal to the frozen per-term path to 1e-12); first-stage F | — |

Each manifest runner equals the direct library call (tests). The new methods-text sentences appear
only when the option is used, so registered manifests' methods text is unchanged.

## Goldens and suite

Both goldens byte-identical to v0.39.0. Suite: 1993 passed, 37 skipped, 63 subtests; 0 failures
(baseline 1977; 16 new tests). One older assertion was updated on purpose: `tests/test_round22.py`
expected `negbin` to be refused for external count outcomes ("not validated", true before Round 39); it
now checks that `negbin` is accepted but still needs the exposure.
