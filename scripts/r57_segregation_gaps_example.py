# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 57 exploratory example: race/ethnicity segregation with the Round 57 ranges, group-quarters tracts
excluded, six groups, and a same-release county contrast (MI/NY 2024).

Exploratory; author self-review, not independent; no registration. Reads cached files (HTTP blocked): 2024 tract
VRE B03002 (MI, NY) and cached 2024 tract API responses for B26001 (group-quarters population) and B01003 (total
population). Defaults: bias-corrected indices, negative replicates clipped. Writes county rows and a summary.

Usage: CENSUS_VRE_DIR=<main>/.cache/vre scripts/r57_segregation_gaps_example.py CACHE_DB OUT_DIR
"""
import json
import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/"scripts"))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import r52_segregation_groups_example as r52  # noqa: E402
from census import replicate, segregation as sg  # noqa: E402

DESIGNS = {"black2": r52.RACE["black2"], "race4": r52.RACE["race4"],
           "race6": {"white": [3], "black": [4], "asian": [6], "hisp": [12], "multi": [9], "other3": [5, 7, 8]}}
NAMES = {"36121": "Wyoming NY", "36039": "Greene NY", "26033": "Chippewa MI", "26163": "Wayne MI", "26125": "Oakland MI"}


def gq_frame(cache_db):
    con = sqlite3.connect(f"file:{cache_db}?mode=ro", uri=True)
    rows = []
    for st in ("26", "36"):
        cols = {}
        for t in ("B26001", "B01003"):
            params = json.dumps({"for": "tract:*", "get": f"NAME,group({t})", "in": f"state:{st} county:*"})
            d = json.loads(con.execute("select payload from responses where endpoint=? and params=?",
                                       ("https://api.census.gov/data/2024/acs/acs5", params)).fetchone()[0])
            df = pd.DataFrame(d[1:], columns=d[0]); df = df.loc[:, ~df.columns.duplicated()]
            df["GEOID"] = df.state+df.county+df.tract
            cols[t] = df.set_index("GEOID")[f"{t}_001E"].astype(float)
        rows.append(pd.DataFrame(dict(gq=cols["B26001"], total=cols["B01003"])))
    return pd.concat(rows).rename_axis("GEOID").reset_index()


def summarise(res, design, label):
    h = res[res.statistic == "theil_h"]
    clipped = h.clipped_replicates > 0
    return dict(design=design, run=label, counties=int(len(h)), validated=int(h.validated.sum()),
                clipped=int(clipped.sum()), clipped_validated=int((clipped & h.validated).sum()))


def main(cache_db, out_dir):
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=False)
    with patch("requests.sessions.Session.request", side_effect=RuntimeError("HTTP blocked")):
        b03 = pd.concat([replicate.fetch_vre("B03002", 2024, "tract", state_code=s, lines=[2, 3, 4, 5, 6, 7, 8, 9, 12])
                         for s in ("26", "36")], ignore_index=True)
    gq = gq_frame(cache_db)
    excl = sg.group_quarters_tracts(gq, "gq", "total", .5)
    summary, tops = [], {}
    for design, groups in DESIGNS.items():
        f, rep = r52.frame(r52.grouped(b03, "B03002", groups), groups, 2024)
        for label, kw in (("all tracts", {}), ("group quarters >= .5 excluded", {"exclude_tracts": excl})):
            res = sg.segregation_replicate(f, list(groups), rep, **kw)
            res[r52.KEEP].to_csv(out_dir/f"{design}_{'gq' if kw else 'all'}.csv", index=False)
            summary.append(summarise(res, design, label))
            h = res[res.statistic == "theil_h"].set_index("GEOID")
            tops[(design, label)] = {NAMES.get(g, g): (round(float(h.loc[g, "estimate"]), 3), bool(h.loc[g, "validated"]))
                                     for g in ("36121", "36039", "26033") if g in h.index}
            if design == "black2" and not kw:
                c = sg.segregation_test(res, "theil_h", "26163", compare_geoid="26125")
                summary.append(dict(design=design, run="contrast Wayne minus Oakland (H)", estimate=c["estimate"],
                                    lower=c["ci_lower"], upper=c["ci_upper"], validated=c["validated"]))
    summary.append(dict(group_quarters_tracts_excluded=len(excl)))
    summary.append({f"{d} | {l}": v for (d, l), v in tops.items()})
    (out_dir/"summary.json").write_text(json.dumps(summary, indent=1, default=float)+"\n")
    for s in summary:
        print(s)


if __name__ == "__main__":
    main(*sys.argv[1:3])
