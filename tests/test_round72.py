# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 72: context covariate sources (CBP, ERS typology and rural-urban codes, CHR additional measures)."""
import hashlib
import json
import os

import pandas as pd
import pytest

from census import context_sources as cs
from census.pipeline import build_entities


class FakeClient:
    api_key = "x"; last_error = None

    def __init__(self, rows):
        self.rows, self.calls = rows, []

    def _get_json(self, ep, params):
        self.calls.append(params[next(k for k in params if k.startswith("NAICS"))])
        return self.rows[self.calls[-1]]


def test_validate_context():
    ok = [{"source": "cbp", "name": "religious", "year": 2012, "naics": ["813110"], "per": 10000, "per_column": "pop"},
          {"source": "ers_rucc", "name": "rucc", "field": "RuralUrbanContinuumCode2013"},
          {"source": "chr_additional", "name": "seg", "measure": "v141", "release": 2025}]
    assert cs.validate_context(ok) == []
    bad = [{"source": "places", "name": "x"}, {"source": "cbp", "name": "a b", "year": 1999, "naics": [813110]},
           {"source": "ers_typology", "name": "t", "field": "nope"}, {"source": "cbp", "name": "c", "year": 2012,
                                                                    "naics": ["1"], "per": 10}]
    errs = cs.validate_context(bad)
    assert len(errs) >= 5 and cs.validate_context(ok, names=["rucc"])  # duplicate name refused


def test_cbp_sum_and_rate():
    rows = {"8134": [["ESTAB", "NAICS2012", "state", "county"], ["3", "8134", "01", "001"], ["1", "8134", "01", "003"]],
            "8139": [["ESTAB", "NAICS2012", "state", "county"], ["2", "8139", "01", "001"]]}
    s, rec = cs.fetch_cbp(2012, ["8134", "8139"], FakeClient(rows))
    assert s.to_dict() == {"01001": 5, "01003": 1} and rec["naics"] == ["8134", "8139"]
    frame = pd.DataFrame(dict(GEOID=["01001", "01003", "01005"], pop=[1000., 2000., 500.]))
    out, prov = cs.context_frame([{"source": "cbp", "name": "m", "year": 2012, "naics": ["8134", "8139"],
                                   "per": 10000, "per_column": "pop"}], frame, client=FakeClient(rows))
    assert out.m.round(6).to_dict() == {"01001": 50.0, "01003": 5.0, "01005": 0.0}


def test_ers_cache_pagination_and_offline(tmp_path, monkeypatch):
    monkeypatch.setenv("CENSUS_CONTEXT_DIR", str(tmp_path))
    pages = [{"features": [{"attributes": {"FIPSTXT": "1001", "Type_2015_Update": 0, "Metro2013": 1}}],
              "exceededTransferLimit": True},
             {"features": [{"attributes": {"FIPSTXT": "48301", "Type_2015_Update": 2, "Metro2013": 0}}]}]

    class Sess:
        def get(self, url, params, headers, timeout):
            page = pages[params["resultOffset"]]
            return type("R", (), {"json": lambda self: page})()
    d, rec = cs.fetch_ers(Sess())
    assert list(d.index) == ["01001", "48301"] and d.loc["48301", "Type_2015_Update"] == 2
    raw = (tmp_path/"ers"/"county_classifications.json").read_bytes()
    assert rec["sha256"] == hashlib.sha256(raw).hexdigest()
    monkeypatch.setenv("CENSUS_HEALTH_OFFLINE", "1")
    assert cs.fetch_ers()[0].shape == d.shape          # cached copy, no network
    (tmp_path/"ers"/"county_classifications.json").unlink()
    with pytest.raises(FileNotFoundError):
        cs.fetch_ers()


def test_chr_additional_and_tract_join(tmp_path, monkeypatch):
    monkeypatch.setenv("CENSUS_CONTEXT_DIR", str(tmp_path))
    csv = b"statecode,countycode,state,county,fipscode,rawvalue,v141_rawvalue\n01,000,AL,Alabama,01000,57.7,57.7\n01,001,AL,Autauga,01001,40.5,40.5\n"
    s, rec = cs.fetch_chr_additional("v141", 2025, fetch=lambda u: csv)
    assert s.to_dict() == {"01001": 40.5} and cs.CHR_COMMITS[2025] in rec["source_url"]
    tracts = pd.DataFrame(dict(GEOID=["01001020100", "01001020200", "01003010100"]))
    joined, info = cs.join_context(tracts, s.rename("seg").to_frame())
    assert joined.seg.tolist()[:2] == [40.5, 40.5] and pd.isna(joined.seg.iloc[2]) and info["level"].startswith("tract")


def test_state_wide_tracts_already_one_request():
    e = build_entities("tract", "26")
    assert len(e) == 1 and e[0].county_code == "*"


def test_manifest_context_validation():
    from census.manifest import load_manifest, validate_manifest
    from tests.test_manifest import EXAMPLE
    m = load_manifest(EXAMPLE)
    m["context"] = [{"source": "ers_rucc", "name": "rucc", "field": "Nope"}]
    errs = validate_manifest(m)
    assert any("context[0]" in str(x) for x in (errs if isinstance(errs, list) else errs.get("errors", [])))


def test_listing():
    from census.workflows_inference import list_health_sources
    out = list_health_sources(kind="context")
    assert out["success"] and set(out["sources"]) == {"cbp", "ers_typology", "ers_rucc", "chr_additional"}
    assert list_health_sources(kind="x")["success"] is False


@pytest.mark.skipif(os.getenv("CENSUS_LIVE_TESTS") != "1", reason="live")
def test_live_sources():
    s, rec = cs.fetch_chr_additional("v141", 2025)
    assert rec["sha256"] == "2c737ea89db403c0cbf825b10ad2e03fccfcdc4e66fd242eb90b2a9c305636fe"
    cbp, _ = cs.fetch_cbp(2012, ["813110"])
    assert cbp["01001"] == 51
    ers, _ = cs.fetch_ers()
    assert len(ers) > 3100 and set(ers.Type_2015_Update.dropna().astype(int)) <= set(range(6))


def test_manifest_run_joins_context(tmp_path, monkeypatch):
    from census.manifest import load_manifest, run_manifest
    from tests.test_manifest import EXAMPLE, FakeClient
    monkeypatch.setenv("CENSUS_CONTEXT_DIR", str(tmp_path/"ctx")); monkeypatch.setenv("CENSUS_HEALTH_OFFLINE", "1")
    m = load_manifest(EXAMPLE)
    plain = run_manifest(m, tmp_path/"a", client=FakeClient(), use_cache=False)
    counties = sorted({g[:5] for g in plain["frame"].GEOID.astype(str)})
    rows = [{"FIPSTXT": c, "Metro2013": 1} for c in counties]
    folder = tmp_path/"ctx"/"ers"; folder.mkdir(parents=True)
    raw = json.dumps(rows, sort_keys=True).encode()
    (folder/"county_classifications.json").write_bytes(raw)
    (folder/"county_classifications.json.json").write_text(json.dumps({"sha256": hashlib.sha256(raw).hexdigest()}))
    m["context"] = [{"source": "ers_rucc", "name": "metro", "field": "Metro2013"}]
    res = run_manifest(m, tmp_path/"b", client=FakeClient(), use_cache=False)
    assert not any(d["kind"] == "context_join_failed" for d in res["deviations"])
    assert (res["frame"].metro == 1).all()
    run = json.loads((tmp_path/"b"/"bundle"/"run.json").read_text()) if (tmp_path/"b"/"bundle"/"run.json").exists() else None
    assert run is None or "context" in run
