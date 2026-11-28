# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 197 tests: Age-structure (% 65+) & urban-rural confounding resolution across 11 WONDER causes."""
from __future__ import annotations

import json
from pathlib import Path

from census.report_tables import verify_bundle

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "studies_output" / "r197_age_urban_confounding"


def test_r197_age_urban_confounding_study_and_bundle():
    summary = json.loads((OUT_DIR / "summary.json").read_text(encoding="utf-8"))
    assert summary["cause_count"] == 11
    assert summary["ny_pa_adjusted_rr_above_1_count"] >= summary["ny_pa_crude_rr_below_1_count"] or summary["ny_pa_adjusted_rr_above_1_count"] >= 8
    assert (ROOT / "docs" / "studies" / "r197_age_urban_confounding_study.md").exists()
    ver = verify_bundle(str(OUT_DIR / "bundle"))
    assert ver["ok"] is True and ver["errors"] == []
