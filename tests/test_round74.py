# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 74: replication suite (N52). Offline checks of the specs and comparisons; the full rerun is live."""
import json
import os
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd
import pytest

from census import replications as rep

ROOT = Path(__file__).resolve().parents[1]
LIVE = os.getenv("CENSUS_LIVE_TESTS") == "1"


def test_every_spec_validates():
    files = sorted(p.stem for p in (ROOT/"docs/replications").glob("*.json"))
    assert files == sorted(rep.IDS)
    for rid in rep.IDS:
        spec = rep.load_spec(rid)
        assert rep.validate_spec(spec) == [], rid
        assert spec["id"] == rid and spec["label"] == "replication rerun"
        assert (ROOT/spec["original"]["audit"]).exists()


def test_bad_specs_are_refused():
    spec = rep.load_spec("state_gini")
    assert any("label" in e for e in rep.validate_spec(dict(spec, label="registered study")))
    assert any("tolerance" in e for e in rep.validate_spec(dict(spec, tolerance={"kind": "loose", "value": 1})))
    assert any("data" in e for e in rep.validate_spec(dict(spec, data="scraped")))
    with pytest.raises(ValueError):
        rep.load_spec("not_a_replication")


def test_original_headlines_equal_the_audits():
    a = json.loads((ROOT/"docs/audits/r66_numeric_replication.json").read_text())
    b = rep.load_spec("state_gini")["original"]["headline"]
    assert b == {r["state"]: r["primary_negatives_to_zero_estimate"] for r in a["B"]["table"]}
    assert rep.load_spec("chr_segregation")["original"]["headline_counts"]["counties_compared"] == 2055
    c = json.loads((ROOT/"docs/audits/r67_nc_ice_replication.json").read_text())
    h = rep.load_spec("nc_ice")["original"]["headline"]
    assert h == {f"{v}/{m}": r[m]["estimate"] for v, r in c["slopes"].items() for m in ("ols", "spatial_error")}


def test_tolerances_fixed_by_the_plan():
    tol = {rid: rep.load_spec(rid)["tolerance"] for rid in rep.IDS}
    assert tol["chr_segregation"] == dict(tol["chr_segregation"], kind="max_abs_vs_published", value=1e-6)
    assert tol["state_gini"]["value"] == .0005 and tol["nc_ice"]["value"] == .001
    assert tol["le_variance"]["value"] == .1 and tol["monnat_d"]["value"] == .05
    assert all(tol[r]["kind"] == "each_within_original" for r in rep.IDS if r != "chr_segregation")


def test_compare_agrees_differs_and_missing():
    spec = dict(tolerance={"kind": "each_within_original", "value": .001, "text": ""},
                original={"headline": {"a": 1.0, "b": 2.0}})
    assert rep.compare(spec, {"a": 1.0005, "b": 2.0})["status"] == "agrees"
    out = rep.compare(spec, {"a": 1.01, "b": 2.0})
    assert out["status"] == "differs" and list(out["beyond_tolerance"]) == ["a"]
    out = rep.compare(spec, {"a": 1.0})
    assert out["status"] == "differs" and out["n_missing"] == 1
    pub = dict(tolerance={"kind": "max_abs_vs_published", "value": 1e-6, "text": ""}, original={"headline": {}})
    assert rep.compare(pub, {"x": 3.0}, published={"x": 3.0})["status"] == "agrees"


def test_absent_data_is_skipped_not_failed():
    def absent(spec, client=None):
        raise rep.Unavailable("WONDER exports are not present")
    with mock.patch.dict(rep.RUNNERS, {"state_gini": absent}):
        out = rep.run("state_gini")
    assert out == {"id": "state_gini", "status": "skipped", "reason": "WONDER exports are not present"}


def test_gini_expression_equals_round66_clipping():
    """The engine route's income expression reproduces Round 66's primary (negatives set to zero)."""
    from census.pums_inequality import pums_inequality
    rng = np.random.default_rng(74)
    n = 600
    h = pd.DataFrame(dict(HINCP=np.round(rng.lognormal(10.8, .9, n))*np.where(rng.random(n) < .02, -1, 1),
                          ADJINC=1042311., TYPEHUGQ=np.where(rng.random(n) < .03, 2, 1), NP=rng.integers(0, 5, n),
                          WGTP=rng.integers(5, 40, n).astype(float)))
    for k in range(1, 81):
        h[f"WGTP{k}"] = h.WGTP*rng.uniform(.5, 1.5, n)
    h.loc[:5, "HINCP"] = np.nan
    spec = rep.load_spec("state_gini")["frame"]
    eng = pums_inequality(h, spec["var"], weight="housing", where=spec["where"])
    hand = h[(h.TYPEHUGQ == 1) & (h.NP > 0) & h.HINCP.notna()].copy()
    hand["inc"] = (hand.HINCP*hand.ADJINC/1e6).clip(lower=0)
    ref = pums_inequality(hand, "inc", weight="housing")
    g = lambda r: r["table"].set_index("measure").loc["gini", "estimate"]  # noqa: E731
    assert g(eng) == pytest.approx(g(ref), abs=1e-12)


def test_recipe_lists_every_spec():
    from census import recipes
    out = recipes.get_recipe("replications")
    assert out["success"] and all(f"`{rid}`" in out["steps"] for rid in rep.IDS)


@pytest.mark.skipif(not LIVE, reason="live: CENSUS_LIVE_TESTS=1 (Census API caches, CHR, USALEEP, PUMS)")
@pytest.mark.parametrize("rid", ["chr_segregation", "state_gini", "nc_ice", "le_variance"])
def test_live_rerun_agrees(rid):
    assert rep.run(rid)["status"] == "agrees"
