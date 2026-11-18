# Round 28 plan: residential segregation indices and SMR reference-rate uncertainty

**Goal.**

- **(A)** Tract-based segregation indices within counties, with ACS replicate uncertainty and a
  pre-registered small-count bias correction.
- **(B)** Extend `smr` so it can use real reference rates: rates per person-year over a multi-year
  period, and the Poisson uncertainty of those reference rates.

Both ship only after their pre-set validations pass. Version 0.25.0.

**Non-goals.**

- No real-data SMR study; that is Round 29, after the owner's WONDER exports.
- No metro-area (CBSA) segregation: counties, or a declared list of counties, only.
- No new MCP tools; no new dependencies.

## 0. Ground rules

1. Branch `phase28/segregation-smr` from `defaultBranch` (after Round 27 merges). Do not merge, tag or
   release. Never rebase or force-push. Work in your own clone or worktree.
2. **No AI attribution** in commits or the PR body.
3. Never print, log or commit `.env` or any key or token.
4. Read `CLAUDE.md` and `STATUS.md` first. Use `.venv/bin/python` and `OPENBLAS_NUM_THREADS=1`. No GitHub CI.
5. **Validation first:** the script and criterion are committed and pushed before the first full run.
   Nothing changes after it. Smoke runs: at most 20 draws per cell, writing no audit files.
6. Record impossibilities in section 8 and choose the option that changes least.

## 1. Part A: `census/segregation.py`

Units are tracts (`t`) inside a containing area (county `c`). For group counts `n_tg` and tract totals
`n_t` (the sum over the declared groups):

| Index | Definition | Groups |
| :--- | :--- | :--- |
| Dissimilarity `D` | `½ Σ_t |n_t1/N_1 − n_t2/N_2|` | exactly 2 |
| Isolation `xPx` | `Σ_t (n_t1/N_1)(n_t1/n_t)` | exactly 2 (group 1) |
| Theil `H` | `Σ_t n_t (E − E_t) / (N E)`, where `E` is the entropy of the area's group shares and `E_t` that of the tract's | 2 or more |

Tracts with `n_t = 0` are dropped and counted in a note. If any group total `N_g` is 0, the index is
undefined (NaN, with a note).

**Uncertainty: 80 replicate refits**, recomputing each index from replicate tract counts:
`se = √(4/80 Σ (I_r − I)²)`. The strict replicate policy applies, as in `inequality_replicate`.

**Small-count bias.** Sampling noise inflates D and H. VRE replicate deviations have one quarter of the
sampling variance: the 4/80 factor means each `(I_r − I)²` averages `Var/4`. So, to first order, the
replicate shift `mean(I_r) − I` is one quarter of the estimate's bias. The pre-registered corrected
estimate is `I_bc = I − 4·(mean(I_r) − I)`, with the same `se`.

**Validation (`scripts/segregation_validation.py` → `docs/audits/segregation_validation.md`/`.json`).**

- **Cells:** tracts per county {20, 100} × true D {0.2, 0.5} × group-count CV {0.15, 0.30}: 8 cells,
  1,000 draws each, seed `20261129 + cell index`.
- **Per cell:**
  - true tract counts are drawn once (tract totals lognormal, median 4,000);
  - each draw adds ACS-like Gaussian error to the group counts at the cell's CV, then 80
    `make_replicates` values;
  - negative draws are not clipped: they count as invalid, which counts as non-coverage.
- **Acceptance (pre-set), per index × {naive, bias-corrected}:** 90% coverage of the true index ≥ 0.86 in
  all CV 0.15 cells. The CV 0.30 cells are informational.
- **Default:** the bias-corrected version if it passes, else the naive version if it passes. An index
  with no passing version is exploratory only.
- **Also report:** bias, and mean SE over the empirical SD.

**Manifest method `segregation`** (one `MethodSpec` entry; no `if method ==` branches):

- **Required keys:** `groups` (a list of manifest variables at tract level; exactly 2 for `dissimilarity`
  and `isolation`) and `within` (`county`).
- **Statistics:** `dissimilarity`, `isolation`, `theil_h`. Hypotheses give `geoid`, the containing
  county, and are either:
  - a **one-area** estimate tested against a pre-registered `null_value`; or
  - a **difference** between two counties (`compare_geoid`), computed within each replicate, so that
    shared replicate structure is respected.
- **Cross-release differences:** only for non-overlapping releases, each with its own replicates. The
  variance is the sum. Overlapping releases are refused, matching `replicates_overlapping_releases`.
- **Methods text:** the definitions, the bias correction, and the references: Duncan & Duncan 1955 (Am
  Sociol Rev 20:210–217); Massey & Denton 1988 (Social Forces 67:281–315); Reardon & Firebaugh 2002
  (Sociol Methodol 32:33–67).
- **Recipe:** `docs/recipes/segregation.md` and a `recipes.py` entry. Mirror the rules in the agent
  protocol and MCP text.

## 2. Part B: SMR with real reference rates

Extend `standardize.indirect_standardize` and the `smr` method:

- **`period_years`** (a positive integer, default 1; hashed): `E_i = period_years × Σ_b pop_ib · rate_b`,
  where the rates are per person-year (WONDER multi-year rates divide by summed annual populations).
- **`reference_counts`** (optional; one non-negative integer per band; hashed): the reference deaths
  behind each rate. With them, the combined variance gains `Σ_b (E_ib/E_i)² / D_b`, the delta method for
  independent Poisson reference counts. Bands with `D_b = 0` are refused.
- When the study areas are part of the reference population (internal standardization), the interval is
  conservative. The note says so; nothing is refused.

