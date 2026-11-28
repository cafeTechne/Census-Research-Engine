# Plan — Round 193: `verify_bundle` LaTeX Lint Integration & `lint-latex` CLI (`v0.189.0`)

## 1. Strategic Objective
Wire `lint_latex()` directly into `census.report_tables.verify_bundle()` so any `.tex` file inside a results bundle is structurally verified alongside SHA-256 hashes, and expose `python -m census lint-latex <path> [--json]` for standalone table/manuscript checking.

## 2. Exact File Contracts
1. `census/report_tables.py`: In `verify_bundle()`, lint any `.tex` files found in `bundle_dir` (including `tables/*.tex`) using `lint_latex()`, recording `linted_tex_files` and appending any LaTeX errors to `errors`.
2. `census/__main__.py`: Add `lint-latex` subcommand accepting one or more `.tex` file paths + `--json`.
3. `tests/test_round193.py` & `docs/audits/round193_compatibility.md`.

## 3. Acceptance Gates
1. `verify_bundle()` catches a broken `.tex` file inside a bundle (`ok: false`) and passes valid `.tex` files (`ok: true`).
2. `python -m census lint-latex studies_output/r188_flagship_manuscript/manuscript.tex --json` exits `0` with `"ok": true`.
3. `pytest -q tests/test_round193.py` passes with 0 failures.

## 4. Iteration Log
- *2026-11-27:* Plan drafted.
- *2026-11-27:* Integrated `lint_latex()` into `census/report_tables.py:verify_bundle()` and added `python -m census lint-latex <paths...> [--json]` CLI subcommand. Verified via `tests/test_round193.py`.
