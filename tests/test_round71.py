# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 71: tract-level spatial intervals (N49) and the residual-dependence warning."""
import json
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

from census import residual_dependence as rd, scpc, spatial
from census.manifest import validate_manifest

ROOT = Path(__file__).resolve().parents[1]
AUDIT = json.loads((ROOT/"docs/audits/tract_spatial_validation.json").read_text())


def test_flags_equal_the_audit():
    passed = AUDIT["passed"]
    assert AUDIT["criterion_commit"] == "f947f64"
    assert passed["T1_sem"] is None and passed["T4_hc3"] is None
    tract = tuple(r for r, key in ((.20, "T2_scpc20"), (.30, "T2_scpc30")) if passed[key] == "all")
    assert scpc.TRACT_VALIDATED_RHO["ols"] == tract == (.20, .30)
    assert scpc.TRACT_DEFAULT_RHO["ols"] == .20 and "poisson" not in scpc.TRACT_VALIDATED_RHO
    assert scpc.DEFAULT_RHO["ols"] == .05 and scpc.validated_rho("ols", False) == (.05, .10)


def _tract_frame(n=80, seed=71, dependent=False):
    rng = np.random.default_rng(seed)
    ids = [f"26161{i:06d}" for i in range(n)]
    lon, lat = rng.uniform(-84, -83, n), rng.uniform(42, 43, n)
    if dependent:   # a smooth field of location: neighbouring residuals agree
        e = 2*np.sin(3*lon)+2*np.cos(3*lat)
    else:
        e = rng.normal(size=n)
    f = pd.DataFrame(dict(GEOID=ids, x=rng.normal(size=n))); f["y"] = .5*f.x+e
    return f, pd.DataFrame(dict(GEOID=ids, lon=lon, lat=lat))


def test_tract_scpc_default_and_flags():
    f, c = _tract_frame()
    out = scpc.fit_scpc("y ~ x", f, coords=c)
    assert out["rho_bar"] == .20 and out["validated"] and any("Round 71" in s for s in out["notes"])
    assert scpc.fit_scpc("y ~ x", f, coords=c, rho_bar=.30)["validated"]
    assert not scpc.fit_scpc("y ~ x", f, coords=c, rho_bar=.10)["validated"]
    f["E"] = 100.; f["k"] = np.random.default_rng(1).poisson(10, len(f))
    assert not scpc.fit_scpc("k ~ x", f, "poisson", exposure="E", coords=c)["validated"]


def test_warning_fires_only_on_dependent_residuals():
    f, c = _tract_frame(n=300, dependent=True)
    hit = rd.check(f, "y ~ x", coords=c)
    assert hit["p"] < .01 and hit["level"] == "tract"
    msg = rd.note(hit, rd.recommended(hit))
    assert "spatially dependent" in msg and 'spatial="scpc"' in msg and "Round 71" in msg
    g, c2 = _tract_frame(n=300, seed=3)
    miss = rd.check(g, "y ~ x", coords=c2)
    assert miss["p"] >= .01 and rd.note(miss, rd.recommended(miss)) is None
    assert rd.check(f, "y ~ x", coords=c, mode="off") is None


def test_fit_model_adds_the_note(tmp_path):
    from census import workflows_inference as wi
    f, c = _tract_frame(n=300, dependent=True)
    p = tmp_path/"f.csv"; f.to_csv(p, index=False)
    with mock.patch("census.small_spatial.frame_coordinates", return_value=c):
        out = wi.fit_model(str(p), "y ~ x")
        off = wi.fit_model(str(p), "y ~ x", spatial_check="off")
    assert out["success"] and out["spatial_dependence"]["p"] < .01
    assert any("spatially dependent" in s for s in out["notes"])
    assert "spatial_dependence" not in off


def test_auto_mode_never_downloads():
    f, _ = _tract_frame()
    with mock.patch("census.small_spatial.frame_coordinates", side_effect=RuntimeError("offline")):
        assert rd.check(f, "y ~ x") is None


def test_manifest_tract_scpc_rule():
    m = json.loads((ROOT/"examples/manifests/mi_ny_income_education.json").read_text())
    a = next(x for x in m["analyses"] if x["method"] == "fit_replicate")
    a.setdefault("args", {})["spatial_scpc"] = {}
    county = [e for e in validate_manifest(m, resolve=False) if "SCPC" in e or "spatial_scpc" in e]
    assert not county
    m["geography"]["level"] = "tract"
    a["args"]["spatial_scpc"] = {"rho_bar": .05}
    assert any("Round 71 tracts" in e for e in validate_manifest(m, resolve=False))
    a["args"]["spatial_scpc"] = {"rho_bar": .20}
    assert not any("Round 71 tracts" in e for e in validate_manifest(m, resolve=False))


def test_tract_error_model_note():
    assert "Round 71" in spatial.TRACT_ERROR_NOTE and "scpc" in spatial.TRACT_ERROR_NOTE


def test_rule_text_mirrored():
    for path in ("docs/agent_protocol.md", "mcp_server.py", "docs/recipes/regression_sampling_error.md"):
        assert "Round 71" in (ROOT/path).read_text() and "rho_bar .20" in (ROOT/path).read_text()
