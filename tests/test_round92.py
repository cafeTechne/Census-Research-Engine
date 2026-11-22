# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 92: Population Estimates, LODES and ACS migration flows (offline fixtures)."""
import gzip

import pandas as pd
import pytest

from census import context_sources as cs
from census import demographic_sources as ds


@pytest.fixture(autouse=True)
def cache(tmp_path, monkeypatch):
    monkeypatch.setenv("CENSUS_CONTEXT_DIR", str(tmp_path/"ctx"))
    monkeypatch.delenv("CENSUS_HEALTH_OFFLINE", raising=False)
    return tmp_path


TOTALS = ("SUMLEV,REGION,DIVISION,STATE,COUNTY,STNAME,CTYNAME,POPESTIMATE2020,POPESTIMATE2021,POPESTIMATE2022,"
          "POPESTIMATE2023,POPESTIMATE2024\n"
          "040,2,3,26,000,Michigan,Michigan,300,310,320,330,340\n"
          "050,2,3,26,001,Michigan,Alcona County,100,105,110,115,120\n"
          "050,2,3,26,003,Michigan,Alger County,200,205,210,215,220\n")
AGESEX = ("SUMLEV,STATE,COUNTY,STNAME,CTYNAME,YEAR,POPESTIMATE,AGE65PLUS_TOT\n"
          "050,26,001,Michigan,Alcona County,1,99,40\n"
          "050,26,001,Michigan,Alcona County,2,100,41\n"
          "050,26,001,Michigan,Alcona County,5,115,45\n")
WAC = ("w_geocode,C000,CA01,CNS01,createdate\n"
       "261630001001000,10,3,1,20230101\n261630001001001,5,1,0,20230101\n261630002002000,7,2,0,20230101\n"
       "260010001001000,4,1,1,20230101\n")


def test_pep_totals_long_with_vintage_and_state_sum():
    t, rec = ds.pep_totals(2024, fetch=lambda u: TOTALS.encode())
    assert set(t.vintage) == {2024} and sorted(t.year.unique()) == [2020, 2021, 2022, 2023, 2024]
    st = t[t.level == "state"].set_index("year").population
    co = t[t.level == "county"].groupby("year").population.sum()
    assert (st == co).all() and len(rec["sha256"]) == 64 and "no MOE" in rec["note"]


def test_pep_age_sex_year_codes():
    a, _ = ds.pep_age_sex("26", 2024, fetch=lambda u: AGESEX.encode())
    assert dict(zip(a.year, a.POPESTIMATE)) == {2020: 100, 2023: 115}   # code 1 (April base) dropped
    with pytest.raises(ValueError):
        ds.pep_totals(2016, fetch=lambda u: b"")


def test_lodes_aggregation_levels():
    raw = gzip.compress(WAC.encode())
    tr, rec = ds.lodes("26", 2021, "wac", "tract", fetch=lambda u: raw)
    co, _ = ds.lodes("26", 2021, "wac", "county", fetch=lambda u: raw)
    assert tr.set_index("w_tract").C000.to_dict() == {"26001000100": 4, "26163000100": 15, "26163000200": 7}
    assert co.set_index("w_county").C000.to_dict() == {"26001": 4, "26163": 22}
    assert "createdate" not in co and "no MOE" in rec["note"] and rec["version"] == "LODES8"
    for bad in (dict(kind="xyz"), dict(job_type="JT99"), dict(level="zcta")):
        with pytest.raises(ValueError):
            ds.lodes("26", 2021, **{"kind": "wac", "level": "county", **bad}, fetch=lambda u: raw)
    with pytest.raises(ValueError):
        ds.lodes("26", 1999, "wac", fetch=lambda u: raw)


class FakeClient:
    api_key = "k"
    last_error = None

    def __init__(self):
        self.calls = []

    def _get_json(self, ep, params):
        self.calls.append((ep, params))
        h = ["MOVEDIN", "MOVEDIN_M", "MOVEDOUT", "MOVEDOUT_M", "MOVEDNET", "MOVEDNET_M", "GEOID1", "GEOID2",
             "FULL2_NAME", "state", "county"]
        return [h, ["30", "10", "50", "20", "-20", "22", "26001", "26003", "Alger", "26", "001"],
                ["5", "4", "8", "6", "-3", "7", "26001", "01003", "Baldwin", "26", "001"],
                ["9", "6", None, None, None, None, "26001", None, "Asia", "26", "001"]]


def test_flows_and_net_migration():
    c = FakeClient()
    f, rec = ds.migration_flows("26", 2020, client=c)
    assert rec["release"] == "2016-2020" and c.calls[0][0].endswith("/2020/acs/flows")
    n = ds.net_migration(f).set_index("GEOID").loc["26001"]
    assert n.moved_in == 44 and n.moved_in_domestic == 35 and n.net_domestic == -23
    assert n.net_domestic_moe == pytest.approx((22**2+7**2)**.5)
    with pytest.raises(ValueError, match="state-level"):
        ds.migration_flows("26", 2022, client=c)


def test_context_validation_messages():
    errs = cs.validate_context([
        {"source": "pep", "name": "a", "vintage": 2024, "year": 2019},
        {"source": "lodes", "name": "b", "year": 2021, "kind": "od"},
        {"source": "acs_flows", "name": "c", "year": 2022, "field": "net_domestic"},
        {"source": "acs_flows", "name": "d", "year": 2020, "field": "bogus"},
    ])
    assert len(errs) == 4
    assert cs.validate_context([{"source": "pep", "name": "p", "vintage": 2019, "year": 2015},
                                {"source": "lodes", "name": "j", "year": 2021, "kind": "rac"}]) == []


def test_context_frame_pep_lodes_flows(monkeypatch):
    raw = gzip.compress(WAC.encode())
    monkeypatch.setattr(ds, "_get", lambda u: TOTALS.encode() if "co-est" in u else raw)
    fr = pd.DataFrame({"GEOID": ["26001", "26163"], "pop": [1000., 2000.]})
    out, prov = cs.context_frame([
        {"source": "pep", "name": "pop23", "vintage": 2024, "year": 2023},
        {"source": "lodes", "name": "jobs", "year": 2021, "kind": "wac", "per": 1000, "per_column": "pop"},
        {"source": "acs_flows", "name": "netmig", "year": 2020, "field": "net_domestic"}], fr, client=FakeClient())
    assert out.loc["26001", "pop23"] == 115 and out.loc["26001", "jobs"] == pytest.approx(4.0)
    assert out.loc["26163", "jobs"] == pytest.approx(11.0)
    assert out.loc["26001", "netmig"] == -23 and "netmig_moe" in out
    assert [p["entry"]["source"] for p in prov] == ["pep", "lodes", "acs_flows"]


def test_sources_registered():
    from census.references import tool_entries
    ids = {s for s, _ in tool_entries("build_analysis_frame")}
    assert {"pep", "lodes", "acs_flows", "walker2023"} <= ids
