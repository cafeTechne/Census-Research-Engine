# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 56 exploratory example: earnings and income inequality by disability, Michigan PUMS 2019-2023.

Exploratory; author self-review, not independent; no registration. Reads the cached public 5-year person file
(census.pums.fetch_pums; no API key; HTTP blocked). Writes results only (no microdata):
- earnings (PERNP) of people aged 25-64 with positive earnings, overall and by disability (DIS 1 vs 2);
- total personal income (PINCP) of people aged 25+, with zero incomes kept and negative incomes excluded.

Usage: scripts/r56_pums_inequality_example.py CACHE_DIR OUT_DIR
"""
import json
import sys
import warnings
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from census import pums  # noqa: E402
from census.pums_inequality import pums_inequality  # noqa: E402
from census.results import _jsonable  # noqa: E402

COLUMNS = ["AGEP", "DIS", "PERNP", "PINCP"]


def main(cache_dir, out_dir):
    warnings.simplefilter("ignore")
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=False)
    with patch("requests.sessions.Session.request", side_effect=RuntimeError("HTTP blocked")):
        df = pums.fetch_pums("26", 2023, product="5-year", record="person", columns=COLUMNS, cache_dir=cache_dir)
    runs = {
        "earnings_25_64_by_disability": pums_inequality(df, "PERNP", where="AGEP >= 25 and AGEP <= 64 and PERNP > 0", by="DIS"),
        "income_25plus": pums_inequality(df, "PINCP", where="AGEP >= 25 and PINCP >= 0"),
    }
    summary = {}
    for name, r in runs.items():
        r = dict(r); r["table"] = r["table"].to_dict("records")
        for g in r.get("groups", {}).values():
            g["table"] = g["table"].to_dict("records")
        summary[name] = _jsonable(r)
        print(name, "n =", r["n"])
        for row in r["table"]:
            print(f"  {row['measure']:>13} {row['estimate']:.4f} ({row['lower']:.4f}-{row['upper']:.4f}) validated={row['validated']}")
        for g, v in r.get("groups", {}).items():
            gi = [x for x in v["table"] if x["measure"] == "gini"][0]
            print(f"  group {g}: n = {v['n']}, Gini {gi['estimate']:.4f} ({gi['lower']:.4f}-{gi['upper']:.4f})")
        if "gini_difference" in r:
            d = r["gini_difference"]
            print(f"  Gini difference {d['groups']}: {d['estimate']:.4f} ({d['lower']:.4f} to {d['upper']:.4f})")
        print(" ", r["notes"])
    (out/"summary.json").write_text(json.dumps(summary, indent=1, default=str)+"\n")


if __name__ == "__main__":
    main(*sys.argv[1:3])
