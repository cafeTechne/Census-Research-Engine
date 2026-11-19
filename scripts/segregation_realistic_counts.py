# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 50: freeze the 2024 five-year MI/NY tract counts and published SEs used as the simulation truth.

Reads the cached API responses (read-only sqlite; no network) for B17001 and B19001, tract level,
states 26 and 36, and writes a compact gzip CSV (fixed mtime, so the bytes are reproducible):

- below / above: B17001_002 (below poverty) and B17001_031 (at or above), each with its published SE
  (MOE / 1.645).
- inc_lo / inc_mid / inc_hi: households with income < $35k (B19001_002-007), $35k-99,999 (008-013)
  and $100k+ (014-017); band SEs combined in quadrature.

Usage: scripts/segregation_realistic_counts.py CACHE_DB OUT.csv.gz
"""
import gzip
import io
import json
import sqlite3
import sys

import numpy as np
import pandas as pd

ENDPOINT = "https://api.census.gov/data/2024/acs/acs5"
GROUPS = {
    "B17001": {"below": ["B17001_002"], "above": ["B17001_031"]},
    "B19001": {"inc_lo": [f"B19001_{i:03d}" for i in range(2, 8)],
               "inc_mid": [f"B19001_{i:03d}" for i in range(8, 14)],
               "inc_hi": [f"B19001_{i:03d}" for i in range(14, 18)]},
}
Z90 = 1.645


def load(con, table, state):
    params = json.dumps({"for": "tract:*", "get": f"NAME,group({table})", "in": f"state:{state} county:*"})
    row = con.execute("select payload from responses where endpoint=? and params=?", (ENDPOINT, params)).fetchone()
    if row is None:
        raise SystemExit(f"{table} state {state} not in the cache")
    d = json.loads(row[0])
    df = pd.DataFrame(d[1:], columns=d[0])
    df["GEOID"] = df.state+df.county+df.tract
    return df.set_index("GEOID")


def build(cache_db):
    con = sqlite3.connect(f"file:{cache_db}?mode=ro", uri=True)
    parts = []
    for state in ("26", "36"):
        cols = {}
        for table, groups in GROUPS.items():
            df = load(con, table, state)
            for name, codes in groups.items():
                E = df[[c+"E" for c in codes]].astype(float)
                M = df[[c+"M" for c in codes]].astype(float)
                if (E < 0).any().any() or (M < 0).any().any():
                    raise SystemExit(f"annotated (negative) estimate or MOE in {table} {state}")
                cols[name] = E.sum(axis=1)
                cols[name+"_se"] = np.sqrt((M**2).sum(axis=1))/Z90
        parts.append(pd.DataFrame(cols))
    out = pd.concat(parts).sort_index()
    if out.isna().any().any():
        raise SystemExit("tracts differ between B17001 and B19001")
    out.insert(0, "county", out.index.str[:5])
    return out.reset_index()


def main(cache_db, out_path):
    out = build(cache_db)
    buf = io.StringIO()
    out.to_csv(buf, index=False, float_format="%.6f", lineterminator="\n")
    with open(out_path, "wb") as fh, gzip.GzipFile(fileobj=fh, mode="wb", mtime=0, filename="") as gz:
        gz.write(buf.getvalue().encode())
    print(len(out), "tracts;", out.county.nunique(), "counties")


if __name__ == "__main__":
    main(*sys.argv[1:3])
