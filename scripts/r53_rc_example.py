# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 53 exploratory example: county child poverty on income and unemployment with corrected slopes.

Exploratory; author self-review, not independent; no registration. Reads cached 2024 five-year county API
responses (read-only sqlite; no network) for MI and NY: B17001 (children under 18 below poverty / all children
with poverty status), B19013 (median household income), B23025 (unemployment among the civilian labour force).
Binomial models of the child poverty rate on log median income and the unemployment rate (both with ACS
sampling error) plus a NY indicator:
- naive binomial GLM with HC3 (fit_replicate, population target);
- regression calibration with bootstrap SEs (Round 46: exploratory for binomial);
- regression calibration with delete-one-area jackknife SEs (Round 53: validated for binomial).
Writes the coefficient tables and a summary.

Usage: scripts/r53_rc_example.py CACHE_DB OUT_DIR
"""
import json
import sqlite3
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from census import derived, models  # noqa: E402

Z90 = 1.645
BELOW = [*range(4, 10), *range(18, 24)]
ABOVE = [*range(33, 39), *range(47, 53)]


def load(con, table, state):
    params = json.dumps({"for": "county:*", "get": f"NAME,group({table})", "in": f"state:{state}"})
    row = con.execute("select payload from responses where endpoint=? and params=?",
                      ("https://api.census.gov/data/2024/acs/acs5", params)).fetchone()
    if row is None:
        raise SystemExit(f"{table} {state} not cached")
    d = json.loads(row[0]); df = pd.DataFrame(d[1:], columns=d[0])
    df = df.loc[:, ~df.columns.duplicated()]   # NAME appears twice (get and group)
    df["GEOID"] = df.state+df.county
    return df.set_index("GEOID")


def frame(cache_db):
    con = sqlite3.connect(f"file:{cache_db}?mode=ro", uri=True)
    rows = []
    for st in ("26", "36"):
        p, inc, emp = (load(con, t, st) for t in ("B17001", "B19013", "B23025"))
        below = p[[f"B17001_{i:03d}E" for i in BELOW]].astype(float).sum(axis=1)
        above = p[[f"B17001_{i:03d}E" for i in ABOVE]].astype(float).sum(axis=1)
        mi, mm = inc["B19013_001E"].astype(float), inc["B19013_001M"].astype(float)
        un = derived.proportion(emp["B23025_005E"].astype(float).to_numpy(), emp["B23025_005M"].astype(float).to_numpy(),
                                emp["B23025_003E"].astype(float).to_numpy(), emp["B23025_003M"].astype(float).to_numpy(),
                                as_percent=True)
        rows.append(pd.DataFrame(dict(NAME=p.NAME, children=below+above, child_poverty=below/(below+above),
                                      log_income=np.log(mi), log_income_se=mm/Z90/mi,
                                      unemployment=un["estimate"].to_numpy(), unemployment_se=un["moe"].to_numpy()/Z90,
                                      NY=float(st == "36"))))
    f = pd.concat(rows).reset_index()
    f["Year"] = 2024
    return f


def main(cache_db, out_dir):
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=False)
    f = frame(cache_db)
    formula = "child_poverty ~ log_income + unemployment + NY"
    err = ["log_income", "unemployment"]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        naive = models.fit_replicate(formula, f, model="binomial", trials="children", scale="robust", target="population")
        boot = models.regression_calibration(formula, f, err, model="binomial", trials="children")
        jack = models.regression_calibration(formula, f, err, model="binomial", trials="children", se_method="jackknife")
    keep = ["term", "estimate", "ci_lower", "ci_upper", "p_value"]
    tabs = {"naive_hc3": naive.coefficients[keep], "rc_bootstrap": boot.coefficients[keep + ["se_total"]],
            "rc_jackknife": jack.coefficients[keep + ["se_total"]]}
    for k, t in tabs.items():
        t.to_csv(out_dir/f"{k}.csv", index=False)
        print(k); print(t.round(4).to_string(index=False))
    summary = dict(counties=int(len(f)), children=int(f.children.sum()),
                   reliability=jack.diagnostics["reliability_ratio"],
                   validated=dict(rc_bootstrap=boot.diagnostics["regression_calibration_validated"],
                                  rc_jackknife=jack.diagnostics["regression_calibration_validated"]),
                   slopes={k: t.set_index("term").loc[err, ["estimate", "ci_lower", "ci_upper"]].to_dict("index")
                           for k, t in tabs.items()})
    (out_dir/"summary.json").write_text(json.dumps(summary, indent=1, default=float)+"\n")
    print(json.dumps(summary["reliability"]), summary["validated"])


if __name__ == "__main__":
    main(*sys.argv[1:3])
