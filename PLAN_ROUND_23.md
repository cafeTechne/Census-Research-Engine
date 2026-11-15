# Round 23 plan: split `census/manifest.py` into a package

**Goal.** `census/manifest.py` (3,010 lines, 180 KB) is the engine's most-edited file. Every change makes an
agent read parts of it. Split it into a package of focused modules with **no behaviour change**, so later
rounds read one module of a few hundred lines.

**Non-goals.** No new features, no bug fixes, no renamed functions, no changed messages, no reformatting of
moved code, no new dependencies, no changes outside the files named here. If you find a bug, write it in
section 7 (status table) and leave it alone.

## 0. Ground rules

1. Branch `phase23/split-manifest` from `phase23/plan`. Push it. Do not merge, tag or release.
2. **No AI attribution anywhere.** Commits and the PR body must not contain `Co-Authored-By`,
   `Generated with`, or any similar line, even if your tooling suggests one.
3. Never print, log or commit `.env` or any API key or token.
4. Use `.venv/bin/python` (there is no `python` on PATH). Set `OPENBLAS_NUM_THREADS=1` for the suite.
5. Do not run GitHub CI. Commits may carry `[skip ci]`.
6. Read only what you need: `census/manifest.py`, the files named in sections 3–4, `pyproject.toml`,
   `tests/test_packaging.py`. Do not read `docs/studies/`, `docs/audits/`, `studies_output/` or old plans.
7. If something in this plan is impossible as written, stop, record it in section 7, and choose the option
   that changes the least.

## 1. Baseline (before touching any code)

On a clean checkout of `phase23/plan`:

```bash
CENSUS_HEALTH_OFFLINE=1 .venv/bin/python scripts/refactor_golden.py /tmp/golden_before.json
.venv/bin/python -c "import census.manifest as m; print('\n'.join(sorted(n for n in vars(m) if not n.startswith('__'))))" > /tmp/names_before.txt
OPENBLAS_NUM_THREADS=1 .venv/bin/python -m pytest -q 2>&1 | tail -1 > /tmp/suite_before.txt
```

Expected suite line: `1634 passed, 37 skipped` (warnings and subtests may vary). Record the actual line in
section 7. `refactor_golden.py` must report `478 snapshots from 11 manifests`.

## 2. Target layout

Convert the module into a package. Start with `git mv census/manifest.py census/manifest/__init__.py`, then
cut code out of `__init__.py` into the submodules below. Move each definition **verbatim**: same body,
same comments, same docstring. Only import lines may change.

| Module | Contents (exact names) |
| :--- | :--- |
| `schema.py` | All module-level constants from `SCHEMA_VERSION` through `REFERENCES` (including `ANALYSIS_METHODS`, `BLOCKING_DEVIATIONS`, the `STATUS_*` names, `FORMULA_ID_COLUMNS`, `FORMULA_FUNCTIONS`, `_STATE_PREFIXED_LEVELS`), `LEGACY_X2_MANIFESTS`, `CONFIRMATORY_REPLICATE_POLICY`, `REPLICATE_METHODS`, `_SPEC_KEYS`; and `canonical_json`, `manifest_hash`, `load_manifest`, `_table_of`, `_dataset_for`, `manifest_states`, `manifest_entities`, `_is_int`, `manifest_releases`, `release_overlap_message`, `_normalize_analysis`, `_duplicate_spec_keys`, `_formula_names`, `_variable_tables`, `tables_and_refs`, `_derivation_refs` |
| `external.py` | `external_names`, `external_circularity`, `_ext_source_text`, `_has_equivalent`, `circularity_errors` |
| `adjustments.py` | `default_rpp_areas`, `latest_rpp_year`, `_check_adjustments`, `_check_rpp_years`, `_check_dollar_year`, `_FILL_REASONS`, `_fill_adjustment_defaults`, `_scale_rows`, `_apply_adjustments` |
| `derivations.py` | `_age_standardized_errors`, `_fill_derivation_defaults` |
| `replicates.py` | `_vre_level`, `census_vre_source`, `_check_replicates`, `vre_unavailable`, `_declared_covariates_only`, `_replicate_overlap`, `_has_replicate_rows`, `_replicate_rows`, `_derive_replicates`, `_census_vre_replicates`, `_canonical_column`, `replicates_digest`, `read_replicates`, `replicates_sha256` |
| `datasource.py` | `effective_data_source`, `observed_data_source`, `data_source_record`, `resolve_data_source` |
| `validate.py` | `_check_geography`, `_check_variables`, `validate_manifest` (and the section 5 helpers) |
| `create.py` | `create_manifest` |
| `methods_text.py` | `_METHOD_TEXT`, `_age_standardized_text`, `_multi_release_adjustment_text`, `methods_section` (and the section 5 helpers) |
| `run.py` | `label_exploratory`, `analysis_status`, `_codebook_columns`, `_wide_from_panel`, `_one_sided`, `_run_analysis`, `_statistic`, `_tag`, `run_variant`, `run_manifest`, `_write_analysed_data`, `_write_bundle` |
| `__init__.py` | The original module docstring (lines 1–174, unchanged) and re-exports only (section 3). No logic. |

Any definition not listed: put it in the module whose functions use it, and list it in section 7.

**Import rules (to avoid cycles).** Submodules import each other with explicit relative imports
(`from .schema import manifest_hash`). A submodule never imports from `census.manifest` or from `.` (the
package `__init__`). Allowed direction: `schema` ← everything; `external`, `adjustments`, `derivations`,
`replicates`, `datasource` ← `validate`, `create`, `methods_text`, `run`; `validate` ← `create`, `run`;
`methods_text` ← `run`. Keep a function-local import inside a function body as a function-local import.

