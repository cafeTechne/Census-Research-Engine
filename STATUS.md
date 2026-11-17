# Project status

The single current summary of the Census Research Engine: what it does, which methods are validated, the
standing rules, and what is next. Read this instead of old plans. Updated each round when it merges.

**Current release:** v0.23.0 (Round 26: spatial-cluster inference; IM-8 validated). Previous: v0.22.1 (Round 25:
staged manifest execution; DOI 10.5281/zenodo.24297411). All versions: concept record
[zenodo.org/records/23925301](https://zenodo.org/records/23925301). Per-round detail: `CHANGELOG.md`.

**Round 27 implementation:** v0.24.0 on `phase27/eb-splines`, awaiting review/merge;
no tag or release. EB passed both fixed interval criteria; splines and joint Wald
failed and remain exploratory. Details below and in `PLAN_ROUND_27.md`.

## Where things are

| Path | What |
| :--- | :--- |
| `census/` | Library. `manifest/` package (pre-registered studies: `schema`, `validate`, `create`, `run` (typed `RunState` and ordered execution stages), `methods_text`, `methods` (single method registry), plus `adjustments`, `replicates`, `external`, `derivations`, `datasource`; import from `census.manifest`, but patch tests at the submodule that looks the name up), `models.py` (`fit_replicate`, `fit_eiv`, robust GLM SEs), `health_sources.py` (PLACES, USALEEP, CHR&R, WONDER exports), `spatial*.py`, `sae*.py`, `simulation*.py` (validation studies) |
| `mcp_server.py` | MCP server (63 tools; profiles in `census/mcp_profiles.py`) |
| `docs/agent_protocol.md`, `docs/recipes/` | What agents are told; keep in step with engine rules |
| `docs/audits/` | Validation reports (pass/fail, reproducible scripts in `scripts/`) |
| `docs/studies/` | Pre-registered study reports; outputs are release attachments, not in the repo |
| `examples/manifests/` | Registered manifests (their bytes are fixed once registered) |
| `PLAN_ROUND_<n>.md` | The current round and queued rounds (27–29). Implement only the lowest-numbered one. Merged plans are archived (below) |
| `docs/data/wonder_exports.md` | Owner's guide to manual CDC WONDER exports (into gitignored `external_data/wonder/`) |

**Archived plans.** `PLAN_ROUND_1`–`22` are at tag `v0.21.0`, `PLAN_ROUND_23` at `v0.21.1`, `PLAN_ROUND_24` at `v0.22.0`, `PLAN_ROUND_25` at `v0.22.1`, `PLAN_ROUND_26` at `v0.23.0`. Code and docs still cite
them as labels (for example "PLAN_ROUND_16 A2"). To read one: `git show v0.21.0:PLAN_ROUND_16.md` (or the later tag), or
`https://github.com/cafeTechne/Census-Research-Engine/blob/v0.21.0/PLAN_ROUND_16.md`.

**Round 23 (v0.21.1, internal):** `census/manifest.py` became the `census/manifest/` package with no
behaviour change (478 golden snapshots identical; `scripts/refactor_golden.py`). `run_manifest` stages for a
later split are listed in `PLAN_ROUND_23.md` section 7 (at `v0.21.1`).

## Methods: validation status

Validated means a fixed, pre-set simulation or reference check passed. Failed methods stay exploratory only;
manifests refuse them in confirmatory analyses.

| Method | Status | Evidence |
| :--- | :--- | :--- |
| ACS derived estimates and MOEs (proportions, ratios, sums, medians) | Validated against Census-published values | `docs/audits/validation_report.md` |
| `fit_replicate` (OLS/WLS; 80 VRE replicate refits) | Validated: `population` 0.907, `these_areas` 0.897; `se_total` conservative (0.952–0.961) | `docs/audits/inference_validation.md` |
| `fit_eiv` (errors-in-variables) and its cluster jackknife | Validated (0.87–0.93) | `eiv_validation.md`, `eiv_cluster_validation.md` |
| Binomial/Poisson GLM with `scale: "robust"` (HC3) | Validated (0.879–0.897); required for external count outcomes | `robust_se_validation.md` |
| Binomial/Poisson with `scale: "X2"` (quasi-likelihood) | Failed under between-area overdispersion (0.689–0.79); refused for new manifests | `robust_se_validation.md` |
| Area SII / log RII / concentration (`inequality`, Round 24 implementation) | Passed fixed 90% conservative-interval validation: 0.876–0.905 for rank CV<=15%; high-error attenuation persists (CV30% information only). Independent areas. | `inequality_validation.md` (criterion `60330e3`) |
| Indirect SMR (`smr`, Round 24 implementation) | Passed combined Poisson/ACS log-interval validation: 0.893–0.909; rates fixed, independent band errors; negative band replicates refused. Exact Garwood limits condition on E. | `smr_validation.md` (criterion `680707e`) |
| Spatial CR1-t, G=8 (`cr1_t`, C1-8) | **Failed**: coverage 0.800–0.895; exploratory only | `spatial_cluster_validation.md`, criterion `46ec2ec` |
| Spatial CR1-t, G=12 (`cr1_t`, C1-12) | **Failed**: coverage 0.773–0.901; exploratory only | `spatial_cluster_validation.md` |
| Ibragimov–Müller, G=8 (`im`, C2-8) | **Passed**: 0.886–0.912; unweighted OLS/binomial, population only, no analysed ACS replicates; every cluster full-rank and >=5 units | `spatial_cluster_validation.md` |
| Restricted wild cluster bootstrap, G=12 (`wcr`, C3-12) | **Failed**: coverage 0.824–0.908; exploratory only, no ACS replicate combination | `spatial_cluster_validation.md` |
| Poisson–Gamma descriptive EB rate smoothing | **Passed** fixed 90% area-average criterion: posterior 0.8813–0.9000 (default); Laird–Louis 0.8718–0.8914 in six required cells. Fixed E/rates, independent areas; [1,9] censoring; 200 bootstrap refits for LL | `eb_rate_validation.md`, criterion `d4dec47` |
| Centered natural splines / joint chi-squared Wald | **Failed**: nominal .10 size 0.1055–0.1825; four cells exceed .13. Both exploratory only; confirmatory manifests refused | `joint_wald_validation.md`, criterion `376ce69` |
| Conley spatial HAC SEs (`spatial_se`) | **Failed** (0.71–0.87 at 150 km); exploratory only | `spatial_hac_validation.md` |
| Spatial error model λ correction (ME-SEM) | Validated for λ > 0 (0.86–0.93); lag model at γ 0.6 under-covers | `spatial_regression_validation.md` |
| LISA under sampling error | Characterised, information only | `lisa_validation.md` |
| Tract 2010→2020 apportionment: 1:1 and merged | Validated | `rate_apportionment_validation.md` |
| Split tracts: default `missing`; opt-in `split: "dominant"` (≥0.95 share) | Dominant passed held-out OH/PA (ratio 0.913); general split failed | `rate_apportionment_retest.md` |

**Round 24 (v0.22.0):** a new manifest method is one `MethodSpec` entry in `census/manifest/methods.py`
(golden identical for the refactor; 516 snapshots now). New methods `inequality` (SII, log RII,
concentration index; ridits least to most deprived, positive = worse in more deprived areas) and `smr`
(combined interval drives tests; fixed-E Garwood limits reported only). Both assume independent areas.
Exploratory example: `docs/studies/r24_lbw_inequality_example.md`. Suite: 1703 passed, 37 skipped.

**Round 25 (v0.22.1):** `run_manifest` drives typed `RunState` stages in `run.py`.
Both offline goldens are required for manifest refactors; suite unchanged at 1703 passed / 37 skipped.

**Round 26 (v0.23.0):** IM-8 passed, CR1/WCR did not.
Cluster assignments and inference bases are explicit; no new MCP tools (63). Cached original residual
Moran I remains 0.195464 / 0.183552. IM comparisons are unavailable under the retained ACS/EIV
protocol; the authorized R21b unclustered OLS/ACS sensitivity is separate from unchanged EIV outputs
(`docs/studies/r26_posthoc_spatial_clusters.md`). No original study files were rewritten.
Acceptance: 1734 passed, 37 skipped (31 new tests); both legacy goldens byte-identical.

**Round 27 (v0.24.0 implementation, pending review):** descriptive `eb_poisson_gamma`
includes censored-count likelihoods, posterior mixtures, optional rate units and
explicit validation metadata; posterior default. `cr(df=3/4/5)` freezes centered
full-sample state in replicates; joint tests use full HC3/sampling covariance,
record df and refuse singular covariance. Both nonlinear features remain
exploratory after the failed criterion. No new dependencies or tools (63).
Acceptance: 1782 passed, 37 skipped, 49 subtests; 0 failures; 48 new tests. Golden differences are supported-statistic
messages, additive covariance diagnostics and dependent hashes only; existing
scientific values unchanged (`docs/audits/round27_compatibility.md`).

## Standing rules

- **Circularity (enforced, R1/R2):** determinant studies use the ACS's own measure (disability: B18101).
  Model-based external estimates such as PLACES only for measures the ACS lacks (such as diabetes).
- **Pre-registration:** a manifest is hashed and committed before any outcome association is examined.
  Registered results are never rewritten; later checks are labelled post hoc.
- **Studies:** MI (26) and NY (36) are the test states. Study reviews by an agent are labelled "author
  self-review, not independent".
- **Releases:** every merged round gets a tag, GitHub release and Zenodo DOI. Study outputs are attached as
  a tarball after a key scan. Merges and releases need the owner's explicit approval.
- **Secrets and attribution:** see `CLAUDE.md`.

## Studies so far

| Round | Study | Headline |
| :--- | :--- | :--- |
| 19 | MI/NY tract income change | `docs/studies/r19_mi_ny_tract_income_change.md` |
| 20 | Disability and its determinants | `r20_mi_ny_disability_determinants.md` |
| 21 | PLACES disability vs ACS | PLACES inflates the education gradient 1.4× |
| 21b | County premature mortality | Poverty, disability supported; vehicle, cost burden not |
| 22 | County low birth weight | Poverty supported (holds with robust SEs); cost burden fragile (fails with robust SEs) |
| 24 | LBW inequality by poverty (exploratory) | RII 1.25 (90% CI 1.00–1.57); all intervals include the null |
| 26 | Cached spatial re-check / OLS sensitivity | IM unavailable for registered ACS/EIV inputs; `r26_posthoc_spatial_clusters.md` |

## Open backlog

1. Spatial dependence with ACS/EIV remains unresolved: Round 26 IM-8 passed for model-only
   OLS/binomial, but cannot incorporate the studies' ACS replicates or EIV. CR1/WCR and Conley failed.
   Separately validate ACS-compatible spatial inference or spatial random effects next; do not drop
   uncertainty to force an IM re-check. Poisson also needs separate validation.
2. Measurement-error correction for GLM covariates (none yet; `regression_calibration` is approximate).
3. Replication of the county findings in held-out states (OH/PA): Round 29 (needs the owner's WONDER exports).
4. Further methods: segregation indices and SMR reference-rate uncertainty (Round 28).
   Round 27 delivered descriptive EB and exploratory splines/joint tests. The latter
   require a separately pre-specified finite-sample validation before confirmatory use.
   Not yet planned: microdata inequality measures.
5. Saturated-model results bundles (Round 25 observation): a two-observation, two-coefficient OLS
   fit can crash while plotting the bundle (`ValueError: arange: cannot compute length`). Preserve
   estimable coefficients, explicitly mark unavailable uncertainty when residual degrees of freedom
   are zero, and skip or adapt plots requiring finite intervals. Add a regression ensuring the bundle
   completes without inventing SEs, confidence intervals or p-values.

## Plan format (keeps agent context small)

Plans may be queued ahead; agents implement only the lowest-numbered one. A round plan stays under about 15 KB: goal, ground rules, exact names and files, fixed acceptance checks,
and a short status table. When the round merges, add its outcome here in a few lines, then delete the plan
from the tree (it stays at its release tag).
