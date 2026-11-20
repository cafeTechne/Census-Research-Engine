# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 59: effective-n partial correlations; Round 48 correlations and alpha on OH/PA (flags = audit)."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from census import rank_methods as rm, small_spatial as ss, small_spatial_core as ssc
from census.partial_neff_core import partial_neff

ROOT = Path(__file__).resolve().parents[1]
AUDIT = json.loads((ROOT/"docs/audits/spatial_correlation_validation.json").read_text())


def test_flags_equal_the_fixed_audit():
    p = AUDIT["passed"]
    assert AUDIT["criterion_commit"] == "669a506"
    assert ss.NEFF_CORRELATION_VALIDATED["partial"] is p["P1"] is True and p["P0"] is False
    for m in ("spearman", "kendall", "pearson"):
        assert ss.OHPA_REPLICATED[m] is p[f"C1_{m}_ohpa"]
    assert ss.OHPA_REPLICATED["alpha"] is p["A3_ohpa"] and ss.OHPA_REPLICATED["partial"] is p["P1"]


def test_ohpa_targets_file():
    t = json.loads((ROOT/"docs/audits/ohpa_correlation_targets.json").read_text())
    assert t["geometry"] == "ohpa" and len(t["rank_rows"]) == 8 and len(t["index_rows"]) == 8
    assert all(set(r["observed"]) == {"pearson", "spearman", "kendall", "partial"} for r in t["rank_rows"])


def field(n, rng, scale=1.):
    lon, lat = rng.uniform(-84, -80, n), rng.uniform(39, 42, n)
    from spatial_hac_validation import haversine_matrix
    D = haversine_matrix(lon, lat)
    L = np.linalg.cholesky(np.exp(-D/150)+1e-9*np.eye(n))
    return D, L


def test_partial_neff_by_hand():
    import sys; sys.path.insert(0, str(ROOT/"scripts"))
    rng = np.random.default_rng(59); n = 120
    D, L = field(n, rng)
    z = L @ rng.standard_normal(n); x = .5*z+L @ rng.standard_normal(n); y = .3*x+.4*z+L @ rng.standard_normal(n)
    cls = ssc.class_index(D)
    out = partial_neff(x, y, z, cls)
    Zm = np.column_stack((np.ones(n), z))
    rx = x-Zm @ np.linalg.lstsq(Zm, x, rcond=None)[0]; ry = y-Zm @ np.linalg.lstsq(Zm, y, rcond=None)[0]
    ne = ssc.effective_n(rx, ry, cls)
    r = rm.coefficient(x, y, "partial", z)
    half = 1.6448536269514722*np.sqrt(1/(ne-4))
    assert out["estimate"] == pytest.approx(r) and out["n_eff"] == pytest.approx(ne) and ne < n
    assert out["upper"] == pytest.approx(np.tanh(np.arctanh(r)+half))
    iid = rm.correlation_interval(x, y, "partial", 1, .90, z=z)
    assert out["upper"]-out["lower"] > iid["upper"]-iid["lower"]           # wider under spatial dependence


def test_engine_partial_with_coords():
    import sys; sys.path.insert(0, str(ROOT/"scripts"))
    from census.correlation import validated_correlations
    from census.simulation import make_replicates, replicate_long
    rng = np.random.default_rng(5); n = 100
    D, L = field(n, rng)
    ids = [f"39{i:03d}" for i in range(n)]
    vals = np.column_stack([L @ rng.standard_normal(n) for _ in range(3)])+5
    se = np.full((n, 3), .2)
    reps = make_replicates(vals, se, rng)
    f = pd.DataFrame(vals, columns=["a", "b", "c"]); f.insert(0, "GEOID", ids); f["Year"] = 2024
    r = replicate_long(ids, ["a", "b", "c"], vals, reps); r["Year"] = 2024
    lonlat = rng.uniform(-84, -80, n), rng.uniform(39, 42, n)
    coords = pd.DataFrame(dict(GEOID=ids, lon=lonlat[0], lat=lonlat[1]))
    out = validated_correlations(f, ["a", "b"], "partial", replicates=r, controls=["c"], coords=coords)
    assert bool(out.validated.iloc[0]) and "Round 59" in out.note.iloc[0] and "n_eff" in out


def test_rule_text_mirrored():
    from census import mcp_profiles
    for path in ("docs/agent_protocol.md", "docs/recipes/rank_methods.md"):
        text = " ".join((ROOT/path).read_text().split())
        assert "Round 59" in text and "partial" in text
    assert "partial too, Round 59" in mcp_profiles.CORE_INSTRUCTIONS
    assert "partial stays exploratory" not in (ROOT/"docs/agent_protocol.md").read_text()