**Packaging.** `pyproject.toml` lists `packages = ["census"]` explicitly, so the new subpackage would be
left out of installs. Change it to `packages = ["census", "census.manifest"]`. Nothing else in
`pyproject.toml` changes.

## 3. Facade: `census/manifest/__init__.py`

Re-export **every** name in `/tmp/names_before.txt` that was defined in the old module (functions, classes,
constants, including `_private` ones). Names that were only imported into the old module (`np`, `pd`, `json`,
`Path`, `Any`, `integrity_errors`, `IncompleteReplicatesError`, etc.) should also stay reachable: re-export
them too, so that `vars(census.manifest)` is a superset of the baseline. Write the re-exports as explicit
`from .schema import (a, b, ...)` lists, grouped by submodule, alphabetical within a group. No `import *`.

## 4. Tests: only these lines may change

Moving a function changes where `mock.patch` must point: a patch on `census.manifest.X` no longer affects
a call to `X` made inside a submodule. These are the only patches on this module:

| File | Current target |
| :--- | :--- |
| `tests/test_review_fixes_r15.py` | `mock.patch("census.manifest.latest_rpp_year", ...)` |
| `tests/test_review_fixes_r12.py` | `mock.patch("census.manifest.replicates_digest", ...)` |
| `tests/test_metadata_integrity.py`, `tests/test_review_fixes_r14.py` | `patch("census.manifest.run_manifest", ...)` |
| `tests/test_manifest_releases.py` | `mock.patch("census.manifest.validate_manifest", ...)` |
| `tests/test_audit_decisions.py` | `patch.object(manifest, "_run_analysis", ...)` |
| `tests/test_review_fixes_r14.py` | `patch.object(M, "default_rpp_areas", ...)` |
| `tests/test_tract_harmonization.py` | `patch.object(mf, "_write_analysed_data", ...)` |

For each one: run its test first. If it still passes unchanged (the caller looks the name up through
`census.manifest`, as `mcp_server.py` and `census/workflows*.py` do), leave it. If it fails, re-point the
patch at the submodule where the name is **looked up at call time** (for example
`census.manifest.run._run_analysis`). If a name is called from two submodules and the test needs both,
patch both. Change nothing else in any test file, and record each change in section 7.

No other file outside `census/manifest/`, `pyproject.toml`, those test lines and the docs in section 6 may
change. In particular, `mcp_server.py` and other `census/*.py` modules keep importing from
`census.manifest` exactly as now.

## 5. Splitting the three long functions (golden-covered only)

After sections 2–4 pass section 6's checks, commit. Then split **only** these two functions, which the golden
snapshot covers byte for byte:

- `validate_manifest` (about 300 lines): extract its consecutive blocks into private helpers in
  `validate.py`, called in the same order with the same `errors` list, so the output order is unchanged.
  Natural cuts: top-level keys/schema; variables; derivations; the per-analysis loop body
  (`_check_analysis(i, a, ...)`); hypotheses; exclusions/missing/correction. Target: the
  `validate_manifest` body is at most 80 lines.
- `methods_section` (about 320 lines): extract the paragraph builders (data, derivations, adjustments,
  replicates, per-analysis text, references) into private helpers in `methods_text.py`, joined in the same
  order. Target: the `methods_section` body is at most 80 lines.

Do **not** split `run_manifest` this round. The golden snapshot does not cover it byte for byte; record its
natural stages in section 7 for a later round.

If a split cannot keep the golden snapshot identical, revert that function to the verbatim move and record
it in section 7.

## 6. Acceptance (all required)

```bash
CENSUS_HEALTH_OFFLINE=1 .venv/bin/python scripts/refactor_golden.py /tmp/golden_after.json
cmp /tmp/golden_before.json /tmp/golden_after.json            # must print nothing
.venv/bin/python -c "import census.manifest as m; print('\n'.join(sorted(n for n in vars(m) if not n.startswith('__'))))" > /tmp/names_after.txt
comm -23 /tmp/names_before.txt /tmp/names_after.txt           # must print nothing (superset)
OPENBLAS_NUM_THREADS=1 .venv/bin/python -m pytest -q 2>&1 | tail -1   # same passed/skipped counts as baseline
.venv/bin/python -c "import mcp_server"                        # server module imports
wc -l census/manifest/*.py                                     # every module <= 900 lines; __init__.py has no defs
grep -n "^def \|^class " census/manifest/__init__.py           # must print nothing
```

Also run each check after the section 5 commit. Then update the docs:
`grep -rn "census/manifest.py\|manifest\.py" docs README.md CLAUDE.md STATUS.md CONTRIBUTING.md`, and change
each path reference to the package or submodule (no other wording changes). Add a three-line CHANGELOG
entry under a new `## Unreleased` heading: "Internal: `census.manifest` split into a package (no behaviour
change; golden snapshot identical)".

## 7. Status table (fill in; keep it short)

| Item | Status | Notes |
| :--- | :--- | :--- |
| Baseline suite line | | |
| Golden snapshot count | | |
| Unlisted definitions placed | | |
| Packaging change | | |
| Test patch targets changed | | |
| Section 5: validate_manifest | | body lines |
| Section 5: methods_section | | body lines |
| `run_manifest` stages (for later) | | |
| Bugs noticed (not fixed) | | |
| Module line counts | | |
| Final suite line | | |

## 8. Deliverables

1. Commits on `phase23/split-manifest`, in this order: (a) package conversion and verbatim moves,
   packaging, test targets; (b) the `validate_manifest` split; (c) the `methods_section` split; (d) docs,
   CHANGELOG, status table. Each commit passes section 6.
2. Push the branch. If you cannot open a PR, say so. The owner's agent opens it.
3. PR body (if you open it): what moved where (one table), the section 6 outputs pasted, the status table,
   no attribution.
