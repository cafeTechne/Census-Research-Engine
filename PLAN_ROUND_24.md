# Round 24 plan: analysis-method registry, health-inequality indices, standardized ratios

**Goal.** (A) Define each manifest analysis method in one place, so a new method is one registry entry
instead of edits in five files. (B) Use the registry to add two validated public-health methods: area-level
inequality indices (slope index, relative index, concentration index) and indirectly standardized ratios
(SMR) with ACS-based expected counts. (C) Show them on an exploratory MI/NY example. Version 0.22.0.

**Non-goals.** No `run_manifest` split (next round). No new MCP tools (63 stays 63). No new dependencies.
No individual-level (microdata) inequality measures. No Erreygers/Wagstaff corrections. No change to any
existing method's numbers or messages.

## 0. Ground rules

1. Branch `phase24/inequality` from `phase24/plan`. Push it. Do not merge, tag or release. (The owner's
   agent merges Round 23 in parallel; `phase24/plan` sits on exactly that history, so no rebase is needed.)
2. **No AI attribution anywhere.** Commits and the PR body must not contain `Co-Authored-By`,
   `Generated with`, or any similar line, even if your tooling suggests one.
3. Never print, log or commit `.env` or any API key or token.
4. Read `CLAUDE.md` and `STATUS.md` first. Use `.venv/bin/python`; set `OPENBLAS_NUM_THREADS=1` for the suite.
5. Do not run GitHub CI. Commits may carry `[skip ci]`.
6. **Validation first.** Each validation's script and acceptance criterion are committed and pushed
   **before** its first full run. Do not change seeds, designs or criteria after a run. A method that fails
   its validation ships as exploratory only (manifests refuse it unless `exploratory: true`), exactly as
   `spatial_se` did in Round 22. Smoke runs of at most 20 draws are allowed before the commit, to debug.
7. If something here is impossible as written, record it in section 9 and choose the option that changes
   least.

## 1. Baseline

```bash
CENSUS_HEALTH_OFFLINE=1 .venv/bin/python scripts/refactor_golden.py /tmp/golden_before.json   # 478 snapshots
OPENBLAS_NUM_THREADS=1 .venv/bin/python -m pytest -q 2>&1 | tail -1    # expect 1634 passed, 37 skipped
```

## 2. Part A: method registry (no behaviour change)

Create `census/manifest/methods.py`:

```python
@dataclass(frozen=True)
class MethodSpec:
    name: str
    required: Tuple[str, ...]            # today's ANALYSIS_METHODS[name][0]
    statistics: Tuple[str, ...]          # today's ANALYSIS_METHODS[name][1]
    run: Callable[..., Any]              # (a, args, frame, level, replicates, correction, ctx) -> result
    replicate: bool = False              # member of REPLICATE_METHODS
    external_outcome: bool = False       # member of health_sources.EXTERNAL_OUTCOME_METHODS
    check: Optional[Callable[..., None]] = None   # method-specific validation, appends to errors
    text: Optional[Tuple[str, List[str]]] = None  # today's _METHOD_TEXT entry, if any

METHODS: Dict[str, MethodSpec] = {...}     # same insertion order as today's ANALYSIS_METHODS
STATISTIC_EXTRACTORS: Dict[str, Callable[[Mapping, Any], Dict[str, Any]]] = {...}
```

Then:

1. `schema.ANALYSIS_METHODS`, `schema.STATISTICS`, `schema.REPLICATE_METHODS` and
   `health_sources.EXTERNAL_OUTCOME_METHODS` keep their names, types, values and order, but are **derived**
   from `METHODS`. Avoid an import cycle: if `schema` cannot import `methods`, define the derived constants
   in `methods.py` and re-export them from `schema` and the facade, so every existing import still works.
2. `run._run_analysis`: keep the shared preamble (argument normalisation, replicate policy, coords,
   `held_external`) and replace the `if method == ...` chain with `METHODS[method].run(...)`. Move each
   branch body verbatim into a small runner function in `methods.py`. `ctx` carries `held_external` and
   `coords`.
