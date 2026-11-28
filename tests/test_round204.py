# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 204 tests: reusable zero-CDN side_by_side_choropleth interactive dual-panel web map."""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
from shapely.geometry import box

from census.web_maps import side_by_side_choropleth


def test_side_by_side_choropleth_zero_cdn(tmp_path: Path):
    geoms = [box(i, 0, i + 1, 1) for i in range(6)]
    gdf = gpd.GeoDataFrame(
        {
            "GEOID": [f"2600{i}" for i in range(6)],
            "NAME": [f"County {i}" for i in range(6)],
            "raw_smr": [0.7, 0.9, 1.0, 1.1, 1.3, 1.6],
            "bym2_rr": [0.85, 0.95, 1.0, 1.05, 1.2, 1.35],
        },
        geometry=geoms,
        crs="EPSG:4326",
    )
    out = tmp_path / "compare.html"
    rep = side_by_side_choropleth(gdf, "raw_smr", "bym2_rr", out, title="Raw vs BYM2", k=3)
    assert rep["ok"] is True
    assert rep["left_features"] == 6 and rep["right_features"] == 6
    txt = out.read_text(encoding="utf-8")
    assert "Content-Security-Policy" in txt
    assert "<iframe" in txt and txt.count("<iframe") == 2
    assert "http://" not in txt and "https://" not in txt
