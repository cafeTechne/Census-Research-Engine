# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 96: BYM2 Poisson disease mapping."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from census import disease_mapping as dmap
from census import disease_mapping_core as dm

ROOT = Path(__file__).resolve().parents[1]


def _grid(k=8):
    n = k*k
    E = [(i, i+1) for i in range(n) if (i+1) % k] + [(i, i+k) for i in range(n-k)]
    return n, E


def test_scaled_icar_and_connectivity():
    n, E = _grid()
    V, lam = dm.scaled_icar_eigen(n, E)
    assert np.exp(np.mean(np.log((V**2) @ lam))) == pytest.approx(1.0)
    assert np.sum(lam == 0) == 1
    with pytest.raises(ValueError, match="connected"):
        dm.scaled_icar_eigen(4, [(0, 1), (2, 3)])


def test_bym2_recovers_risks_and_shrinks():
    n, E = _grid(10)
    eig = dm.scaled_icar_eigen(n, E)
    rng = np.random.default_rng(3)
    b = dm.simulate_field(rng, eig, .5, .8); Ex = np.full(n, 30.0)
    y = rng.poisson(Ex*np.exp(b)).astype(float)
    f = dm.bym2(y, Ex, eigen=eig)
    for k in ("B1", "B2"):
        assert np.sqrt(np.mean((f[k]["log_rr"]-b)**2)) < np.sqrt(np.mean((np.log((y+.5)/Ex)-b)**2))
        assert (f[k]["lower"] < f[k]["rr"]).all() and (f[k]["rr"] < f[k]["upper"]).all()
    p = dm.exceedance(f["B2"], 1.2)
    assert ((0 <= p) & (p <= 1)).all()


def test_missing_counts_predicted_from_neighbours():
    n, E = _grid()
    f = pd.DataFrame({"GEOID": [f"{i:05d}" for i in range(n)], "y": np.r_[np.nan, np.full(n-1, 20.0)], "E": 20.0})
    out = dmap.disease_map(f, "y", "E", E)
    t = out["table"]
    assert not t.count_used.iloc[0] and t.count_used.iloc[1:].all()
    assert t.ci_upper.iloc[0]-t.ci_lower.iloc[0] > t.ci_upper.iloc[1]-t.ci_lower.iloc[1]
    assert any("suppressed" in n_ for n_ in out["notes"])
    with pytest.raises(ValueError):
        dmap.disease_map(f.assign(E=0.0), "y", "E", E)


def test_validated_flags_match_audit():
    out = json.loads((ROOT/"docs/audits/disease_mapping_validation.json").read_text())["outcome"]
    assert dmap.VALIDATED == {"B1": out["B1"]["passed"], "B2": out["B2"]["passed"]}
    assert dmap.EXCEEDANCE_CALIBRATED == (out["B1"]["calibration_ok"] and out["B2"]["calibration_ok"])


def test_bridge_components():
    import geopandas as gpd
    from shapely.geometry import Point
    from census.workflows_geo import _bridge_components
    g = gpd.GeoDataFrame({"GEOID": ["a", "b", "c", "d"]}, geometry=[Point(0, 0), Point(1, 0), Point(5, 0), Point(6, 0)],
                         crs="EPSG:5070")
    edges, bridges = _bridge_components(g, [(0, 1), (2, 3)])
    assert len(bridges) == 1 and (1, 2) in edges
