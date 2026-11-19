# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 32 exploratory example: disability, insurance, poverty and earnings, Michigan PUMS 2019-2023 (2020 PUMAs throughout).

Exploratory; author self-review, not independent; no registration. Downloads the public
5-year person file once (census.pums.fetch_pums; no API key). Writes results only (no microdata).

Usage: scripts/r32_pums_tests_example.py CACHE_DIR OUT_DIR
"""
import json
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd

from census import pums, pums_inference as pi
from census.results import _jsonable

COLUMNS = ["AGEP", "DIS", "PRIVCOV", "PUBCOV", "HICOV", "POVPIP", "PERNP", "PUMA"]


def insurance_type(df):
    priv, pub = df.PRIVCOV.eq(1), df.PUBCOV.eq(1)
    return np.select([priv & ~pub, pub & ~priv, priv & pub], ["private_only", "public_only", "both"], "none")


def main(cache_dir, out_dir):
    warnings.simplefilter("ignore")
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=False)
    df = pums.fetch_pums("26", 2023, product="5-year", record="person", columns=COLUMNS, cache_dir=cache_dir)
    df["INSTYPE"] = insurance_type(df)
    df["DISABLED"] = np.where(df.DIS.eq(1), "disabled", "not_disabled")
    adults = "AGEP >= 19 and AGEP <= 64"
    res = {}
    res["insurance_by_disability"] = pi.independence_test(df, "INSTYPE", "DISABLED", where=adults)
    res["poverty_by_disability"] = pi.two_by_two(df, "DIS == 1", "POVPIP < 100", where=adults)
    working = "AGEP >= 25 and AGEP <= 64 and PERNP > 0"
    res["earnings_means"] = pi.compare_means(df, "PERNP", "DISABLED", where=working)
    res["earnings_medians"] = pi.compare_medians(df, "PERNP", "DISABLED", where=working)
    disabled = df.query(adults+" and DIS == 1")
    counts = disabled.groupby("PUMA").size()
    puma = counts[counts >= 30].idxmin()
    where = f"{adults} and DIS == 1 and PUMA == {puma!r}" if isinstance(puma, str) else f"{adults} and DIS == 1 and PUMA == {puma}"
    res["uninsured_small_puma"] = dict(
        puma=str(puma), records=int(counts[puma]),
        korn_graubard=pi.proportion_interval(df, "HICOV == 2", where=where),
        wald=pi.proportion_interval(df, "HICOV == 2", where=where, method="wald"))
    meta = dict(state="26", release="2019-2023 5-year PUMS (one PUMA column, 2020 PUMAs)", person_records=int(len(df)),
                source=df.attrs.get("source_url"), sha256=df.attrs.get("sha256"),
                note="Exploratory; author self-review, not independent; results only, no microdata")
    (out/"results.json").write_text(json.dumps(_jsonable(dict(meta=meta, results=res)), indent=2, default=str)+"\n")
    ind = res["insurance_by_disability"]
    print("independence", ind["p_value"], ind["design_effect_mean"], "pearson", ind["alternatives"]["pearson_ignoring_design"]["p"])
    print("2x2", {k: res["poverty_by_disability"][k] for k in ("odds_ratio", "relative_risk", "difference_of_proportions")})
    print("means", res["earnings_means"]["means"], res["earnings_means"]["p_value"])
    print("medians", res["earnings_medians"]["difference"])
    print("puma", res["uninsured_small_puma"])


if __name__ == "__main__":
    main(*sys.argv[1:3])
