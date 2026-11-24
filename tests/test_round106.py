# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 106: third-wave exploratory-measure repairs (Lin's CCC Fisher-z jackknife; parametric g-formula)."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from census import agreement, msm
from census import repairs106_core as r106

ROOT = Path(__file__).resolve().parents[1]


def test_round106_audit_matches_engine_flags():
    audit = json.loads((ROOT / "docs/audits/repairs106_validation.json").read_text())
    out = audit["outcomes"]
    assert out["C2_all"] is True and out["M5_all"] is True
    assert out["H2c_all"] is False and out["Q2c_all"] is False and out["E3_all"] is False
    assert msm.GFORMULA_VALIDATED is out["M5_all"]


def test_ccc_jackknife_validated_in_check_agreement():
    rng = np.random.default_rng(1061)
    n = 100
    x = rng.standard_normal(n)
    y = 0.2 + 1.1 * (0.9 * x + np.sqrt(1 - 0.81) * rng.standard_normal(n))
    df = pd.DataFrame({"GEOID": [f"26{i:03d}" for i in range(n)], "a": x, "b": y})
    out = agreement.check_agreement(df, "a", "b")
    assert out["ccc"]["validated"] is True
    assert out["ccc"]["method"] == "jackknife_fisher_z"
    assert out["ccc"]["lower"] < out["ccc"]["estimate"] < out["ccc"]["upper"]


def test_gformula_validated_in_msm():
    from tests.test_round91 import _panel
    df, _ = _panel(seed=106, g=0.5, psi=-2.0, K=12, n=51)
    out = msm.marginal_structural_model(df, "y", "first", ["unemp"], method="gformula")
    assert out["validated"] is True
    assert out["method"] == "gformula_jackknife"
    assert len(out["effects"]) == 3
    for e in out["effects"]:
        assert e["lower"] < e["estimate"] < e["upper"]
