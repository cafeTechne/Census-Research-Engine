# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 54: OH/PA re-check of Rounds 45-53 spatial designs; IM with 4/6 within-state clusters (flags = audit)."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from census import im_acs, im_clusters_core as imc, spatial_clusters as scl, spatial_eiv

ROOT = Path(__file__).resolve().parents[1]
AUDIT = json.loads((ROOT/"docs/audits/ohpa_revalidation2.json").read_text())


def test_flags_equal_the_fixed_audit():
    p = AUDIT["passed"]
    assert AUDIT["criterion_commit"] == "e42840d"
    assert scl.IM_CLUSTER_COUNT_REPAIR_VALIDATED == {4: p["IM4"], 6: p["IM6"]} == {4: False, 6: False}
    assert scl.VALIDATED_CLUSTER_COUNTS["im"] == (8,)
    assert p["K2a"] and p["K2b"] and p["S1_poisson"] and p["S1_negbin"]          # replicated on OH/PA
    assert p["G2_p3"] and p["G2_p4"] and not p["G2_p5"]
    assert not (p["G1_p3"] or p["G1_p4"] or p["G1_p5"])
    assert p["IM4_miny"] and p["IM6_miny"] and not p["IM8_miny"]                  # informational
    low = [r for r in AUDIT["cells"] if r["problem"] == "C" and r["geometry"] == "miny" and r["coverage"]["IM8"] < .86]
    assert [(r["model"], r["range_km"], r["reliability"]) for r in low] == [("linear", 100, .7)]


def test_geometry_file():
    g = json.loads((ROOT/"docs/audits/im_cluster_counts_geometry.json").read_text())["assignments"]
    for geo, n, states in (("miny", 145, ("26", "36")), ("ohpa", 155, ("39", "42"))):
        for G in ("4", "6"):
            a = pd.Series(g[geo][G])
            assert len(a) == n and a.nunique() == int(G) and a.value_counts().min() >= 5
            st = pd.Series(a.index.str[:2], index=a.index)
            assert all(st[a == c].nunique() == 1 for c in a.unique())            # within-state clusters
            assert set(st) == set(states)


def test_general_core_equals_im_acs_for_eight_clusters():
    rng = np.random.default_rng(54)
    labels = np.repeat(np.arange(8), 12); X = np.column_stack((np.ones(96), rng.normal(size=96)))
    y = 1+.5*X[:, 1]+rng.normal(size=96)
    a = im_acs.summarize(im_acs.cluster_coefficients(X, y, labels, "linear"))
    b = imc.summarize(imc.cluster_coefficients(X, y, labels, "linear"))
    for k in ("estimate", "se", "lower", "upper"):
        assert np.allclose(a[k], b[k])
    c = imc.summarize(imc.cluster_coefficients(X, y, labels % 4, "linear"))
    assert c["df"] == 3


def test_geography_notes_by_kind():
    a = pd.DataFrame(dict(GEOID=["39001", "39003", "42001"], cluster=[0, 0, 1]))
    c1 = " ".join(scl.geography_notes(a))
    counts = " ".join(scl.geography_notes(a, kind="counts"))
    assert "4 or 6 within-state clusters also under-covered" in c1
    assert "replicated on OH/PA" in counts and "under-covered" not in counts
    assert scl.geography_notes(a.assign(GEOID=["26001", "26003", "36001"])) == []


def test_spatial_eiv_note_outside_miny(monkeypatch):
    from tests.test_round46 import several
    f, long, coords, rhs = several(3)
    f = f.assign(GEOID="39"+f.GEOID.str[2:]); long = long.assign(GEOID="39"+long.GEOID.str[2:])
    coords = coords.assign(GEOID="39"+coords.GEOID.str[2:])
    out = spatial_eiv.fit_spatial_eiv(f"y ~ {rhs}", f, long, method="g1", coords=coords, fixed_variables=("y",))
    # Round 58: the note depends on the estimated reliability (gate .8, tests/test_round58.py)
    low = min(out["reliability"].values()) < spatial_eiv.RELIABILITY_GATE
    assert any("EXPLORATORY OUTSIDE MI/NY" in n for n in out["notes"]) is low
    assert any("Outside MI/NY" in n for n in out["notes"]) is (not low)
    out = spatial_eiv.fit_spatial_eiv(f"y ~ {rhs}", f, long, method="g2", coords=coords, fixed_variables=("y",))
    assert not any("EXPLORATORY OUTSIDE MI/NY" in n for n in out["notes"])        # G2 with three replicated


def test_rule_text_mirrored():
    from census import mcp_profiles
    for path in ("docs/agent_protocol.md", "docs/recipes/regression_sampling_error.md", "census/mcp_instructions.py",
                 "docs/recipes/external_health_outcome.md"):
        text = " ".join((ROOT/path).read_text().split())
        assert "Round 54" in text and ("4 or 6" in text)
    assert "Round 54" in " ".join(mcp_profiles.CORE_INSTRUCTIONS.split())
