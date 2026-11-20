# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 57: freeze the 2024 MI/NY B03002 tract counts and SEs used as the simulation truth (six groups).

Reads the cached API responses (read-only sqlite; no network) and writes a compact gzip CSV (fixed mtime,
byte-reproducible), one row per 2024 MI (26) / NY (36) tract, B03002 groups: white (003), black (004), asian (006),
hisp (012), multi (009, two or more races), other3 (005 + 007 + 008: non-Hispanic AIAN, NHPI, some other race),
nonblack (every component except 004), nonhisp (002). Sums of lines combine SEs (MOE / 1.645) in quadrature.

Usage: scripts/segregation_r57_counts.py CACHE_DB OUT.csv.gz
"""
import gzip
import io
import json
import sqlite3
import sys

import numpy as np
import pandas as pd

B03 = {"white": [3], "black": [4], "asian": [6], "hisp": [12], "multi": [9], "other3": [5, 7, 8],
       "nonblack": [3, 5, 6, 7, 8, 9, 12], "nonhisp": [2]}
PULLS = [(2024, s, "B03002", B03) for s in ("26", "36")]
Z90 = 1.645


def load(con, year, table, state):
    endpoint = f"https://api.census.gov/data/{year}/acs/acs5"
    params = json.dumps({"for": "tract:*", "get": f"NAME,group({table})", "in": f"state:{state} county:*"})
    row = con.execute("select payload from responses where endpoint=? and params=?", (endpoint, params)).fetchone()
    if row is None:
        raise SystemExit(f"{year} {table} state {state} not in the cache")
    d = json.loads(row[0])
    df = pd.DataFrame(d[1:], columns=d[0])
    df["GEOID"] = df.state+df.county+df.tract
    return df.set_index("GEOID")


def build(cache_db):
    con = sqlite3.connect(f"file:{cache_db}?mode=ro", uri=True)
    frames = {}
    for year, state, table, groups in PULLS:
        df = load(con, year, table, state)
        cols = {}
        for name, lines in groups.items():
            codes = [f"{table}_{i:03d}" for i in lines]
            E = df[[c+"E" for c in codes]].astype(float); M = df[[c+"M" for c in codes]].astype(float)
            if (E < 0).any().any() or (M < 0).any().any():
                raise SystemExit(f"annotated (negative) estimate or MOE in {year} {table} {state}")
            cols[name] = E.sum(axis=1); cols[name+"_se"] = np.sqrt((M**2).sum(axis=1))/Z90
        part = pd.DataFrame(cols)
        key = (year, state)
        frames[key] = part if key not in frames else frames[key].join(part, how="outer")
    out = []
    for (year, state), f in sorted(frames.items()):
        if f.isna().any().any():
            raise SystemExit(f"tracts differ between tables for {year} {state}")
        f = f.copy(); f.insert(0, "release", year); f.insert(1, "county", f.index.str[:5])
        out.append(f)
    out = pd.concat(out).rename_axis("GEOID").reset_index()
    cols = ["release", "GEOID", "county"]+[c for g in B03 for c in (g, g+"_se")]
    return out.reindex(columns=cols).sort_values(["release", "GEOID"]).reset_index(drop=True)


def main(cache_db, out_path):
    out = build(cache_db)
    buf = io.StringIO()
    out.to_csv(buf, index=False, float_format="%.6f", lineterminator="\n")
    with open(out_path, "wb") as fh, gzip.GzipFile(fileobj=fh, mode="wb", mtime=0, filename="") as gz:
        gz.write(buf.getvalue().encode())
    print(out.groupby("release").size().to_dict(), "tracts;", out.groupby("release").county.nunique().to_dict(), "counties")


if __name__ == "__main__":
    main(*sys.argv[1:3])
