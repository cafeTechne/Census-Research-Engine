# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 67: replication C (NC tract life expectancy and ICE) and SCPC on NC tract geometry."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from census import scpc

ROOT = Path(__file__).resolve().parents[1]
REP = json.loads((ROOT/"docs/audits/r67_nc_ice_replication.json").read_text())
SIM = json.loads((ROOT/"docs/audits/r67_nc_tract_validation.json").read_text())


def test_outcomes_recorded():
    assert REP["criterion_commit"] == "14b78b2" and SIM["criterion_commit"] == "daa1d15"
    assert REP["outcome"] == "partly replicated" and REP["interval"] == "HC3" and REP["n_tracts"] == 1971
    flags = {(k, m): v[m]["replicated"] for k, v in REP["slopes"].items() for m in ("ols", "spatial_error")}
    assert sum(flags.values()) == 5 and not flags[("ice_income_race", "ols")]
    assert not SIM["passed"]["SCPC05"] and not SIM["passed"]["SCPC10"]


def test_tract_level_scpc_is_exploratory():
    rng = np.random.default_rng(67)
    n = 60
    for width in (5, 11):
        ids = [f"{37000+i:05d}" if width == 5 else f"37001{i:06d}" for i in range(n)]
        f = pd.DataFrame(dict(GEOID=ids, x=rng.normal(size=n))); f["y"] = .5*f.x+rng.normal(size=n)
        c = pd.DataFrame(dict(GEOID=ids, lon=rng.uniform(-84, -76, n), lat=rng.uniform(34, 36.5, n)))
        out = scpc.fit_scpc("y ~ x", f, coords=c, rho_bar=.05)   # Round 71: the tract default is now .20
        assert out["validated"] is (width == 5)
        assert any("Round 67" in s for s in out["notes"]) is (width == 11)


def test_rule_text_mirrored():
    for path in ("docs/agent_protocol.md", "mcp_server.py", "docs/recipes/regression_sampling_error.md"):
        assert "Round 67" in (ROOT/path).read_text()
