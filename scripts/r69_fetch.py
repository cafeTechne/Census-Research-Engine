# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 69: download the public inputs for replication D into caches (no association computed).

ACS 2010-2014 county tables (national requests); County Business Patterns 2012 county establishment counts for the
social-capital NAICS codes; ERS 2015 county economic types and 2013 metro status (ERS GIS portal, CC0); 2014
cartographic county boundaries. Writes .cache/replication/ers_county_types_2015.json and prints its SHA-256.

Usage: scripts/r69_fetch.py
"""
import hashlib
import json
import os
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from census import boundaries  # noqa: E402
from census.workflows import _client  # noqa: E402

ACS_TABLES = ["B17001", "B23001", "B18101", "B15002", "B19056", "B19057", "B19083", "B27001", "B25002", "B25070",
              "B12001", "B11003", "B07003", "B01001", "B21001", "B03002", "B01003"]
CBP_NAICS = ["813110", "8134", "8139", "713910", "713940", "713950"]
ERS = ("https://gisportal.ers.usda.gov/server/rest/services/Rural_Atlas_Data/County_Classifications/MapServer/5/query")
REPL = Path(os.getenv("CENSUS_REPLICATION_DIR", ROOT/".cache/replication"))


def main():
    c = _client()
    for t in ACS_TABLES:
        if c.fetch(2014, "*", t, geo_level="county") is None:
            raise SystemExit(f"{t}: {c.last_error}")
        print("acs", t, flush=True)
    ep = "https://api.census.gov/data/2012/cbp"
    for n in CBP_NAICS:
        params = {"get": "ESTAB,NAICS2012", "for": "county:*", "in": "state:*", "NAICS2012": n, "key": c.api_key}
        if c._get_json(ep, params) is None:
            raise SystemExit(f"CBP {n}: {c.last_error}")
        print("cbp", n, flush=True)
    rows, off = [], 0
    while True:
        r = requests.get(ERS, params={"where": "1=1", "outFields": "FIPSTXT,Type_2015_Update,Metro2013",
                                      "returnGeometry": "false", "f": "json", "resultOffset": off,
                                      "resultRecordCount": 1000}, headers={"User-Agent": "census-research-engine"},
                         timeout=120).json()
        feats = r.get("features", [])
        rows += [f["attributes"] for f in feats]
        if not feats or not r.get("exceededTransferLimit"):
            break
        off += len(feats)
    REPL.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(sorted(rows, key=lambda x: str(x["FIPSTXT"])), sort_keys=True).encode()
    (REPL/"ers_county_types_2015.json").write_bytes(raw)
    print("ers rows", len(rows), "sha256", hashlib.sha256(raw).hexdigest())
    boundaries.get_boundaries("county", 2014)
    print("boundaries ok")


if __name__ == "__main__":
    main()
