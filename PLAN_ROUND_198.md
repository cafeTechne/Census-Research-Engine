# Plan — Round 198 (N133): GitHub Actions Offline CI Workflow & Optional LaTeX PDF Compiler Check (`v0.194.0`)

## 1. Strategic Objective
Automate continuous quality verification via a clean GitHub Actions CI workflow (`.github/workflows/ci.yml`) covering `release_hygiene_check.py`, `python -m census doctor --verbose --json`, `python -m census lint-latex`, Layer B isolation tests, and offline Layer A unit/contract tests, and add an optional `compile_latex_pdf()` helper in `census/report_tables.py`.

## 2. Exact File Contracts
1. `.github/workflows/ci.yml`: Offline CI workflow (Python 3.12, installs `requirements.txt` + `pytest`, runs hygiene, doctor, lint-latex, Layer B tests, and core/contract tests).
2. `census/report_tables.py`: Add `compile_latex_pdf(tex_path, out_dir=None)` which detects `tectonic` or `pdflatex` on `PATH`, runs `lint_latex()` first, compiles if a TeX engine is present, or returns `{"ok": True, "compiled": False, "reason": "no_latex_compiler_on_path"}` cleanly when absent.
3. `tests/test_round198.py` & `docs/audits/round198_compatibility.md`.

## 3. Iteration Log
- *2026-11-27:* Plan drafted from roadmap item `N133`.
