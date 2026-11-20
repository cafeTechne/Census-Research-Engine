# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 62 exploratory example: OH/PA county child poverty as a binomial outcome with SCPC intervals.

Exploratory; author self-review, not independent; no registration. Cached 2024 county B17001/B19013/B23025 for OH
and PA (Round 54's sources; ACS only). Binomial regression of the share of children in poverty (trials = children
with poverty status) on log median income and the unemployment rate, with SCPC (validated for binomial at rho_bar
.15 since Round 62), next to the OLS SCPC result on the percentage (Round 58).

Usage: scripts/r62_binomial_scpc_example.py CACHE_DB OUT_DIR
"""
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/"scripts"))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import r54_ohpa_im_example as r54  # noqa: E402
from census.scpc import fit_scpc  # noqa: E402


def main(cache_db, out_dir):
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=False)
    f = r54.frame(cache_db)
    con = sqlite3.connect(f"file:{cache_db}?mode=ro", uri=True)
    kids = []
    for st in ("39", "42"):
        p = r54.load(con, "B17001", st)
        below = p[[f"B17001_{i:03d}E" for i in r54.BELOW]].astype(float).sum(axis=1)
        above = p[[f"B17001_{i:03d}E" for i in r54.ABOVE]].astype(float).sum(axis=1)
        kids.append(pd.DataFrame(dict(children=below+above, share=below/(below+above))))
    f = f.merge(pd.concat(kids).rename_axis("GEOID").reset_index(), on="GEOID")
    g = json.loads((ROOT/"docs/audits/ohpa_geometry.json").read_text())["coordinates"]
    coords = pd.DataFrame(dict(GEOID=g["GEOID"], lon=g["lon"], lat=g["lat"]))
    rows = []
    b = fit_scpc("share ~ log_income + unemployment", f, "binomial", trials="children", coords=coords)
    for _, t in b["table"].iterrows():
        rows.append(dict(model="binomial (log odds), SCPC rho_bar .15", term=t.term, estimate=t.estimate, lower=t.lower,
                         upper=t.upper, p_value=t.p_value, validated=b["validated"]))
    o = fit_scpc("child_poverty ~ log_income + unemployment", f, coords=coords)
    for _, t in o["table"].iterrows():
        rows.append(dict(model="OLS (percent), SCPC rho_bar .05", term=t.term, estimate=t.estimate, lower=t.lower,
                         upper=t.upper, p_value=t.p_value, validated=o["validated"]))
    out = pd.DataFrame(rows); out.to_csv(out_dir/"slopes.csv", index=False)
    print(out.round(4).to_string(index=False))
    (out_dir/"summary.json").write_text(json.dumps(dict(counties=int(len(f)), children=int(f.children.sum())), indent=1)+"\n")


if __name__ == "__main__":
    main(*sys.argv[1:3])
