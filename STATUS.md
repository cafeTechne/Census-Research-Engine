# Project status

The single current summary of the Census Research Engine: what it does, which methods are validated, the
standing rules, and what is next. Read this instead of old plans. Updated each round when it merges.

**Current release:** v0.21.1 (Round 23, internal package split). Latest study release: v0.21.0 (Round 22), DOI 10.5281/zenodo.24264540. All versions: concept record
[zenodo.org/records/23925301](https://zenodo.org/records/23925301). Per-round detail: `CHANGELOG.md`.

## Where things are

| Path | What |
| :--- | :--- |
| `census/` | Library. `manifest/` package (pre-registered studies: `schema`, `validate`, `create`, `run`, `methods_text`, `methods` (single method registry), plus `adjustments`, `replicates`, `external`, `derivations`, `datasource`; import from `census.manifest`, but patch tests at the submodule that looks the name up), `models.py` (`fit_replicate`, `fit_eiv`, robust GLM SEs), `health_sources.py` (PLACES, USALEEP, CHR&R, WONDER exports), `spatial*.py`, `sae*.py`, `simulation*.py` (validation studies) |
| `mcp_server.py` | MCP server (63 tools; profiles in `census/mcp_profiles.py`) |
| `docs/agent_protocol.md`, `docs/recipes/` | What agents are told; keep in step with engine rules |
| `docs/audits/` | Validation reports (pass/fail, reproducible scripts in `scripts/`) |
| `docs/studies/` | Pre-registered study reports; outputs are release attachments, not in the repo |
| `examples/manifests/` | Registered manifests (their bytes are fixed once registered) |
| `PLAN_ROUND_<n>.md` | Only the current round's plan. Older plans are archived (below) |

**Archived plans.** `PLAN_ROUND_1`–`22` are at tag `v0.21.0`, `PLAN_ROUND_23` at `v0.21.1`. Code and docs still cite
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
| Conley spatial HAC SEs (`spatial_se`) | **Failed** (0.71–0.87 at 150 km); exploratory only | `spatial_hac_validation.md` |
| Spatial error model λ correction (ME-SEM) | Validated for λ > 0 (0.86–0.93); lag model at γ 0.6 under-covers | `spatial_regression_validation.md` |
| LISA under sampling error | Characterised, information only | `lisa_validation.md` |
| Tract 2010→2020 apportionment: 1:1 and merged | Validated | `rate_apportionment_validation.md` |
| Split tracts: default `missing`; opt-in `split: "dominant"` (≥0.95 share) | Dominant passed held-out OH/PA (ratio 0.913); general split failed | `rate_apportionment_retest.md` |

**Round 24 implementation (v0.22.0, awaiting review/merge):** method registry, area inequality and
indirect SMR; no new MCP tools (63). The exploratory cached LBW example uses 144 complete counties
and is documented in `docs/studies/r24_lbw_inequality_example.md`. Full suite: 1703 passed, 37 skipped;
69 new tests. Legacy 478 golden snapshots change only supported-method lists; final total 516.
Both final-library validation replays reproduce every committed cell. No merge, tag or release performed.

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

## Open backlog

1. Spatial dependence: residual Moran's I is about 0.18–0.20 in both county studies; Conley failed.
   Candidates: spatial random effects or a spatial block bootstrap, tested on the Round 22 design.
2. Measurement-error correction for GLM covariates (none yet; `regression_calibration` is approximate).
3. Replication of the county findings in held-out states (OH/PA).
4. Split `run_manifest` into stages (Round 23 recorded them in `PLAN_ROUND_23.md` section 7).

## Plan format (keeps agent context small)

A round plan stays under about 15 KB: goal, ground rules, exact names and files, fixed acceptance checks,
and a short status table. When the round merges, add its outcome here in a few lines, then delete the plan
from the tree (it stays at its release tag).
