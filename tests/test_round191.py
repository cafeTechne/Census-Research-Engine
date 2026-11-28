# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 191 tests: LaTeX structural linter and zero-CDN interactive 11-cause mortality companion."""
from __future__ import annotations

from pathlib import Path

from census.report_tables import lint_latex

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "studies_output" / "r188_flagship_manuscript"


def test_lint_latex_catches_errors_and_passes_r188_files():
    bad = r"\begin{tabular}{ll}\toprule a & b \\ \end{table}"
    res_bad = lint_latex(bad)
    assert res_bad["ok"] is False and len(res_bad["errors"]) >= 1

    for rel in (
        "tables/table1_11cause_atlas.tex",
        "tables/table2_methodological_pitfalls.tex",
        "manuscript.tex",
    ):
        rep = lint_latex((OUT_DIR / rel).read_text(encoding="utf-8"))
        assert rep["ok"] is True, f"{rel}: {rep}"


def test_interactive_dashboard_offline_zero_cdn():
    html = (OUT_DIR / "dashboard.html").read_text(encoding="utf-8")
    assert "http://" not in html and "https://" not in html
    assert "Drug Overdose" in html and "Firearm" in html and "Stroke" in html
    assert (ROOT / "docs" / "studies" / "r191_interactive_atlas_summary.md").exists()
