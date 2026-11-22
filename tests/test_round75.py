# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 75: manifest multilevel method, indices block, person-years expected counts, tract coordinates, recipes."""
import copy
import os
from unittest import mock

import numpy as np
import pandas as pd
import pytest

from census.manifest import load_manifest, run_manifest, validate_manifest
from census.manifest import methods as mm, round75 as r75
from census.replicate import REPLICATE_COLUMNS
from tests.test_manifest import EXAMPLE, FakeClient

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _errs(m):
    return validate_manifest(m, resolve=False)


def _three_level(seed=75, G=12):
    rng = np.random.default_rng(seed)
    rows = []
    for g in range(G):
        ug = rng.normal(0, .6)
        for c in range(6):
            uc = rng.normal(0, .35)
            for t in range(8):
                x = rng.normal()
                rows.append(dict(GEOID=f"{g:02d}{c:03d}{t:06d}", x=x, y=1+.5*x+ug+uc+rng.normal()))
    return pd.DataFrame(rows)


# ---- multilevel -------------------------------------------------------------------------------------------------

def test_multilevel_validation():
    m = load_manifest(EXAMPLE)
    m["analyses"] = [dict(id="ml", method="multilevel", formula="income ~ pop", groups=["state_fips", "county_fips"])]
    m["hypotheses"] = [dict(id="H1", analysis="ml", statistic="coefficient", term="pop", direction="greater",
                            statement="s")]
    assert _errs(m) == []
    bad = copy.deepcopy(m); bad["analyses"][0]["groups"] = ["county_fips", "county_fips"]
    assert any("two distinct" in e for e in _errs(bad))
    bad = copy.deepcopy(m); bad["analyses"][0]["args"] = {"target": "these_areas"}
    assert any("take no args" in e for e in _errs(bad))
    two = copy.deepcopy(m); two["analyses"][0]["groups"] = "county_fips"; two["analyses"][0]["args"] = {"sampling_se": True}
    assert _errs(two) == []
    two["analyses"][0]["groups"] = "nope"
    assert any("not a manifest variable" in e for e in _errs(two))


def test_three_level_runner_and_statistic():
    d = r75.with_geo_groups(_three_level(), {"state_fips", "county_fips"})
    assert d.state_fips.nunique() == 12 and d.county_fips.nunique() == 72
    res = mm._run_multilevel(dict(formula="y ~ x", groups=["state_fips", "county_fips"]), {}, d, .9, None, "holm", {})
    s = mm._stat_coefficient({"term": "x"}, res)
    assert s["ci_lower"] < .5 < s["ci_upper"] and "confirmatory_refusal" not in s
    assert res.diagnostics["three_level"]["n_top"] == 12 and res.diagnostics["three_level"]["validated"] is True
    from census.multilevel3 import fit_three_level
    ref = fit_three_level("y ~ x", d, ["state_fips", "county_fips"], share_intervals=False)["table"].set_index("term")
    assert s["estimate"] == pytest.approx(ref.loc["x", "estimate"]) and s["ci_upper"] == pytest.approx(ref.loc["x", "upper"])
    assert any("not included" in n for n in res.notes)


def test_two_level_runner():
    d = r75.with_geo_groups(_three_level(), {"county_fips"})
    res = mm._run_multilevel(dict(formula="y ~ x", groups="county_fips"), {}, d, .9, None, "holm", {})
    assert res.coefficients.set_index("term").loc["x", "ci_lower"] < .5


# ---- indices ----------------------------------------------------------------------------------------------------

def _index_manifest():
    m = load_manifest(EXAMPLE)
    m["indices"] = [dict(name="size_index", indicators=["income", "pop"], method="loadings",
                         loadings={"income": .8, "pop": .6}, standardize=True)]
    return m


def test_index_validation_and_circularity():
    m = _index_manifest()
    assert _errs(m) == []
    bad = copy.deepcopy(m); bad["indices"][0]["loadings"] = {"income": .8}
    assert any("loadings must give" in e for e in _errs(bad))
    bad = copy.deepcopy(m); bad["indices"][0]["indicators"] = ["income", "nope"]
    assert any("ACS manifest variables" in e for e in _errs(bad))
    bad = copy.deepcopy(m); bad["indices"][0]["method"] = "pca"
    assert any("at least 3" in e for e in _errs(bad))
    circ = copy.deepcopy(m); circ["analyses"][0]["formula"] = "income ~ size_index"
    assert any("CIRCULARITY" in e for e in _errs(circ))


def _reps(frame, names, seed=5):
    rng = np.random.default_rng(seed)
    parts = []
    for v in names:
        est = frame[v].to_numpy(float)
        r = est[:, None]+rng.normal(0, 1, (len(frame), 80))*np.maximum(est, 1)[:, None]*.03
        parts.append(pd.DataFrame({"GEOID": frame["GEOID"].astype(str), "Year": 2019, "variable": v, "estimate": est,
                                   **dict(zip(REPLICATE_COLUMNS, r.T))}))
    return pd.concat(parts, ignore_index=True)