3. `run._statistic`: dispatch through `STATISTIC_EXTRACTORS`. Move each branch verbatim.
4. `validate._check_analysis`: the method-specific blocks (today's `fit_replicate` argument block, the
   `spatial_se` block, and any other `if method == ...` block) move verbatim into `check` callbacks, called
   at the same point so the error order is unchanged.
5. `methods_text._METHOD_TEXT` becomes a view built from `MethodSpec.text`, with the same keys and values.

**Acceptance A** (commit when all pass): golden snapshot byte-identical to `/tmp/golden_before.json`; the
suite has the same counts; `grep -n 'method == "' census/manifest/run.py census/manifest/validate.py`
prints only lines you list and justify in section 9 (shared, not method-specific, logic).

## 3. Part B1: `census/inequality.py` (library)

Conventions (state them in the module docstring):

- Units are areas with population weights `w_i > 0`. The ranking variable `x` is an area-level
  socioeconomic measure. Areas are ordered from **least deprived (ridit 0) to most deprived (ridit 1)**.
  The caller says which way `x` points (`higher_is_more_deprived`, required, no default).
- **Ridit:** `r_i = (W_below_i + w_i / 2) / W`, where `W_below_i` is the weight of areas strictly less
  deprived. Tied `x` values share the mean ridit of their block.
- Positive SII, log RII and concentration index all mean the outcome is **higher among more deprived
  areas**. The concentration index sign is therefore the reverse of the usual income-ranked convention;
  say so in every output note.

Functions (NumPy/pandas/statsmodels only):

| Function | Definition | Model SE |
| :--- | :--- | :--- |
| `ridits(x, w, higher_is_more_deprived)` | above | none |
| `slope_index(y, x, w, hi)` | WLS of `y` on `[1, r]`, weights `w`: `SII = b`, `log RII = log((a + b) / a)` (undefined, NaN with a note, if `a <= 0` or `a + b <= 0`) | HC3 (`cov_type="HC3"`); log RII by delta method, gradient `(1/(a+b) - 1/a, 1/(a+b))` |
| `concentration_index(y, x, w, hi)` | `C = 2 cov_w(y, r) / mean_w(y)`; equivalently the slope of the weighted convenient regression `2 var_w(r) y / mean_w(y) = alpha + C r` | HC3 slope SE of that regression (an approximation; the validation tests it) |
| `inequality_replicate(frame, outcome, rank_by, weights, hi, replicates, fixed=(), level=0.90, target="conservative")` | Full-sample SII, log RII and C, then the same three on each of the 80 replicates, recomputing ridits each time. The rank variable, the weights and the outcome use their replicates when present; names in `fixed` (external outcomes) stay at their estimates. `se_sampling = sqrt(4/80 sum (t_r - t)^2)`, `se_total = sqrt(se_model^2 + se_sampling^2)`. | Returns a `ModelResult` whose `coefficients` has terms `sii`, `log_rii`, `concentration_index` and the usual SE and interval columns for `target`. |

`inequality_replicate` uses the strict replicate policy of `census.results`, as `fit_replicate` does. It
records the median CV of `rank_by` in `diagnostics["rank_cv_median"]`. When that is above the validated range
(section 5), it adds a note, and the methods text says the estimates may be attenuated by rank error.

## 4. Part B2: standardized ratios in `census/standardize.py`

Add `indirect_standardize(observed, band_populations, reference_rates, band_replicates=None, level=0.90)`:

- `E_i = sum_b pop_ib * ref_b`, `SMR_i = O_i / E_i`. A pooled ratio over a set of areas is
  `sum O / sum E`.
- **Exact interval with E fixed** (Garwood): lower `chi2.ppf(alpha/2, 2O) / (2E)` (0 when `O = 0`), upper
  `chi2.ppf(1 - alpha/2, 2O + 2) / (2E)`. Report as `smr_exact_lower`/`upper`.
- **Combined interval** (used for tests): on the log scale,
  `var(log SMR) = 1/O + s_E^2`, where `s_E^2 = 4/80 sum (log E_r - log E)^2` from the band replicates
  (0 without replicates, with a note). Wald interval, exponentiated. Not defined when `O = 0` (NaN, note).
