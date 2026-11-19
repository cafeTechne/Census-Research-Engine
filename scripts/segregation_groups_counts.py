# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 52: freeze the tract counts and published SEs used as the simulation truth.

Reads the cached API responses (read-only sqlite; no network) and writes a compact gzip CSV (fixed mtime,
byte-reproducible), one row per (release, tract):

- 2024 five-year, MI (26), NY (36), OH (39), PA (42), from B03002 (Hispanic or Latino origin by race):
  white (003), black (004), asian (006), hisp (012), other (005 + 007 + 008 + 009, non-Hispanic AIAN,
  NHPI, some other race, two or more), nonblack (every B03002 component except 004: 003, 005-009, 012),
  nonhisp (002); and from B17001: below (002), above (031).
- 2019 five-year (2015-2019), MI and NY: below and above from B17001.

Sums of published lines get SEs combined in quadrature (MOE / 1.645). Columns not available for a release
are empty.

Usage: scripts/segregation_groups_counts.py CACHE_DB OUT.csv.gz
"""
import gzip
import io
import json
import sqlite3
import sys

import numpy as np
import pandas as pd

B03 = {"white": [3], "black": [4], "asian": [6], "hisp": [12], "other": [5, 7, 8, 9],
       "nonblack": [3, 5, 6, 7, 8, 9, 12], "nonhisp": [2]}
B17 = {"below": [2], "above": [31]}
PULLS = [(2024, s, "B03002", B03) for s in ("26", "36", "39", "42")] + \
        [(2024, s, "B17001", B17) for s in ("26", "36", "39", "42")] + \
        [(2019, s, "B17001", B17) for s in ("26", "36")]
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
    cols = ["release", "GEOID", "county"]+[c for g in (*B03, *B17) for c in (g, g+"_se")]
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
