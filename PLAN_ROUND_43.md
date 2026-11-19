# Round 43 plan: manifest routing and housekeeping

**Goal.** No new statistics. Make methods already validated in Rounds 33, 35 and 39 usable from
pre-registered manifests as **opt-in** arguments, fix the saturated-model bundle crash, and shrink the
agent-facing text that Rounds 31–42 grew. Source: `ROADMAP_BACKLOG.md` (issues N1–N4; STATUS backlog
items 1–3 and 7).

Version 0.40.0. Baseline: 1977 passed, 37 skipped (v0.39.0). Branch `phase43/routing-housekeeping`,
worktree `/tmp/census-round43`. Commits carry `[skip ci]`; no AI attribution.

## 0. Invariants

- Registered manifests in `examples/manifests/` are byte-fixed and their outputs must not change:
  `scripts/refactor_golden.py` and `scripts/run_golden.py` stay **byte-identical** to v0.39.0. New
  options are tested with new test manifests under `tests/`, not by editing registered ones.
- Every new manifest option is refused by `validate` outside its validated range (same wording style
  as the existing `spatial_clusters` refusals), unless the manifest is `exploratory: true`.
- Rule text changes go to `docs/agent_protocol.md`, `mcp_server.py` INSTRUCTIONS, `census/mcp_profiles.py`
  and the affected `docs/recipes/` together.

## 1. Manifest routing (`census/manifest/methods.py`, `schema.py`, `methods_text.py`)

