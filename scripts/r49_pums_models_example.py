# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 49 exploratory example: survey-weighted models on the Michigan PUMS 2019-2023 person file.

Exploratory; author self-review, not independent; no registration. Reads the cached public 5-year person
file (census.pums.fetch_pums; no API key; HTTP blocked). Writes results only (no microdata).

Usage: scripts/r49_pums_models_example.py CACHE_DIR OUT_DIR
"""
import json
import sys
import warnings
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np

from census import pums
from census.pums_models import fit_pums_model
from census.results import _jsonable

COLUMNS = ["AGEP", "DIS", "HICOV", "POVPIP", "PERNP"]


def main(cache_dir, out_dir):
    warnings.simplefilter("ignore")
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=False)
    with patch("requests.sessions.Session.request", side_effect=RuntimeError("HTTP blocked")):
        df = pums.fetch_pums("26", 2023, product="5-year", record="person", columns=COLUMNS, cache_dir=cache_dir)
    df["disabled"] = df.DIS.eq(1).astype(float)
    df["age10"] = (df.AGEP-45)/10
    df["pov_band"] = np.select([df.POVPIP < 100, df.POVPIP < 200, df.POVPIP < 400], [0, 1, 2], 3).astype(float)
    df.loc[df.POVPIP.isna(), "pov_band"] = np.nan
    df["uninsured"] = df.HICOV.eq(2).astype(float)
    df["log_earn"] = np.log(df.PERNP.where(df.PERNP > 0))
    adults = "AGEP >= 25 and AGEP <= 64"
    res = {
        "poverty_band_ordered_logit": fit_pums_model("pov_band ~ disabled + age10", df, "ordered_logit", where=adults),
        "poverty_band_ordered_probit": fit_pums_model("pov_band ~ disabled + age10", df, "ordered_probit", where=adults),
        "uninsured_probit": fit_pums_model("uninsured ~ disabled + age10", df, "probit", where=adults),
        "median_log_earnings": fit_pums_model("log_earn ~ disabled + age10", df, "median",
                                              where=adults+" and PERNP > 0"),
    }
    for k, r in res.items():
        r["table"] = r["table"].to_dict("records")
    (out/"results.json").write_text(json.dumps(_jsonable(res), indent=2, default=str)+"\n")
    for k, r in res.items():
        print(k, "n", r["n"], "validated", r["validated"])
        for row in r["table"]:
            print("  %-28s %.4f (%.4f, %.4f)" % (row["term"], row["estimate"], row["lower"], row["upper"]))


if __name__ == "__main__":
    main(*sys.argv[1:3])
