# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 66: freeze the 2019-2023 tract counts and published SEs of GA, TX and AZ (simulation truth for S).

Same definitions as scripts/segregation_groups_counts.py (Round 52): from B03002, black (004) and nonblack (003,
005-009, 012); from B17001, below (002) and above (031); SE = MOE / 1.645 (band SEs in quadrature). Read from the
engine's API cache (filled by scripts/r66_fetch.py); writes a gzip CSV with a fixed mtime.

Usage: scripts/r66_segregation_counts.py OUT.csv.gz
"""
import gzip
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from census.workflows import _client  # noqa: E402

YEAR, STATES = 2023, ("13", "48", "04")
GROUPS = {"B03002": {"black": [4], "nonblack": [3, 5, 6, 7, 8, 9, 12]}, "B17001": {"below": [2], "above": [31]}}


def main(out):
    c = _client(); parts = []
    for s in STATES:
        fr = None
        for table, groups in GROUPS.items():
            rows = c.fetch(YEAR, s, table, geo_level="tract")
            if rows is None:
                raise SystemExit(f"{table} {s} not available: {c.last_error}")
            d = pd.DataFrame(rows[1:], columns=rows[0]); d["GEOID"] = d.state+d.county+d.tract
            g = d[["GEOID"]].copy()
            for name, lines in groups.items():
                est = np.sum([pd.to_numeric(d[f"{table}_{i:03d}E"]) for i in lines], axis=0)
                moe = np.sqrt(np.sum([np.maximum(pd.to_numeric(d[f"{table}_{i:03d}M"]), 0)**2 for i in lines], axis=0))
                g[name] = est; g[name+"_se"] = moe/1.645
            fr = g if fr is None else fr.merge(g, on="GEOID")
        parts.append(fr)
    df = pd.concat(parts, ignore_index=True)
    df.insert(0, "release", YEAR); df.insert(2, "county", df.GEOID.str[:5])
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as fh:
        fh.write(df.sort_values("GEOID").round(6).to_csv(index=False).encode())
    Path(out).write_bytes(buf.getvalue())
    print(len(df), "tracts")


if __name__ == "__main__":
    main(sys.argv[1])