- Returns a DataFrame with GEOID, observed, expected, smr, `log_smr`, `se_log_smr`, combined and exact
  limits, `p_value` (two-sided Wald on log scale), and the notes.

## 5. Part B3: validations (criteria committed before running)

**`scripts/inequality_validation.py` → `docs/audits/inequality_validation.md`/`.json`.**
- Cells: n ∈ {145, 1000} × rank CV ∈ {0.05, 0.15, 0.30}. 1,000 draws per cell. Seed `20261116 + cell index`.
- Fixed per cell, drawn once:
  - weights: lognormal, median 20,000 (n = 145) or 4,000 (n = 1000), log-SD 1.0;
  - true deprivation `x = expit(N(-1.6, 0.6))`;
  - true ridits from `x`.
- Each draw:
  - outcome proportion `y = 0.07 + 0.03 r + u`, with `u ~ N(0, 0.008^2)`;
  - observed `y` from a binomial with denominators `w / 50`, held fixed (an external outcome);
  - observed `x_hat = x + N(0, (cv x)^2)`, with replicates from `census.simulation.make_replicates(x_hat, cv * x, rng)`.
- Truths:
  - `SII = 0.03`, `log RII = log(0.10 / 0.07)`;
  - `C = 2 cov_w(0.07 + 0.03 r, r) / mean_w(0.07 + 0.03 r)` with the true ridits.
- **Acceptance:** coverage of nominal 90% intervals ≥ 0.86 for all three statistics, at target
  `conservative`, in the four cells with CV ≤ 0.15. Report target `population` coverage, bias and mean
  SE / empirical SD for every cell. The CV 0.30 cells are information only. They define the "validated
  range" note (median rank CV ≤ 15%).

**`scripts/smr_validation.py` → `docs/audits/smr_validation.md`/`.json`.**
- Cells: expected deaths `E_true` ∈ {10, 50, 500} × band CV ∈ {0.05, 0.20}. 2,000 draws. Seed
  `20261117 + cell index`. Five bands with reference rates `(0.0005, 0.001, 0.003, 0.01, 0.04)`, band
  populations scaled so that `E_true` is hit. True SMR 1.2.
- Each draw:
  - `O ~ Poisson(1.2 E_true)`;
  - observed band populations `pop_b (1 + N(0, cv^2))`, with replicates from `make_replicates`.
- **Acceptance:** combined-interval coverage of the true SMR ≥ 0.86 in all six cells. A draw with
  `O = 0` counts as non-coverage. Report exact-interval coverage too.

If a validation fails, its method is exploratory only (manifests refuse it unless `exploratory: true`).
Record this in the audit and in section 9.

## 6. Part B4: manifest methods (registry entries)

| Method | Required keys | Args | Statistics (hypothesis `statistic`) |
| :--- | :--- | :--- | :--- |
| `inequality` | `outcome`, `rank_by`, `weights` | `higher_is_more_deprived` (bool, required), `target` (default `conservative`) | `sii`, `log_rii`, `concentration_index` |
| `smr` | `observed`, `population_bands`, `reference_rates`, `reference_source` | `target` (no other args) | `log_smr` |

