# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 44: OH/PA re-check geometry and outcomes, geography notes, NB2 optimizer fallback."""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from census import manova_counts_core as mc
from census.count_models import _negbin_slope, fit_count_model
from census.spatial_clusters import geography_notes

ROOT = Path(__file__).resolve().parents[1]
warnings.simplefilter("ignore")


def test_ohpa_geometry_is_state_respecting():
    g = json.loads((ROOT/"docs/audits/ohpa_geometry.json").read_text())
    ids = g["coordinates"]["GEOID"]
    assert len(ids) == 155 and {i[:2] for i in ids} == {"39", "42"}
    a = pd.DataFrame(dict(GEOID=ids, cluster=[g["assignment"][i] for i in ids]))
    assert a.cluster.nunique() == 8 and a.cluster.value_counts().min() >= 5
    assert all(s.str[:2].nunique() == 1 for _, s in a.groupby("cluster").GEOID)
    assert len(g["rows"]) == 12 and all(r["reference_n"] == 400000 for r in g["rows"])


def test_outcomes_equal_the_fixed_audit():
    res = json.loads((ROOT/"docs/audits/ohpa_revalidation.json").read_text())
    assert res["passed"] == {"C1": {"binomial": False, "linear": False, "poisson": False}, "G1": True, "G2": True}
    ind = [r for r in res["rows"] if r["design"] == "C1" and r["range_km"] == 0]
    assert all(r["coverage"] >= .86 for r in ind)          # the failure is in the spatially correlated cells


def test_geography_notes():
    a = pd.DataFrame(dict(GEOID=["26001", "26003", "36001", "36003"], cluster=[0, 0, 1, 1]))
    assert geography_notes(a) == []
    b = pd.DataFrame(dict(GEOID=["39001", "42003", "42005", "39007"], cluster=[0, 0, 1, 1]))
    notes = geography_notes(b)
    assert notes[0].startswith("CLUSTERS CROSS") and "[0, 1]" in notes[0]
    assert "outside the IM-8 validation geometry" in notes[1] and "ohpa_revalidation.md" in notes[1]


def test_im_fit_carries_the_geography_note():
    from census.models import fit_replicate
    rng = np.random.default_rng(44); n = 96
    ids = [f"{'39' if i < 48 else '42'}{i:03d}" for i in range(n)]
    f = pd.DataFrame(dict(GEOID=ids, Year=2022, x=rng.normal(size=n)))
    f["y"] = 1+.5*f.x+rng.normal(size=n)
    coords = pd.DataFrame(dict(GEOID=ids, lon=-84+np.arange(n) % 12*.3+np.where(np.arange(n) < 48, 0, 6),
                               lat=40+np.arange(n)//12*.3))
    r = fit_replicate("y ~ x", f, coords=coords, spatial_clusters={"k": 8, "method": "im"}, target="population")
    assert any("outside the IM-8 validation geometry" in s for s in r.notes)


def large_count_case(seed=6, n=150):
    rng = np.random.default_rng(seed)
    x = rng.normal(15, 6, n); E = rng.lognormal(np.log(20000), 1.2, n)
    y = rng.poisson(E*np.exp(-6+.03*x)*rng.gamma(60, 1/60, n)).astype(float)
    return y, np.column_stack((np.ones(n), x, (np.arange(n) > 80).astype(float))), E


def test_negbin_fallback_only_when_the_frozen_core_fails(monkeypatch):
    rng = np.random.default_rng(1); n = 200
    x = rng.normal(size=n); E = np.maximum(5, np.rint(rng.lognormal(np.log(50), 1, n)))
    y = rng.poisson(E*np.exp(.3*x)*rng.gamma(4, .25, n)).astype(float)
    X = np.column_stack((np.ones(n), x))
    assert _negbin_slope(y, X, E) == mc.count_slope(y, X, E, "negbin")
    y, X, E = large_count_case()
    # Non-convergence in the frozen core triggers the Nelder-Mead + BFGS fallback;
    # other ValueErrors must propagate unchanged.
    def _fail_nonconverge(*a, **kw):
        raise ValueError("NB alpha did not converge")
    with monkeypatch.context() as mp:
        mp.setattr(mc, "count_slope", _fail_nonconverge)
        r_fb = _negbin_slope(y, X, E)
    assert abs(r_fb["estimate"]-.03) < .01 and r_fb["lower"] < r_fb["estimate"] < r_fb["upper"]
    def _fail_other(*a, **kw):
        raise ValueError("unrelated error")
    with monkeypatch.context() as mp:
        mp.setattr(mc, "count_slope", _fail_other)
        with pytest.raises(ValueError, match="unrelated error"):
            _negbin_slope(y, X, E)
    r = _negbin_slope(y, X, E)
    assert abs(r["estimate"]-.03) < .01 and r["lower"] < r["estimate"] < r["upper"]
    f = pd.DataFrame(dict(c=y, x=X[:, 1], s=X[:, 2], E=E))
    assert fit_count_model("c ~ x + s", f, "E")["table"].set_index("term").loc["x", "estimate"] == pytest.approx(r["estimate"])


def test_posthoc_report_records_the_preset_reading():
    text = (ROOT/"docs/studies/r44_posthoc_r29.md").read_text()
    assert "author self-review, not independent" in text and "registered results are unchanged" in text.lower()
    assert text.count("| holds |") == 6