def test_index_matches_build_index(tmp_path):
    from census.composite_index import build_index
    m = _index_manifest()
    m["analyses"] = [dict(id="m1", method="fit_replicate", formula="pop ~ size_index", args={"model": "ols"})]
    m["hypotheses"] = [dict(id="H1", analysis="m1", statistic="coefficient", term="size_index", direction="two-sided",
                            statement="s")]
    m["exploratory"] = True          # pop is an indicator: the circularity rule refuses it as an outcome
    assert any("CIRCULARITY" in e for e in _errs(dict(m, exploratory=False)))
    probe = run_manifest(load_manifest(EXAMPLE), tmp_path/"probe", client=FakeClient(), use_cache=False)["frame"]
    reps = _reps(probe, ["income", "pop"])
    frame, reps2, info = r75.build_indices(probe, reps, m["indices"])
    ref = build_index(probe, ["income", "pop"], replicates=reps, method="loadings",
                      loadings={"income": .8, "pop": .6}, standardize=True)["table"].set_index("area")
    got = frame.set_index(frame.GEOID.astype(str))
    assert np.allclose(got.size_index, ref.score.reindex(got.index), atol=1e-10)
    assert np.allclose(got.size_index_se, ref.se.reindex(got.index), atol=1e-10)
    assert info[0]["replicates"] and (reps2.variable == "size_index").sum() == len(probe)


def test_manifest_with_index_runs(tmp_path):
    m = _index_manifest()
    m["derivations"] = [dict(name="pop_k", op="scale", num="pop", k=.001)]
    m["indices"][0].update(indicators=["income", "pop_k"], loadings={"income": .8, "pop_k": .6})
    m["analyses"] = [dict(id="m1", method="fit_replicate", formula="pop ~ size_index", args={"model": "ols"})]
    m["hypotheses"] = [dict(id="H1", analysis="m1", statistic="coefficient", term="size_index",
                            direction="two-sided", statement="s")]
    m["exploratory"] = True
    assert _errs(m) == []
    res = run_manifest(m, tmp_path, client=FakeClient(), use_cache=False)
    from census.manifest.methods_text import methods_section
    assert "Index size_index" in methods_section(m) and "published fixed loadings" in methods_section(m)
    assert "size_index" in res["frame"] and not [d for d in res["deviations"] if d["kind"] == "analysis_not_run"]


# ---- person-years -----------------------------------------------------------------------------------------------

def test_person_years_matches_library():
    from census import wonder_reference as wr
    ref = os.path.join(ROOT, "tests/fixtures/wonder/national_age_sex.tsv")
    bands = [wr.band_name(s, b) for s, b in wr.band_order()]
    rng = np.random.default_rng(2)
    f = pd.DataFrame(rng.integers(100, 900, (4, 20)).astype(float), columns=bands)
    f["GEOID"] = ["01001", "01003", "01005", "01007"]; f["py"] = [50000., 90000., 12000., 30000.]
    import hashlib
    from census.vital_records import read_wonder_reference
    years = len(read_wonder_reference(ref)["years"])
    d = dict(name="expected", op="expected_count", population_bands=bands, period_years=years, person_years="py",
             reference_export={"file": ref, "sha256": hashlib.sha256(open(ref, "rb").read()).hexdigest()})
    out, _, info = r75.apply_person_years(f, None, [d])
    want = wr.expected_counts(f.set_index("GEOID")[bands], ref, person_years=f.set_index("GEOID").py)
    assert np.allclose(out.expected.to_numpy(), want.to_numpy())
    assert info[0]["person_years"] == "py"


def test_person_years_validation():
    m = load_manifest(EXAMPLE)
    m["derivations"] = [dict(name="e", op="ratio", num="income", den="pop", person_years="nope")]
    assert any("person_years applies" in e for e in _errs(m))


# ---- tract coordinates ------------------------------------------------------------------------------------------

def test_tract_vintage_retry_and_error():
    from census import small_spatial as ss
    f = pd.DataFrame(dict(GEOID=["37001020300", "37001020400"]))
    found = pd.DataFrame(dict(GEOID=f.GEOID, lon=[-79., -79.1], lat=[36., 36.1]))
    calls = []

    def uc(geoids, level, year):
        calls.append(year)
        if year == 2022:
            raise ValueError("missing boundary GEOIDs")
        return found, {}
    with mock.patch("census.spatial_hac.unit_coordinates", uc):
        out = ss.frame_coordinates(f)
    assert calls == [2022, 2019] and "2010 tracts" in out.attrs["tract_vintage_note"]
    with mock.patch("census.spatial_hac.unit_coordinates", side_effect=ValueError("missing")):
        with pytest.raises(ValueError, match="Add a Year column"):
            ss.frame_coordinates(f)
    with mock.patch("census.spatial_hac.unit_coordinates", return_value=(found, {})) as m:
        ss.frame_coordinates(f.assign(Year=2018))
    assert m.call_args[0][2] == 2018


# ---- recipes ----------------------------------------------------------------------------------------------------

NEW_RECIPES = ("policy_change", "custom_geographies", "dollars", "spatial_patterns", "cross_release", "reporting")


def test_new_recipes():
    from census import recipes
    for name in NEW_RECIPES:
        out = recipes.get_recipe(name)
        assert out["success"] and "1. " in out["steps"], name
    assert "spatial_small_area_estimates" in recipes.get_recipe("small_area")["steps"]
    assert "pums_tabulate" in recipes.get_recipe("pums_tests")["steps"]
    assert "multilevel" in recipes.get_recipe("preregistered")["steps"]
