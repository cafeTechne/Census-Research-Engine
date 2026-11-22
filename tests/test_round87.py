# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 87: ecologic versus individual-level associations on PUMS."""
import json
from pathlib import Path

import numpy as np
import pytest

from census import ecologic as eg, ecologic_core as ec

ROOT = Path(__file__).resolve().parents[1]
AUDIT = json.loads((ROOT/"docs/audits/ecologic_validation.json").read_text())


def test_flags_equal_the_audit():
    o = AUDIT["outcome"]
    assert (eg.VALIDATED_FROM["C1"] is None) == (not o["C1"]["passed"] and not o["C1"]["gated"])
    assert (eg.VALIDATED_FROM["C2"] is None) == (not o["C2"]["passed"] and not o["C2"]["gated"])
    assert (eg.VALIDATED_FROM["C1l"] == 5000) == o["C1l"]["passed"]
    assert "Committed before the full run" in (ROOT/"docs/audits/ecologic_validation_criterion.md").read_text()


def _data(seed=0, n=20000, J=40, contextual=.3):
    rng = np.random.default_rng(seed)
    area = rng.integers(0, J, n)
    mu = rng.standard_normal(J)
    x = mu[area]+rng.standard_normal(n)
    y = .5*x+contextual*mu[area]+rng.standard_normal(n)
    W = np.column_stack([np.ones(n)]+[1+.2*rng.standard_normal(n) for _ in range(80)])
    return y, x, area, W


def test_decomposition_recovers_truth_and_identity():
    y, x, area, W = _data()
    r, J = ec.decompose(y, x, area, W)
    assert J == 40 and r["within"][0] == pytest.approx(.5, abs=.03)
    assert r["contextual"][0] == pytest.approx(r["between"][0]-r["within"][0])
    assert r["ecologic"][0] == pytest.approx(r["between"][0], abs=.05)  # no covariates: C2 ~ between
    assert r["within"][2] < r["within"][0] < r["within"][3]


def test_ecologic_check_flags():
    y, x, area, W = _data(n=8000)
    out = eg.ecologic_check(y, x, area, W)
    assert out["validated"] == {"within_between_contextual": False, "ecologic_gap": False}
    yb = (y > np.median(y)).astype(float)
    outb = eg.ecologic_check(yb, x, area, W, binary=True)
    assert outb["validated"]["logit"] is True and "logit" in outb
    assert any("not proof of an area cause" in n for n in out["notes"])
