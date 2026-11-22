# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 73: three-level models, fixed-loading indices and the expected-counts helper (N51)."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from census import composite_index, multilevel3, wonder_reference as wr
from census.vital_records import read_wonder_reference

ROOT = Path(__file__).resolve().parents[1]
AUDIT = json.loads((ROOT/"docs/audits/methods73_validation.json").read_text())
REF = ROOT/"tests/fixtures/wonder/national_age_sex.tsv"


def test_flags_equal_the_audit():
    assert AUDIT["criterion_commit"] == "e97e9fc"
    p = AUDIT["passed"]
    assert multilevel3.FIXED_VALIDATED is p["M1"]
    assert multilevel3.SHARES_VALIDATED is False          # M3 is screening only, whatever its result
    assert composite_index.LOADINGS_VALIDATED is p["LI"]


def _three_level(seed=73, G=12):
    rng = np.random.default_rng(seed)
    rows = []
    for g in range(G):
        ug = rng.normal(0, .6)
        for m in range(6):
            um = rng.normal(0, .35)
            for _ in range(8):
                x = rng.normal()
                rows.append(dict(state=f"{g:02d}", county=f"{m:03d}", x=x, y=1+.5*x+ug+um+rng.normal()))
    return pd.DataFrame(rows)


def test_fit_three_level_fields():
    d = _three_level()
    out = multilevel3.fit_three_level("y ~ x", d, ["state", "county"], share_intervals=False)
    assert out["n_top"] == 12 and out["n_middle"] == 72 and out["n"] == len(d)
    assert set(out["shares"]) == {"bottom", "middle", "top"} and abs(sum(out["shares"].values())-1) < 1e-9
    row = out["table"].set_index("term").loc["x"]
    assert row.lower < .5 < row.upper and row.df == 11
    assert out["validated"] is bool(multilevel3.FIXED_VALIDATED)
    assert "share_intervals" not in out
    with pytest.raises(ValueError):
        multilevel3.fit_three_level("y ~ x", d, ["state"])


def test_middle_units_are_nested_within_top():
    d = _three_level()                     # county codes repeat across states: 6 codes, 72 counties
    out = multilevel3.fit_three_level("y ~ 1", d, ["state", "county"], share_intervals=False)
    assert out["n_middle"] == 72


def test_workflow_routes_a_list_and_refuses_two_level_options(tmp_path):
    from census import workflows_microdata as wm
    p = tmp_path/"f.csv"; _three_level().to_csv(p, index=False)
    out = wm.multilevel_model(str(p), "y ~ x", ["state", "county"], share_intervals=False)
    assert out["success"] and out["n_top"] == 12 and "Three-level" in out["summary"]
    bad = wm.multilevel_model(str(p), "y ~ x", ["state", "county"], sampling_se="x")
    assert not bad["success"]


def test_loadings_index():
    rng = np.random.default_rng(1)
    f = pd.DataFrame(dict(GEOID=[f"{i:05d}" for i in range(50)], a=rng.normal(size=50), b=rng.normal(size=50)))
    lw = {"a": .9, "b": .5}
    out = composite_index.build_index(f, ["a", "b"], method="loadings", loadings=lw, standardize=True)
    z = lambda s: (s-s.mean())/s.std(ddof=1)  # noqa: E731
    want = z(.9*z(f.a)+.5*z(f.b))
    got = out["table"].set_index("area").score.reindex(f.GEOID).to_numpy()
    assert np.allclose(got, want.to_numpy(), atol=1e-12)
    assert out["loadings"] == lw and out["validated_scores"] is False      # no replicates
    with pytest.raises(ValueError):
        composite_index.build_index(f, ["a", "b"], method="loadings")
    with pytest.raises(ValueError):
        composite_index.build_index(f, ["a", "b"], method="loadings", loadings={"a": 1.})


def test_expected_counts_both_rules():
    ref = read_wonder_reference(str(REF))["rows"].set_index(["sex", "band"]).loc[wr.band_order()].rate.to_numpy(float)
    names = [wr.band_name(s, b) for s, b in wr.band_order()]
    pops = pd.DataFrame([np.full(20, 100.), np.arange(1, 21)*50.], columns=names, index=["01001", "01003"])
    ten = wr.expected_counts(pops, str(REF), period_years=10)
    assert np.allclose(ten, 10*pops.to_numpy()@ref)
    py = pd.Series({"01001": 20000., "01003": 5000.})
    mix = wr.expected_counts(pops, str(REF), person_years=py)
    assert np.allclose(mix, (pops.to_numpy()@ref)/pops.sum(axis=1).to_numpy()*py.to_numpy())
    with pytest.raises(ValueError):
        wr.expected_counts(pops, str(REF))
    with pytest.raises(ValueError):
        wr.expected_counts(pops[names[::-1]], str(REF), period_years=10)


def test_acs_band_populations_partition_b01001():
    rng = np.random.default_rng(5)
    cols = {f"B01001_{i:03d}E": rng.integers(0, 500, 3) for i in range(1, 50)}
    b = pd.DataFrame(cols, index=["a", "b", "c"])
    bands = wr.acs_band_populations(b)
    cells = [i for i in range(3, 26)]+[i for i in range(27, 50)]
    assert (bands.sum(axis=1).to_numpy() == b[[f"B01001_{i:03d}E" for i in cells]].sum(axis=1).to_numpy()).all()
    assert list(bands.columns) == [wr.band_name(s, x) for s, x in wr.band_order()]


def test_rule_text_mirrored():
    for path in ("docs/agent_protocol.md", "mcp_server.py"):
        assert "Round 73" in (ROOT/path).read_text()
