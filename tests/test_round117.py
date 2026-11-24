# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 117 tests: offline N39 ACS 2021-2025 release-refresh preflight tooling."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_acs_release_preflight_runs_offline():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/acs_release_preflight.py"), "--target-year", "2025"],
        capture_output=True, text=True, check=True,
    )
    report = json.loads(proc.stdout)
    assert report["target_year"] == 2025
    assert isinstance(report["ready"], bool)
    assert isinstance(report["metadata_vintages"], list)
    for k in ("r-cpi-u-rs", "cpi-u", "c-cpi-u"):
        assert report["price_indexes"][k]["integrity_ok"] is True
    assert report["rpp"]["integrity_ok"] is True
    assert report["crosswalk_error_count"] == 0
