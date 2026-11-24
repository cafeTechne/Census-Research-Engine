# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 113 test: confirms M3c failed its pre-set G_top >= 49 criterion and was not promoted."""
import json
from pathlib import Path

from census import multilevel3 as m3

ROOT = Path(__file__).resolve().parents[1]


def test_round113_m3c_failed_and_not_promoted():
    audit = json.loads((ROOT / "docs/audits/repairs113_validation.json").read_text())
    assert audit["verdicts"]["M3c"] is False
    assert m3.SHARES_VALIDATED is False
