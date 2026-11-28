# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 193 tests: verify_bundle LaTeX lint integration and python -m census lint-latex CLI."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from census.report_tables import results_bundle, verify_bundle

ROOT = Path(__file__).resolve().parents[1]


def test_verify_bundle_lints_tex_files(tmp_path: Path):
    bdir = tmp_path / "bundle"
    results_bundle(
        str(bdir),
        methods="# Methods\nTest.\n",
        results={"x": 1},
        provenance={"round": 193},
        citation="Test citation.",
        references={"references.bib": "@misc{t, title={T}, year={2026}}\n"},
    )
    # Add a valid LaTeX table and record its digest in bundle.json
    import hashlib

    tdir = bdir / "tables"
    tdir.mkdir(parents=True, exist_ok=True)
    good_p = tdir / "good.tex"
    good_p.write_text(
        "\\begin{tabular}{ll}\n\\toprule\nA & B \\\\\n\\midrule\n1 & 2 \\\\\n\\bottomrule\n\\end{tabular}\n",
        encoding="utf-8",
    )
    meta_p = bdir / "bundle.json"
    meta = json.loads(meta_p.read_text(encoding="utf-8"))
    meta["files"]["tables/good.tex"] = hashlib.sha256(good_p.read_bytes()).hexdigest()
    meta_p.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    ok_res = verify_bundle(str(bdir))
    assert ok_res["ok"] is True, ok_res
    assert ok_res["linted_tex_files"] == 1

    # Corrupt the .tex file -> verify_bundle catches the structural error
    bad_p = tdir / "bad.tex"
    bad_p.write_text("\\begin{tabular}{ll}\n\\toprule\nA & B \\\\\n\\end{table}\n", encoding="utf-8")
    meta["files"]["tables/bad.tex"] = hashlib.sha256(bad_p.read_bytes()).hexdigest()
    meta_p.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    bad_res = verify_bundle(str(bdir))
    assert bad_res["ok"] is False
    assert any("bad.tex" in e for e in bad_res["errors"])


def test_cli_lint_latex_on_r188_manuscript():
    tex_path = ROOT / "studies_output" / "r188_flagship_manuscript" / "manuscript.tex"
    proc = subprocess.run(
        [sys.executable, "-m", "census", "lint-latex", str(tex_path), "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rep = json.loads(proc.stdout)
    assert rep["ok"] is True
    assert rep["checked"] == 1
