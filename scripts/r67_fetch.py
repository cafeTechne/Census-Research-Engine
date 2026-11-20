# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 67: download the public inputs for replication C into the engine caches (no association computed).

USALEEP 2010-2015 NC A file; ACS 2014-2018 NC tract B19001, B19001B, B19001H, B03002; 2018 NC cartographic tract
boundaries; 2018 VRE tract files B19001 and B03002 for NC. Then write the tract geometry used by simulation S
(docs/audits/nc_tract_geometry.json: GEOID, lon, lat of the analysis tracts) without reading any outcome value.

Usage: scripts/r67_fetch.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from census import boundaries, health_sources, replicate  # noqa: E402
from census.workflows import _client  # noqa: E402


def main():
    c = _client()
    for t in ("B19001", "B19001B", "B19001H", "B03002"):
        if c.fetch(2018, "37", t, geo_level="tract") is None:
            raise SystemExit(f"{t}: {c.last_error}")
    health_sources.fetch_usaleep(["37"])
    gdf = boundaries.get_boundaries("tract", 2018, state="37")
    for t in ("B19001", "B03002"):
        replicate.fetch_vre(t, 2018, "tract", state_code="37")
    pts = gdf.to_crs(5070).representative_point().to_crs(4326)
    geo = dict(source="2018 cartographic tract boundaries, NC; representative points",
               GEOID=gdf.GEOID.astype(str).tolist(), lon=[round(p.x, 6) for p in pts], lat=[round(p.y, 6) for p in pts])
    (ROOT/"docs/audits/nc_tract_geometry.json").write_text(json.dumps(geo)+"\n")
    print(len(geo["GEOID"]), "tracts")


if __name__ == "__main__":
    main()
