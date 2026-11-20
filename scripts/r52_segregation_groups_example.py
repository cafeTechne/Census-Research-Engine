# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 52 exploratory example: race/ethnicity segregation and the 2019-2024 poverty-segregation change.

Exploratory; author self-review, not independent; no registration. Reads cached tract VRE files (HTTP
blocked): 2024 B03002 (MI, NY) and B17001 for 2015-2019 and 2020-2024 (MI, NY). Runs
census.segregation_replicate with its defaults (bias-corrected; negative replicates clipped) on:
- Black vs everyone else (B03002_004 vs the other components), Hispanic vs non-Hispanic (012 vs 002);
- four groups: non-Hispanic White, non-Hispanic Black, Hispanic, all other non-Hispanic (005-009);
- poverty two groups in both releases, and segregation_test release 2024 vs 2019 per county.
Writes county rows (no tract data) and a summary.

Usage: CENSUS_VRE_DIR=<main>/.cache/vre scripts/r52_segregation_groups_example.py OUT_DIR
"""
import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pandas as pd  # noqa: E402

from census import replicate, segregation as sg  # noqa: E402
from census.variance import REPLICATE_COLUMNS  # noqa: E402

COLS = ["estimate", *REPLICATE_COLUMNS]
RACE = {"black2": {"black": [4], "nonblack": [3, 5, 6, 7, 8, 9, 12]},
        "hisp2": {"hisp": [12], "nonhisp": [2]},
        "race4": {"white": [3], "black": [4], "hisp": [12], "other": [5, 6, 7, 8, 9]}}
KEEP = ["GEOID", "Year", "statistic", "estimate", "se", "ci_lower", "ci_upper", "validated", "noise_level",
        "clipped_replicates", "tracts"]


def grouped(long, table, groups):
    parts = []
    for name, lines in groups.items():
        sub = long[long.variable.isin([f"{table}_{i:03d}" for i in lines])]
        g = sub.groupby("GEOID", as_index=False)[COLS].sum(); g["variable"] = name
        parts.append(g)
    return pd.concat(parts, ignore_index=True)


def frame(long, groups, year):
    f = long.pivot(index="GEOID", columns="variable", values="estimate")[list(groups)].reset_index()
    f["Year"] = year
    rep = long[["GEOID", "variable", *REPLICATE_COLUMNS]].copy(); rep["Year"] = year
    return f, rep


def main(out_dir):
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=False)
    with patch("requests.sessions.Session.request", side_effect=RuntimeError("HTTP blocked")):
        b03 = pd.concat([replicate.fetch_vre("B03002", 2024, "tract", state_code=s, lines=[2, 3, 4, 5, 6, 7, 8, 9, 12])
                         for s in ("26", "36")], ignore_index=True)
        pov = {y: pd.concat([replicate.fetch_vre("B17001", y, "tract", state_code=s, lines=[2, 31]) for s in ("26", "36")],
                            ignore_index=True) for y in (2019, 2024)}
    summary = []
    for design, groups in RACE.items():
        f, rep = frame(grouped(b03, "B03002", groups), groups, 2024)
        res = sg.segregation_replicate(f, list(groups), rep)
        res[KEEP].to_csv(out_dir/f"{design}.csv", index=False)
        for stat, part in res.groupby("statistic"):
            summary.append(dict(design=design, statistic=stat, counties=int(len(part)), validated=int(part.validated.sum()),
                                noise_median=float(part.noise_level.median()),
                                noise_infinite=int((part.noise_level == float("inf")).sum())))
        h = res[(res.statistic == "theil_h") & res.validated].sort_values("estimate", ascending=False).head(5)
        print(design, "top validated H:", [(g, round(e, 3), round(lo, 3), round(hi, 3)) for g, e, lo, hi in
                                          zip(h.GEOID, h.estimate, h.ci_lower, h.ci_upper)])
    fr, rp = [], []
    for y, long in pov.items():
        long = long.copy(); long["variable"] = long.variable.map({"B17001_002": "below", "B17001_031": "above"})
        f, rep = frame(long, ["below", "above"], y); fr.append(f); rp.append(rep)
    res = sg.segregation_replicate(pd.concat(fr, ignore_index=True), ["below", "above"], pd.concat(rp, ignore_index=True))
    rows = []
    for county in sorted(set(res.GEOID[res.Year == 2024]) & set(res.GEOID[res.Year == 2019])):
        for stat in ("dissimilarity", "theil_h"):
            t = sg.segregation_test(res, stat, county, release=2024, compare_release=2019)
            rows.append(dict(GEOID=county, statistic=stat, change=t["estimate"], se=t["se"], ci_lower=t["ci_lower"],
                             ci_upper=t["ci_upper"], validated=t["validated"]))
    ch = pd.DataFrame(rows); ch.to_csv(out_dir/"poverty_change_2019_2024.csv", index=False)
    for stat, part in ch.groupby("statistic"):
        v = part[part.validated]
        summary.append(dict(design="poverty_change", statistic=stat, counties=int(len(part)), validated=int(len(v)),
                            ci_excludes_zero=int(((v.ci_lower > 0) | (v.ci_upper < 0)).sum()),
                            median_change=float(v.change.median()) if len(v) else None))
    (out_dir/"summary.json").write_text(json.dumps(summary, indent=1)+"\n")
    for s in summary:
        print(s)


if __name__ == "__main__":
    main(sys.argv[1])
