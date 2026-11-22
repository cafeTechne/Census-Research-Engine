# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 93 exploratory example: GWR, neighbourhood types and SKATER regions for Wayne County, MI tracts.

Exploratory; author self-review, not independent; not a registered study. ACS 2019-2023 tracts: percent below poverty
(S1701_C03_001), unemployment rate (S2301_C04_001), percent with a bachelor's degree or higher among adults 25+
(S1501_C02_015), each with its MOE. (a) GWR of poverty on unemployment and education; (b) k-means neighbourhood types
(k = 4, fixed in advance) and (c) SKATER regions (k = 6, fixed in advance) on the three measures, with stability.
Writes docs/audits/r93_spatial_models_example.md (summary only).

Usage: scripts/r93_spatial_models_example.py OUT_DIR
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pandas as pd  # noqa: E402

from census.api import CensusAPIClient  # noqa: E402
from census.workflows_geo import spatial_model  # noqa: E402

COLS = {"pov": "S1701_C03_001", "unemp": "S2301_C04_001", "ba": "S1501_C02_015"}


def frame():
    c = CensusAPIClient(); parts = []
    for table, var in (("S1701", "pov"), ("S2301", "unemp"), ("S1501", "ba")):
        d = c.fetch(2023, "26", table, geo_level="tract", dataset="subject")
        if d is None:
            raise SystemExit(f"{table}: {c.last_error}")
        f = pd.DataFrame(d[1:], columns=d[0]).loc[:, lambda x: ~x.columns.duplicated()]
        f = f[f.county == "163"]
        f["GEOID"] = f.state+f.county+f.tract
        code = COLS[var]
        parts.append(pd.DataFrame({"GEOID": f.GEOID, var: pd.to_numeric(f[code+"E"], errors="coerce"),
                                   f"{var}_moe": pd.to_numeric(f[code+"M"], errors="coerce")}).set_index("GEOID"))
    out = pd.concat(parts, axis=1).reset_index()
    out = out[(out[list(COLS)] >= 0).all(axis=1) & (out[[f"{v}_moe" for v in COLS]] >= 0).all(axis=1)].dropna()
    assert out.pov.median() < 40 and out.ba.median() < 60, "column checks"
    return out


def main():
    od = Path(sys.argv[1]); od.mkdir(parents=True, exist_ok=False)
    f = frame(); p = od/"wayne.csv"; f.to_csv(p, index=False)
    g = spatial_model(str(p), "gwr", "tract", 2023, outcome="pov", predictors=["unemp", "ba"],
                      output_path=str(od/"gwr.csv"))
    c = spatial_model(str(p), "classify", "tract", 2023, features=list(COLS), k=4, output_path=str(od/"types.csv"))
    r = spatial_model(str(p), "regionalize", "tract", 2023, features=list(COLS), k=6, output_path=str(od/"regions.csv"))
    for x in (g, c, r):
        if not x["success"]:
            raise SystemExit(x["error"])
    co = g["coefficients"]
    L = ["# Round 93 example: GWR, neighbourhood types and regions, Wayne County tracts (exploratory)", "",
         f"Author self-review, not independent; not a registered study. ACS 2019-2023, {len(f)} Wayne County, MI "
         "tracts with complete estimates. Percent below poverty, unemployment rate, percent with a bachelor's "
         "degree (25+), each with its MOE.", "",
         f"**GWR (exploratory)** of poverty on unemployment and education: bandwidth {g['bandwidth_km']:.1f} km, "
         f"{g['effective_parameters']:.1f} effective parameters. Local unemployment slopes {co['unemp']['min']:.2f} to "
         f"{co['unemp']['max']:.2f} (median {co['unemp']['median']:.2f}); local education slopes {co['ba']['min']:.2f} "
         f"to {co['ba']['max']:.2f} (median {co['ba']['median']:.2f}); non-stationarity p = "
         f"{g['nonstationarity']['p_value']:.3f} (unemployment). Local intervals under-covered in validation when slopes "
         "vary; read the spread descriptively.", "",
         f"**Neighbourhood types** (k-means, k = 4): mean stability {c['mean_stability']:.2f}; "
         f"{c['share_unstable']:.0%} of tracts unstable (< .8).", "",
         "| Type | Poverty % | Unemployment % | Bachelor's % |", "| ---: | ---: | ---: | ---: |"]
    L += [f"| {x['group']} | {x['pov']:.1f} | {x['unemp']:.1f} | {x['ba']:.1f} |" for x in c["profiles"]]
    L += ["", f"**SKATER regions** (k = 6, queen contiguity): mean stability {r['mean_stability']:.2f}; "
          f"{r['share_unstable']:.0%} of tracts unstable.", "",
          "| Region | Poverty % | Unemployment % | Bachelor's % |", "| ---: | ---: | ---: | ---: |"]
    L += [f"| {x['group']} | {x['pov']:.1f} | {x['unemp']:.1f} | {x['ba']:.1f} |" for x in r["profiles"]]
    L.append("")
    (ROOT/"docs/audits/r93_spatial_models_example.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
