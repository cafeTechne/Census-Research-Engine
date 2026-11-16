# Round 25 plan: split `run_manifest` into stages (no behaviour change)

**Goal.** `run_manifest` (`census/manifest/run.py`, about 450 lines in one function) becomes a short driver
over named stage functions that share one `RunState`. Before any code moves, a new **run golden**
snapshot records what offline runs produce, and it must stay byte-identical. Version 0.22.1.

**Non-goals.** No new features, no bug fixes (record any you notice in section 8), no output changes, no
test edits, no new dependencies, no MCP changes.

## 0. Ground rules

1. Branch `phase25/run-stages` from `plans/r25-r29` (it carries these plans and merges with this round). Push
   it. Do not merge, tag or release. Never rebase or force-push.
2. **No AI attribution anywhere.** Commits and the PR body must not contain `Co-Authored-By`,
   `Generated with` or any similar line, even if your tooling suggests one.
3. Never print, log or commit `.env` or any API key or token. No network access is needed this round.
4. Read `CLAUDE.md` and `STATUS.md` first. Use `.venv/bin/python`; set `OPENBLAS_NUM_THREADS=1`.
5. Do not run GitHub CI. Commits may carry `[skip ci]`.
6. Work in your own clone or worktree, not in the owner's main checkout.
7. If something here is impossible as written, record it in section 8 and choose the option that changes
   least.

## 1. Baseline

```bash
.venv/bin/python scripts/refactor_golden.py /tmp/golden_before.json   # 516 snapshots, 12 manifests
OPENBLAS_NUM_THREADS=1 .venv/bin/python -m pytest -q 2>&1 | tail -1   # 1703 passed, 37 skipped
```

Do not set `CENSUS_HEALTH_OFFLINE=1` for the suite: some tests mock fetches and expect it unset.

## 2. Run golden first (commit 1, before any refactor)

Add `scripts/run_golden.py OUT.json`. It runs `run_manifest` on a fixed corpus of **offline** scenarios
and writes one JSON snapshot. It mirrors `scripts/refactor_golden.py` (exceptions recorded as
`"<Type>: <message>"`, sorted keys, `indent=1`, trailing newline).

**Corpus.** Build each scenario from fixtures the test suite already uses. You may import helpers from
`tests/` (for example `tests.test_manifest.FakeClient`, `synthetic_payload`, and the Round 21, 22 and 24
offline fixtures). Each scenario has a fixed name and runs in its own temporary output directory. The
corpus must cover:

- a synthetic `fit_replicate` run with replicates, and one without (`replicates_unavailable`);
- exclusions and the CV screen; pre-registered adjustments (if an offline RPP fixture exists);
- tract harmonization (the `tests/test_tract_harmonization.py` fixtures);
- derivations with replicates;
- an external join (CHR and WONDER offline fixtures) with a binomial `scale: "robust"` outcome;
- `inequality` and `smr` (the `tests/test_round24.py` fixtures);
- a multistate run (`tests/test_manifest_multistate.py`);
- `run_variant` on one scenario;
- failure paths: validation errors; an output-directory error; `analysis_failed` (bad formula);
  `hypothesis_not_tested`; `data_source_mismatch`;
- every other deviation kind in `schema.BLOCKING_DEVIATIONS` that is reachable offline. List the
  unreachable ones in section 8.

**Snapshot per scenario.**

- The returned dict. DataFrames go through `to_dict(orient="split")`; Paths become strings relative to
  that scenario's output directory.
- For every file under the output directory, the relative path and:
  - for text files (`.json`, `.md`, `.csv`, `.tex`, `.txt`, `.svg`), the SHA-256 after normalisation;
  - for binary files (`.png`, `.pdf`, `.eps`, `.parquet`), the name only.

**Normalisation.** Volatile values are replaced by `"<volatile>"`: wall-clock timestamps, durations, the
absolute temporary path, and anything else that differs between two identical runs. List every
normalised key in the script's docstring. Normalise nothing else.

**Determinism check, before commit 1:** run the script twice on the unchanged code; the two outputs must
be byte-identical. If a value still differs, add it to the normalisation list and say why. Commit the
script only. Snapshots live in `/tmp`, not the repo:

```bash
.venv/bin/python scripts/run_golden.py /tmp/run_before.json
```

## 3. The split (commit 2)

Keep every stage function **in `census/manifest/run.py`**. Tests patch names such as
`census.manifest.run._write_analysed_data` and `census.manifest.run.validate_manifest`, and a stage moved
to another module would silently bypass those patches.

```python
@dataclass
class RunState:            # every local that crosses a stage boundary, typed; nothing else
    m: Dict[str, Any]; h: str; out: Path; client: Any; use_cache: bool; replicates: Any
    level: float; corr: Dict[str, Any]; releases: List[int]; geo: Any; entities: Any; opts: Any
    deviations: List[Dict[str, Any]] = field(default_factory=list)
    frame: Optional[pd.DataFrame] = None
    # ... the remaining cross-stage locals, named as they are today
```

Stages are named after the existing numbered comments in `run_manifest`. Run them in this order and move
each body **verbatim**, with locals becoming `state.` attributes:

