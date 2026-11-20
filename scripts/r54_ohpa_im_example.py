# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 54 exploratory example: OH/PA county child poverty, naive slopes with IM using 4, 6 and 8 clusters.

Exploratory; author self-review, not independent; no registration. Reads cached 2024 five-year county API
responses (read-only sqlite; no network) for OH (39) and PA (42): B17001 (child poverty rate), B19013 (median
household income), B23025 (unemployment rate). OLS of the child poverty rate (percent) on log median income
and the unemployment rate (percent): HC3, and naive IM (observed-estimate target) with the within-state G = 4
and 6 assignments of docs/audits/im_cluster_counts_geometry.json and the Round 44 G = 8 assignment of
docs/audits/ohpa_geometry.json. ACS only; no WONDER data.

Usage: scripts/r54_ohpa_im_example.py CACHE_DB OUT_DIR
"""
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import statsmodels.api as sm  # noqa: E402

from census import derived  # noqa: E402
from census import im_clusters_core as imc  # noqa: E402

BELOW = [*range(4, 10), *range(18, 24)]
ABOVE = [*range(33, 39), *range(47, 53)]


def load(con, table, state):
    params = json.dumps({"for": "county:*", "get": f"NAME,group({table})", "in": f"state:{state}"})
    row = con.execute("select payload from responses where endpoint=? and params=?",
                      ("https://api.census.gov/data/2024/acs/acs5", params)).fetchone()
    if row is None:
        raise SystemExit(f"{table} {state} not cached")
    d = json.loads(row[0]); df = pd.DataFrame(d[1:], columns=d[0])
    df = df.loc[:, ~df.columns.duplicated()]
    df["GEOID"] = df.state+df.county
    return df.set_index("GEOID")


def frame(cache_db):
    con = sqlite3.connect(f"file:{cache_db}?mode=ro", uri=True)
    rows = []
    for st in ("39", "42"):
        p, inc, emp = (load(con, t, st) for t in ("B17001", "B19013", "B23025"))
        below = p[[f"B17001_{i:03d}E" for i in BELOW]].astype(float).sum(axis=1)
        above = p[[f"B17001_{i:03d}E" for i in ABOVE]].astype(float).sum(axis=1)
        un = derived.proportion(emp["B23025_005E"].astype(float).to_numpy(), emp["B23025_005M"].astype(float).to_numpy(),
                                emp["B23025_003E"].astype(float).to_numpy(), emp["B23025_003M"].astype(float).to_numpy(),
                                as_percent=True)
        rows.append(pd.DataFrame(dict(NAME=p.NAME, child_poverty=100*below/(below+above),
                                      log_income=np.log(inc["B19013_001E"].astype(float)),
                                      unemployment=un["estimate"].to_numpy(), PA=float(st == "42"))))
    return pd.concat(rows).reset_index()


def main(cache_db, out_dir):
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=False)
    f = frame(cache_db)
    g8 = json.loads((ROOT/"docs/audits/ohpa_geometry.json").read_text())["assignment"]
    g46 = json.loads((ROOT/"docs/audits/im_cluster_counts_geometry.json").read_text())["assignments"]["ohpa"]
    labels = {8: f.GEOID.map(g8).to_numpy(), 4: f.GEOID.map(g46["4"]).to_numpy(), 6: f.GEOID.map(g46["6"]).to_numpy()}
    X = np.column_stack((np.ones(len(f)), f.log_income, f.unemployment)); y = f.child_poverty.to_numpy()
    terms = ["log_income", "unemployment"]
    rows = []
    hc3 = sm.OLS(y, np.column_stack((X, f.PA))).fit(cov_type="HC3")
    for j, term in enumerate(terms, start=1):
        b, s = hc3.params[j], hc3.bse[j]
        rows.append(dict(method="OLS HC3 (with PA term)", term=term, estimate=b, lower=b-1.645*s, upper=b+1.645*s, df=None))
    for G in (4, 6, 8):
        s = imc.summarize(imc.cluster_coefficients(X, y, labels[G], "linear"))   # PA absorbed by within-state clusters
        for j, term in enumerate(terms, start=1):
            rows.append(dict(method=f"IM, G = {G}", term=term, estimate=s["estimate"][j], lower=s["lower"][j],
                             upper=s["upper"][j], df=s["df"]))
    out = pd.DataFrame(rows); out.to_csv(out_dir/"slopes.csv", index=False)
    print(out.round(3).to_string(index=False))
    (out_dir/"summary.json").write_text(json.dumps(dict(counties=int(len(f)), cluster_sizes={
        str(G): np.bincount(labels[G]).tolist() for G in (4, 6, 8)}), indent=1)+"\n")


if __name__ == "__main__":
    main(*sys.argv[1:3])
