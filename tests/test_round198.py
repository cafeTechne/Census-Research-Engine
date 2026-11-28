# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 198 tests: GitHub Actions CI workflow & optional compile_latex_pdf helper."""
from __future__ import annotations

from pathlib import Path

from census.report_tables import compile_latex_pdf

ROOT = Path(__file__).resolve().parents[1]


def test_ci_workflow_exists_and_runs_hygiene_and_doctor():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "release_hygiene_check.py" in ci
    assert "python -m census doctor --verbose --json" in ci
    assert "layer_b_openscholar/tests/" in ci


def test_compile_latex_pdf_graceful_fallback_and_lint_gate(tmp_path: Path):
    good = tmp_path / "good.tex"
    good.write_text("\\documentclass{article}\n\\begin{document}\nHello.\n\\end{document}\n", encoding="utf-8")
    res = compile_latex_pdf(good)
    assert res["ok"] is True

    bad = tmp_path / "bad.tex"
    bad.write_text("\\begin{document}\nHello.\n\\end{table}\n", encoding="utf-8")
    res_bad = compile_latex_pdf(bad)
    assert res_bad["ok"] is False and res_bad["compiled"] is False