Rules (implement as the methods' `check` callbacks; error texts are yours, but each must name the analysis):

- `outcome`, `rank_by`, `weights` and each `population_bands` entry must be manifest variables, except
  that `weights` may be `<outcome>_denominator` when the outcome is external. `outcome`
  may also be an external variable, and `observed` may be an external `<name>_numerator`. Set
  `external_outcome=True` for both methods. External outcomes are held fixed in the replicate refits.
- `reference_rates`: a list of finite numbers > 0, the same length as `population_bands`.
  `reference_source`: a non-empty string (where the rates come from). Both are part of the hash.
- Hypotheses on `inequality` name a `statistic` only (no `term`). Hypotheses on `smr` give `geoid`: one
  GEOID, or `"all"` for the pooled ratio.
- **Circularity R2:** for `inequality`, `rank_by` is the tested term, so extend `circularity_errors`
  (`census/manifest/external.py`) to apply R2 to it. R1 applies unchanged to `outcome`/`observed`.
- Log-scale statistics (`log_rii`, `log_smr`) are tested against 0, so `_one_sided` needs no change. Add
  ratio columns to the hypothesis table, following the `odds_ratio` pattern in `run.py`: `ratio`,
  `ratio_lower`, `ratio_upper`.
- Methods text: one paragraph each (ridit definition and direction, HC3 plus replicates, target; SMR
  definition, reference source, exact and combined intervals). Add references: Pamuk 1985 (Population
  Studies 39:17–31); Kakwani, Wagstaff & van Doorslaer 1997 (J Econometrics 77:87–103); Garwood 1936
  (Biometrika 28:437–442); Breslow & Day 1987 (IARC Sci Publ 82).

## 7. Part C: docs and exploratory example

- `docs/recipes/health_inequality.md` and a `health_inequality` entry in `census/recipes.py` (the recipe
  count test may need its expected list extended; that is the only allowed test edit outside new tests).
- `docs/agent_protocol.md`: a short "Inequality and standardized ratios" section (statistics, direction
  convention, validated range, SMR reference-rate requirement).
- Library exports in `census/__init__.py`: `ridits`, `slope_index`, `concentration_index`,
  `inequality_replicate`, `indirect_standardize`.
- Example `examples/manifests/r24_mi_ny_lbw_inequality.json`:
  - `exploratory: true`; MI/NY counties;
  - outcome CHR v037 low birth weight (`lbw`); `rank_by: pov_rate`, `higher_is_more_deprived: true`;
  - weights: `lbw_denominator` (live births; allow `weights: "<outcome>_denominator"` when the outcome is
    external, as the binomial `trials` role does).
  
  It is exploratory because Round 22 already related poverty to this outcome. Run it with the cached CHR
  data. Write `docs/studies/r24_lbw_inequality_example.md` (one page: the three indices, intervals,
  median rank CV, the sign convention). Release outputs go in a tarball, not the repo.
- No SMR example with real data, because no age-specific death counts are cached (WONDER exports are
  manual). Use a synthetic end-to-end manifest test instead.
- Tests in `tests/test_round24.py`:
  - ridits: ties, weights, direction;
  - SII/RII/C against hand calculations on a 6-area example;
  - HC3 matches statsmodels;
  - exact Garwood limits against `scipy.stats.chi2`;
  - pooled SMR;
  - manifest validation: each rule in section 6;
  - end-to-end offline runs of both methods;
  - refusal when a failed method is used without `exploratory`.

## 8. Final acceptance

- Part A golden identical (section 2). After Part B, regenerate the golden snapshot and confirm by `diff`
  that only messages listing supported methods or statistics changed. Paste that diff summary in section 9.
- Full suite: baseline counts plus the new tests, 0 failures.
- Both audits committed, with the criterion commit preceding the run commit.
- CHANGELOG `0.22.0` entry; version metadata 0.22.0 wherever the existing release checklist sets it
  (`CHANGELOG.md` "Releasing").
- `STATUS.md`: add both methods to the validation table with their results, and remove backlog item 5.

## 9. Status table (fill in; keep it short)

| Item | Status | Notes |
| :--- | :--- | :--- |
| Baseline | | |
| A: registry, golden identical | | |
| A: remaining `method ==` lines | | |
| B1/B2 library | | |
| Inequality validation (criterion commit, result) | | |
| SMR validation (criterion commit, result) | | |
| B4 manifest methods, R2 extension | | |
| Golden diff after B | | |
| C docs, example run | | |
| Final suite | | |
| Exceptions (0.7) | | |

## 10. Deliverables

Commits in order: (1) Part A; (2) B1/B2 library and unit tests; (3) the inequality validation script and
criterion; (4) its run and audit; (5) the SMR validation script and criterion; (6) its run and audit; (7) B4
manifest methods and tests; (8) Part C; (9) CHANGELOG, STATUS, version, status table. Push
`phase24/inequality`. If you cannot open a PR, say so and leave a PR body at `/tmp/round24-pr-body.md`.
