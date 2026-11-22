# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 79: Oaxaca-Blinder and Fairlie decompositions on PUMS with SDR replicate weights."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from census import decomposition as dp, decomposition_core as dc

ROOT = Path(__file__).resolve().parents[1]
AUDIT = json.loads((ROOT/"docs/audits/decomposition_validation.json").read_text())


def _pums(n=2400, seed=0):
    rng = np.random.default_rng(seed)
    black = rng.random(n) < .4
    age = rng.normal(40-3*black, 10, n).round()
    pov = np.clip(rng.normal(300-80*black, 120, n), 0, 501)
    schl = np.digitize(rng.normal(-.4*black, 1, n), [-1, 0, 1])+16
    p = 1/(1+np.exp(-(-2+.6*black-.004*(pov-250)-.2*(schl-17))))
    hicov = np.where(rng.random(n) < p, 2, 1)
    df = pd.DataFrame(dict(RAC1P=np.where(black, 2, 1), HISP=1, AGEP=age, POVPIP=pov, SCHL=schl, HICOV=hicov,
                           WAGP=np.exp(10+.01*age+.002*pov+rng.normal(0, .5, n)), PWGTP=rng.uniform(20, 80, n).round()))
    for r in range(1, 81):
        df[f"PWGTP{r}"] = (df.PWGTP*rng.uniform(.5, 1.5, n)).round()
    return df


def test_flags_equal_the_audit():
    out = AUDIT["outcome"]
    assert dp.VALIDATED_FROM == {k: v["validated_from"] for k, v in out.items()}
    assert AUDIT["draws"] == 1000 and AUDIT["orderings"]["draw"] == 10
    assert "Committed before the full run" in (ROOT/"docs/audits/decomposition_validation_criterion.md").read_text()


def test_oaxaca_identities_and_invariance():
    rng = np.random.default_rng(0); n = 3000
    g = (rng.random(n) < .4).astype(int); x = rng.normal(-.5*g, 1); cat = np.digitize(rng.normal(.4*g, 1), [-1, 0, 1])
    y = 1+.5*x+.3*cat+.3*g+rng.normal(0, 1, n); w = rng.uniform(.5, 2, n)
    blocks = {"x": [1], "cat": [2, 3, 4]}
    for ref in (0, 2):
        D = np.eye(4)[(cat+ref) % 4][:, 1:]
        o = dc.oaxaca(y, np.column_stack([np.ones(n), x, D]), g, w, blocks, ("cat",))
        assert o["explained"]+o["unexplained"] == pytest.approx(o["gap"])
        assert o["unexplained:x"]+o["unexplained:cat"]+o["unexplained:intercept"] == pytest.approx(o["unexplained"])
        if ref == 0:
            first = o
        else:
            assert o["unexplained:cat"] == pytest.approx(first["unexplained:cat"])


def test_pums_decomposition_linear_and_logit():
    df = _pums()
    lin = dp.pums_decomposition(df, "WAGP", "RAC1P == 2", "RAC1P == 1", ["AGEP", "POVPIP"], ["SCHL"])
    t = lin["table"].set_index("component")
    assert t.loc["explained", "validated"] and not t.loc["explained:AGEP", "validated"]  # 960 < 1000 records in B
    assert t.loc["gap", "estimate"] == pytest.approx(t.loc["explained", "estimate"]+t.loc["unexplained", "estimate"])
    lg = dp.pums_decomposition(df, "HICOV == 2", "RAC1P == 2", "RAC1P == 1", ["POVPIP"], ["SCHL"], model="logit",
                               orderings=10)
    t = lg["table"].set_index("component")
    assert t.loc["explained", "estimate"] > 0 and not t.loc["explained", "validated"]
    assert any("not a causal effect" in n for n in lg["notes"])


def test_refusals():
    df = _pums()
    with pytest.raises(ValueError, match="mutually exclusive"):
        dp.pums_decomposition(df, "WAGP", "RAC1P == 2", "RAC1P >= 1", ["AGEP"])
    with pytest.raises(ValueError, match="0/1"):
        dp.pums_decomposition(df, "WAGP", "RAC1P == 2", "RAC1P == 1", ["AGEP"], model="logit")
    with pytest.raises(ValueError, match="covariate"):
        dp.pums_decomposition(df, "WAGP", "RAC1P == 2", "RAC1P == 1")