| Stage function | Today's section |
| :--- | :--- |
| `_prepare(...) -> RunState or early result` | load, validate, hash, output dir, data-source check, options |
| `_extract(state)` | 1–2 plan and extraction |
| `_build_frame(state)` | 3 analysis frame (harmonization or aggregation) |
| `_fetch_vre(state)` | 3a Census VRE replicates and the apportioned-estimate check |
| `_derive_replicates(state)` | 3b derivations on supplied replicates |
| `_join_external(state)` | 3c external variables |
| `_apply_exclusions(state)` | 4 exclusions and CV screen |
| `_apply_adjustments(state)` | 4b adjustments, replicate-SE coverage, spatial coordinates |
| `_run_analyses(state)` | 5 analyses and 5a analysed data |
| `_test_hypotheses(state)` | 6 hypotheses and correction |
| `_bundle(state) -> dict` | 7 bundle and return value |

`run_manifest` keeps its signature and docstring, and its body (excluding the docstring) is at most 30
lines:

```python
state = _prepare(...)
if not isinstance(state, RunState):
    return state            # early validation/output error, exactly as today
for stage in _STAGES:       # the ten middle stages, in order
    stage(state)
return _bundle(state)
```

**Rules.**

- **Order.** No reordering of side effects: HTTP calls, file writes, `deviations.append` order and
  note order stay as they are.
- **Early returns.** A stage that today returns early from `run_manifest` sets `state.result`, and the
  driver returns it. Use one pattern and document it.
- **Length.** Each stage is at most 80 lines; if a stage is longer, split it into private helpers in the
  same module.
- **`run_variant`.** It keeps working unchanged.
- **Ripple effect.** If `run.py` grows past about 900 lines, you may move the pure helpers
  (`_codebook_columns`, `_wide_from_panel`, `_one_sided`) into a new `census/manifest/run_helpers.py`.
  Only do this if no test patches them; check with `grep -rn "run\.<name>" tests/`.

## 4. Acceptance

- `scripts/run_golden.py` output is byte-identical to `/tmp/run_before.json`.
- `scripts/refactor_golden.py` output is byte-identical to `/tmp/golden_before.json`.
- The full suite gives the same counts as the baseline, with no test file changed.
- `run_manifest` body is at most 30 lines, and each stage at most 80.
- `grep -n "^def \|^class " census/manifest/run.py` shows the stages in section 3's order.

## 5. Docs (commit 3)

- **`CLAUDE.md` Commands:** a refactor of `census/manifest` is accepted by *both* golden scripts.
- **`STATUS.md`:** remove backlog item 4 (split `run_manifest`); add a two-line Round 25 note; update the
  layout row.
- **`CHANGELOG.md`:** `0.22.1 (Round 25)` entry; version 0.22.1 in `census/__init__.py`,
  `census/pipeline.py` (`PACKAGE_VERSION`) and `CITATION.cff`.

## 6. Commits

(1) `scripts/run_golden.py`; (2) the split; (3) docs, version and the status table. Push
`phase25/run-stages`. If you cannot open a PR, say so and leave a PR body at `/tmp/round25-pr-body.md`.

## 7. Later rounds (do not start them)

`PLAN_ROUND_26`–`28` are queued in the tree. Do not read or start them this round.

## 8. Status table (fill in; keep it short)

| Item | Status | Notes |
| :--- | :--- | :--- |
| Baseline (golden count, suite line) | Pass | 516 snapshots / 12 manifests; 1703 passed, 37 skipped, 49 subtests (4 warnings). |
| Run golden: scenarios, normalised keys, determinism | Pass | 29 scenarios; two pre-split runs byte-identical. Keys: generated_at/git_commit/package_version; scenario path prefix, SVG dc:date and transitive text-artifact digests. Fixed SVG hashsalt. |
| Unreachable deviation kinds | None | All 19 blocking kinds exercised offline, using existing fixtures and explicit dependency failures. No HTTP calls. |
| Split: line counts (driver, longest stage, run.py) | Pass | 7-line driver excluding docstring; longest stage _bundle 77 lines; run.py 896. Stages follow table order; helpers and run_variant unchanged. |
| Both goldens identical | Pass | Execution: 29 scenarios byte-identical. Schema: all 516 snapshots byte-identical. |
| Final suite | Pass | 1703 passed, 37 skipped, 49 subtests, 4 unchanged warnings. Targeted: 115 passed / 1 skipped. No test file changed. |
| Bugs noticed (not fixed) | Recorded | WONDER suppression counts toward missing-join guard (1/3 suppressed triggers vintage-mismatch warning despite matching IDs). A saturated two-observation/two-coefficient OLS fixture raised ValueError: arange: cannot compute length while bundling. |
| Exceptions (0.7) | Recorded | Build-identity normalisation and stage-count/name details below. No scientific result or production bug fix. |

Execution-build identity (`git_commit`, `package_version`) necessarily changes with the required
commits/version bump, so the run golden explicitly normalises those two keys. JSON whitespace,
manifest creation dates/hashes, scientific values and other dependency/input/binary hashes remain
unchanged. Only digests of text artifacts affected by the listed normalisation are recalculated.
The table defines **nine** middle stages (the prose says ten); the driver uses those exact nine.
Only `_prepare` has early returns, so no unused `state.result` field was added. Existing imported
helpers `_derive_replicates` and `_apply_adjustments` have local aliases to avoid the required stage
names; facade exports still refer to the original helpers. No pure helper was moved.
