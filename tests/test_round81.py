# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 81: Kulldorff Poisson spatial scan."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from census import scan as sn, scan_core as sc

ROOT = Path(__file__).resolve().parents[1]
AUDIT = json.loads((ROOT/"docs/audits/scan_validation.json").read_text())
GEOM = pd.read_csv(ROOT/"docs/audits/scan_geometry.csv", dtype={"GEOID": str})


def _frame(rr=2.0, seed=0):
    g = GEOM[GEOM.pair == "MINY"].reset_index(drop=True)
    mu = g.population/g.population.mean()*20
    D = sc.distances(g.lon.to_numpy(), g.lat.to_numpy())
    members = np.argsort(D[list(g.GEOID).index("26065")], kind="stable")[:3]
    lam = mu.to_numpy().copy(); lam[members] *= rr
    cases = np.random.default_rng(seed).poisson(lam)
    return g.assign(cases=cases, pop=g.population), set(g.GEOID[members])


def test_flags_equal_the_audit():
    assert sn.K1_VALIDATED is AUDIT["passed"]["K1"] is True
    nulls = [r["rejection"] for r in AUDIT["rows"] if r["kind"] == "null"]
    assert len(nulls) == 6 and all(.07 <= r <= .13 for r in nulls)
    assert "Committed before the full run" in (ROOT/"docs/audits/scan_validation_criterion.md").read_text()


def test_llr_by_hand():
    v = sc._llr(np.array(30.), np.array(20.), np.array(100.))
    assert v == pytest.approx(30*np.log(30/20)+70*np.log(70/80))
    assert sc._llr(np.array(10.), np.array(20.), np.array(100.)) == 0


def test_finds_planted_cluster(monkeypatch):
    f, truth = _frame()
    coords = GEOM[["GEOID", "lon", "lat"]]
    monkeypatch.setattr(sn, "_coords", lambda frame, year: coords)
    r = sn.spatial_scan(f, "cases", population="pop", replicates=199)
    assert set(r["primary"]["counties"]) == truth and r["primary"]["p_value"] <= .01
    assert not r["validated_p"]  # 199 replicates is outside the validated setting
    r = sn.spatial_scan(f, "cases", population="pop", prespecified=True)
    assert r["validated_p"] and r["confirmatory"]
    noisy = sn.spatial_scan(f.assign(pop_se=f["pop"]*.05), "cases", population="pop", replicates=199)
    assert any("inflate false clusters" in n for n in noisy["notes"]) and not noisy["validated_p"]


def test_refusals(monkeypatch):
    f, _ = _frame()
    monkeypatch.setattr(sn, "_coords", lambda frame, year: GEOM[["GEOID", "lon", "lat"]])
    bad = f.astype({"cases": float}); bad.loc[0, "cases"] = np.nan
    with pytest.raises(ValueError, match="never imputed"):
        sn.spatial_scan(bad, "cases", population="pop")
    with pytest.raises(ValueError, match="exclude_rule"):
        sn.spatial_scan(bad, "cases", population="pop", exclude=[bad.GEOID[0]])
    r = sn.spatial_scan(bad, "cases", population="pop", exclude=[bad.GEOID[0]], exclude_rule="suppressed",
                        replicates=99)
    assert r["counties"] == len(f)-1
    with pytest.raises(ValueError, match="exactly one"):
        sn.spatial_scan(f, "cases")
