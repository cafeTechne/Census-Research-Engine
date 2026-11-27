# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 188 tests: Flagship 11-cause county mortality manuscript, 3 PDF/SVG/PNG figures, 2 booktabs tables, verify_bundle."""
from __future__ import annotations

import json
from pathlib import Path

from census.report_tables import verify_bundle

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "studies_output" / "r188_flagship_manuscript"


def test_r188_flagship_manuscript_artifacts_and_bundle():
    summary = json.loads((OUT_DIR / "summary.json").read_text(encoding="utf-8"))
    assert summary["cause_count"] == 11

    for stem in (
        "fig1_mortality_poverty_forest",
        "fig2_bym2_shrinkage_spatial",
        "fig3_methodological_pitfalls",
    ):
        for ext in ("pdf", "svg", "png"):
            p = OUT_DIR / "figures" / f"{stem}.{ext}"
            assert p.exists() and p.stat().st_size > 1000, f"missing or empty figure {p}"

    for tbl in ("table1_11cause_atlas.tex", "table2_methodological_pitfalls.tex"):
        txt = (OUT_DIR / "tables" / tbl).read_text(encoding="utf-8")
        assert r"\toprule" in txt and r"\midrule" in txt and r"\bottomrule" in txt
        assert r"\begin{tabular}" in txt and r"\end{tabular}" in txt

    bib = (OUT_DIR / "references.bib").read_text(encoding="utf-8")
    assert "@article{riebler2016bym2" in bib and "@article{muller2022scpc" in bib
    assert (OUT_DIR / "manuscript.tex").exists()
    assert (OUT_DIR / "manuscript.md").exists()
    assert (ROOT / "docs" / "studies" / "r188_flagship_manuscript.md").exists()

    ver = verify_bundle(OUT_DIR / "bundle")
    assert ver["ok"] is True, ver
    assert ver["errors"] == []
