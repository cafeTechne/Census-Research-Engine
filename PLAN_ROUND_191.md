# Plan — Round 191: LaTeX Lint Verifier & Offline Interactive 11-Cause Mortality Atlas Companion (`v0.187.0`)

## 1. Strategic Objective
Add automated LaTeX table/manuscript structural verification (`lint_latex_tables`) to `census/report_tables.py` and generate a self-contained, zero-CDN offline interactive HTML companion (`studies_output/r188_flagship_manuscript/dashboard.html`) + summary doc (`docs/studies/r191_interactive_atlas_summary.md`) for the 11-cause county mortality manuscript.

## 2. Exact File Contracts
1. `census/report_tables.py`:
   - Add `lint_latex(text: str) -> Dict[str, Any]` verifying balanced `\begin{...}`/`\end{...}` environments, matched braces, unescaped `%` / `$` inside tabular cells, and booktabs rule order (`\toprule` -> `\midrule` -> `\bottomrule`).
2. `scripts/r191_manuscript_companion.py`:
   - Reads `studies_output/r188_flagship_manuscript/summary.json`, lints `table1_11cause_atlas.tex`, `table2_methodological_pitfalls.tex`, and `manuscript.tex`, and generates a zero-dependency interactive HTML dashboard (`studies_output/r188_flagship_manuscript/dashboard.html`) with client-side sorting/filtering across all 11 causes + the 4 methodological pitfalls.
   - Writes `docs/studies/r191_interactive_atlas_summary.md`.
3. `tests/test_round191.py` & `docs/audits/round191_compatibility.md`.

## 3. Acceptance Gates
1. `lint_latex` passes with `ok: true` and `0` errors on all Round 188 `.tex` artifacts.
2. `studies_output/r188_flagship_manuscript/dashboard.html` is generated offline with zero external CDN `<script>`/`<link>` tags.
3. `pytest -q tests/test_round191.py` passes with 0 failures.

## 4. Iteration Log
- *2026-11-27:* Plan drafted after `v0.185.0` local commit & tag.
- *2026-11-27:* Added `lint_latex()` in `census/report_tables.py` and ran `scripts/r191_manuscript_companion.py`, verifying all 3 Round 188 `.tex` files with 0 errors and generating zero-CDN offline interactive `studies_output/r188_flagship_manuscript/dashboard.html` + `docs/studies/r191_interactive_atlas_summary.md`. Verified via `tests/test_round191.py`.