| ID | Method | New argument | Routes to | Validated range (refuse outside) |
| :--- | :--- | :--- | :--- | :--- |
| M1 | `correlation_matrix` | `interval: "validated"` (default `"fisher"`, today's behaviour) | `correlation.validated_correlations` with `VALIDATED_VARIANT` | Spearman/Kendall variant 1, Pearson/partial variant 2; partial with one control; non-spatial only (R33: all intervals fail under spatial dependence, so add a methods-text caveat) |
| M2 | `fit_replicate` | `model: "negbin"` with `exposure` | `count_models.fit_count_model(family="negbin")` (NB2-HC3) | no `spatial_clusters`, `spatial_se` or `weights` (not validated; Round 45 may add clusters) |
| M3 | `fit_eiv` | `spatial: "clusters"` (G1) or `"error"` (G2) | `spatial_eiv.fit_spatial_eiv` | ≤ 2 error-prone covariates; linear only; mutually exclusive with `spatial_se`; G1 needs every non-constant term to vary within clusters (the engine already refuses partial constancy) |

- M1 statistic: `correlation` hypotheses read the validated row's estimate, interval and p-value;
  `se_basis` records the variant (`"r33_variant_1"` etc.). Rows labelled exploratory by
  `validated_correlations` make a confirmatory hypothesis fail validation.
- M2/M3 results must be wrapped as `census.results.ModelResult` (coefficients table with `term`,
  `estimate`, the SE column `interval_se_column` reports, `p_value`, `ci_lower`, `ci_upper`; `notes`;
  `diagnostics`) so `_stat_coefficient`, `joint_test` refusals and the results bundle work unchanged.
  `joint_test` on M2/M3 fits is refused (not validated).
- M2 keeps the existing WONDER handling in `_run_fit_replicate` (suppression notes and deviations,
  fixed-exposure note): the NB2 branch must go through the same post-processing.
- `methods_text.py`: one sentence per option with its audit citation
  (`rank_validation.md`, `manova_counts_validation.md`, `spatial_eiv_validation.md`) and the `references` keys it needs.
- `create_manifest` / `write_manifest` default stays unchanged (no silent switch for new manifests);
  the recipe text recommends the new options instead.

## 2. Saturated-model bundle crash (STATUS backlog 7)

Reproduce first: a two-observation, two-coefficient OLS `fit_replicate` whose results bundle fails with
`ValueError: arange: cannot compute length`. Fix: keep estimable coefficients, set SE/interval/p-value
to missing with a note when residual df is 0, and skip or adapt plots that need finite intervals.
Regression test: the bundle completes, the table has the coefficients, and no SE, interval or p-value is
invented.

## 3. Housekeeping

- **H1 (core instructions budget).** `census.mcp_profiles.CORE_INSTRUCTIONS` is 12,480 characters
  (5,953 at v0.27.0). Rewrite items 10–23 (Rounds 31–42) into a compact form: one or two lines each
  naming the tool, what is validated, and "else exploratory; see get_recipe('<name>')", moving detail
  into the recipes (which already hold it). Target ≤ 8,000 characters. Add a test bounding
  `len(CORE_INSTRUCTIONS) <= 8000`. The full-profile `mcp_server.py` INSTRUCTIONS and
  `docs/agent_protocol.md` may stay detailed, but every validated/failed claim in the compact text must
  still match them (test: the set of tool names mentioned in the core text is a subset of the core
  profile's tools plus `get_recipe`).
- **H2 (tool counts).** Correct README and STATUS: 70 tools in the full profile, 16 in `core`, 17 in
  `core_spatial` (recount at the end of the round); fix the stale README tree line ("32 tools"). Add a
  test that derives the counts from the server and checks the numbers written in README and STATUS.
- **H3.** `workflows_inference.estimate_effect`: stop catching `AttributeError`; check the kind-specific
  arguments first (treatment needs `treatment` and `confounders`; iv needs `x` and `instrument`;
  mediation needs `x` and `mediator`) and return `INVALID_INPUT` naming the missing argument.
- **H4.** `missing_censored_its.impute_and_fit`: draw the imputations once and fit every term from the
  same completed data sets. `mci_core` is frozen: add a new engine-side helper rather than editing
  `mci_core.multiple_imputation`, and test that its results equal the current per-term path to 1e-12
  for a fixed seed.
- **H5.** `causal.iv_slope`: the corr < 0.3 weak-instrument cut-off was not validated (all validation
  cells had strong instruments). Keep the flag but change the note to say the cut-off is a convention
  pending Round 47, and report the first-stage F statistic alongside the correlation.

## 4. Tests (`tests/test_round43.py`)

M1–M3 each: a valid test manifest runs and its hypothesis statistic equals the direct library call; each
refusal in the table fires; `exploratory: true` lifts the refusal with a note. Plus the bundle
regression (section 2), H1 budget and tool-subset tests, H2 count test, H3 missing-argument messages,
H4 equality, H5 F statistic present.

## 5. Docs

STATUS (backlog items 1–3 and 7 updated or closed; round entry; tool counts), CHANGELOG 0.40.0,
version bump in `census/__init__.py`, `CITATION.cff` and `census/pipeline.py` `PACKAGE_VERSION`,
`docs/audits/round43_compatibility.md` (author self-review, not independent), recipes
`regression_sampling_error`, `rank_methods`, `external_health_outcome` and `preregistered` mention the
manifest options, `ROADMAP_BACKLOG.md` status column.

## 6. Acceptance

Both goldens byte-identical to v0.39.0; full suite 0 failures; `len(CORE_INSTRUCTIONS) <= 8000`; every
new option refused outside its validated range.

## 8. Status table

| Item | Status | Notes |
| :--- | :--- | :--- |
| M1 validated correlations in manifests | Done | Runner equals library; exploratory pairs refused. |
| M2 NB2 in manifests | Done | Also for external counts; R22 test assertion updated. |
| M3 spatial EIV in manifests | Done | G1/G2 equal the library. |
| Bundle crash fix | Done | Saturated fits: NaN SEs plus note; plot clamps non-finite whiskers. |
| H1–H5 | Done | Core text 3.9 K characters. |
| Goldens, final suite | Done | Goldens identical; 1993 passed, 37 skipped, 0 failures. |
| Exceptions | Recorded | No new validation needed (routing only). |