**Validation (`scripts/smr_reference_validation.py` → `docs/audits/smr_reference_validation.md`/`.json`).**

- **Cells:** reference deaths per band {50, 500, 5,000} × E ∈ {10, 100} × band CV 0.05: 6 cells, 2,000
  draws each, seed `20261130 + cell index`.
- **Design:** the Round 24 SMR design, plus reference counts drawn as Poisson from the true rates.
- **Acceptance (pre-set):** combined 90% coverage of the true SMR ≥ 0.86 in all 6 cells, *with* the
  reference term. Also report coverage *without* it, to show why the term is needed.

## 3. Tests (`tests/test_round28.py`)

- **D, xPx and H:** each against a hand calculation on a 4-tract example. H is 0 for identical tract
  shares; D is 1 for complete separation.
- **Replicates:** replicate SE and the bias correction on a fixed replicate array. The strict replicate
  policy refuses missing replicates.
- **Manifest:**
  - every section 1 rule;
  - the cross-county difference uses per-replicate differences;
  - overlapping releases are refused;
  - the exploratory gate works (patch where the check imports from, and assert the refusal).
- **SMR:** the `period_years` arithmetic. The `reference_counts` variance matches the delta method by
  hand. `D_b = 0` is refused. Both are included in the hash.
- **End to end:** offline runs of `segregation` and of `smr` with `reference_counts`.

## 4. Acceptance

- Both audits are committed after their criterion commits.
- The two golden scripts change only in "supported method/statistic" messages and the new example (if
  any); list the changes.
- Full suite: baseline plus the new tests, 0 failures.
- STATUS: validation-table rows, and remove the delivered parts of backlog item 5.
- Version 0.25.0, with a CHANGELOG entry.

## 5. Commits

(1) The segregation validation script and criterion; (2) its run and audit; (3) the SMR-reference
validation script and criterion; (4) its run and audit; (5) the library, manifest and tests; (6) docs,
STATUS, version and the status table. Push. If you cannot open a PR, leave a body at
`/tmp/round28-pr-body.md`.

## 8. Status table (fill in; keep it short)

| Item | Status | Notes |
| :--- | :--- | :--- |
| Baseline suite | Passed | 1782 passed, 37 skipped, 49 subtests; base `22a4c96`. |
| Segregation criterion / result (per index, naive vs corrected) | Passed variants selected | `4791763` pushed before full run; audit `43cbedf`. D naive .898–.911 passed, corrected failed. Isolation corrected .877–.901 passed, naive failed. H corrected .896–.961 passed, naive failed. No criterion changes. |
| SMR-reference criterion / result | Passed | `134bf7f` pushed before full run; audit `8335199`. Coverage .8995–.9105 in all six cells. Without term, coverage reached .724. |
| Engine, tests | Implemented | `6f3e82e`; 56 new tests, including independent definitions/covariances and offline bundles. No new tools or dependencies. |
| Golden changes | Accepted | 516 schema snapshots: 50 unsupported-method messages add segregation between regression_calibration and simex (analyses[0..2], validate/create). Run golden byte-identical across 29 scenarios/all 19 deviation kinds; no new example. |
| Final suite | 1838 passed, 37 skipped, 50 subtests; 0 failures | Baseline plus 56 new tests. |
| Exceptions | Documented below | Least-change choices under 0.6; no later-round implementation. |

Round 27 is complete/pushed but has not merged into defaultBranch. To proceed with
the owner's Round 28 request without an unauthorized merge, branch/worktree from
its final `22a4c96`: `phase28/segregation-smr` in `/tmp/census-round28`. This branch
is stacked on `phase27/eb-splines`; review/land in that order. No rebase/force push,
merge, tag, release or CI. The owner's untracked planning file is untouched.

The segregation DGP's unspecified tract log-SD is fixed at one. Matched lognormal
pairs, rounded to multiples of 20, produce integer counts and exactly the requested
true D. Both group count errors are independent Gaussian. The same fixed correction
is assessed for all three indices; the preset default-selection rule is retained.
CV .30 stays informational, with many invalid negative-count draws (noncoverage),
not clipped/redrawn. All details were committed before full results.

Only two-group coverage was simulated; multigroup H is computationally supported
but exploratory. Contrasts have covariance regression checks, not separate coverage
claims. Explicit hypothesis selectors release/compare_release resolve cross-year
ambiguity; compare_geoid may select another county. First minus comparison; same
county allowed across independent releases. One-area null_value is mandatory,
contrast null defaults to zero; the generic test step centers signs on the null.
Zero full-sample tracts may enter a replicate; absent county groups remain NaN with
notes. Zero/undefined SE produces an untested hypothesis, not invented inference.

MethodSpec gained optional-field and conditional-text callbacks for the new SMR
options, preserving all legacy outputs. period_years/reference_counts work at top
level or in args (duplicate placement refused), and both are hashed. No additional
internal-reference flag is introduced: membership cannot be inferred from rates
and counts. With reference counts, the library note conditionally explains internal
conservatism; reference denominators remain fixed. Pool band contributions before
squaring to retain common-reference covariance. Full validation fixes a five-year
period and the Round 24 rate/ACS-error design; exact limits remain fixed-E.

The delivered-method backlog was item 4, not item 5. Update by content; preserve
the unrelated saturated-model bundle bug. Package/citation version 0.25.0, while
the published-release line stays unchanged pending authorized integration/release.
Validation and golden artifacts are in `/tmp/r28-*`; if PR creation is unavailable,
its prepared body is `/tmp/round28-pr-body.md`.
