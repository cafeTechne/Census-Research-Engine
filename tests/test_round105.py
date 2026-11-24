# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 105: second-wave exploratory-measure repairs (continuous RDD CER bandwidth; propagated misclassification)."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from census import bias_analysis as ba
from census import rdd as rd
from census import repairs105_core as r105

ROOT = Path(__file__).resolve().parents[1]


def test_round105_audit_matches_engine_flags():
    audit = json.loads((ROOT / "docs/audits/repairs105_validation.json").read_text())
    out = audit["outcomes"]
    assert out["R1b_all"] is True and out["M1b_all"] is True
    assert out["H2b_all"] is False and out["Q2b_all"] is False and out["M4_all"] is False
    assert rd.VALIDATED["continuous"] is out["R1b_all"]
    assert ba.VALIDATED["probabilistic_misclassification"] is out["M1b_all"]


def test_continuous_rdd_cer_bandwidth_validated():
    rng = np.random.default_rng(1051)
    n = 3000
    x = rng.uniform(-1.0, 1.0, n)
    y = 0.5 * x + 2.0 * (x ** 2) + 3.0 * (x ** 3) + 0.5 * (x >= 0.0) + rng.normal(0.0, 0.5, n)
    df = pd.DataFrame({"x": x, "y": y})
    r = rd.regression_discontinuity(df, "y", "x", 0.0)
    assert r["validated"] is True
    assert r["lower"] < 0.5 < r["upper"]

    # Custom bandwidth stays exploratory
    r_custom = rd.regression_discontinuity(df, "y", "x", 0.0, bandwidth=0.4)
    assert r_custom["validated"] is False


def test_probabilistic_misclassification_propagated_validated():
    r = ba.misclassification(360, 1640, 280, 1720, 0.85, 0.92, kind="outcome", sd=0.03, draws=3000)
    assert r["validated"] is True
    assert r["probabilistic"]["method"] == "propagated_sampling"
    assert r["probabilistic"]["rr"]["lower"] < r["probabilistic"]["rr"]["median"] < r["probabilistic"]["rr"]["upper"]
    # Total-error interval must be wider than systematic-only interval
    assert (r["probabilistic"]["rr"]["upper"] - r["probabilistic"]["rr"]["lower"] >
            r["probabilistic"]["rr"]["systematic_upper"] - r["probabilistic"]["rr"]["systematic_lower"])

    # Simple point correction without sd stays unvalidated (no interval)
    r_pt = ba.misclassification(360, 1640, 280, 1720, 0.85, 0.92, kind="outcome")
    assert r_pt["validated"] is False
