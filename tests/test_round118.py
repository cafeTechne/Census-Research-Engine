# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 118 test: verifies pre-commit release hygiene audit passes cleanly."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_release_hygiene_check_passes():
    proc = subprocess.run([sys.executable, str(ROOT / "scripts/release_hygiene_check.py")],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = json.loads(proc.stdout)
    assert report["ok"] is True
    assert report["manifest_methods"] == 28
    assert report["errors"] == []
