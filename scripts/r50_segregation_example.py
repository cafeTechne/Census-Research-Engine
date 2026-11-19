# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 50 exploratory example: county poverty and income segregation in MI/NY with the noise-level gate.

Exploratory; author self-review, not independent; no registration. Reads the cached 2024 five-year
tract VRE files (B17001, B19001; HTTP blocked) and runs census.segregation_replicate on:
- two groups: below poverty (B17001_002) vs at or above (B17001_031);
- three groups: households with income < $35k, $35k-99,999, $100k+ (B19001 bands summed, replicates
  summed band by band).
Counties with a negative replicate estimate in any tract are refused by the engine (strict policy, no
clipping); they are left out and listed. Writes county rows (no tract data) and a summary of how many
counties each gate validates.

Usage: CENSUS_VRE_DIR=<main>/.cache/vre scripts/r50_segregation_example.py OUT_DIR
"""
import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pandas as pd

from census import replicate, segregation as sg
from census.variance import REPLICATE_COLUMNS

BANDS = {"inc_lo": range(2, 8), "inc_mid": range(8, 14), "inc_hi": range(14, 18)}
COLS = ["estimate", *REPLICATE_COLUMNS]


def load():
    pov, inc = [], []
    with patch("requests.sessions.Session.request", side_effect=RuntimeError("HTTP blocked")):
        for st in ("26", "36"):
            pov.append(replicate.fetch_vre("B17001", 2024, "tract", state_code=st, lines=[2, 31]))
            inc.append(replicate.fetch_vre("B19001", 2024, "tract", state_code=st, lines=list(range(2, 18))))
    pov = pd.concat(pov, ignore_index=True)
    pov["variable"] = pov.variable.map({"B17001_002": "below", "B17001_031": "above"})
    inc = pd.concat(inc, ignore_index=True)
    band = {f"B19001_{i:03d}": name for name, rng in BANDS.items() for i in rng}
    inc["variable"] = inc.variable.map(band)
    inc = inc.groupby(["GEOID", "variable"], as_index=False)[COLS].sum()
    return pov, inc


def frame(long, groups):
    f = long.pivot(index="GEOID", columns="variable", values="estimate")[groups].reset_index()
    f["Year"] = 2024
    rep = long[["GEOID", "variable", *REPLICATE_COLUMNS]].copy(); rep["Year"] = 2024
    return f, rep


def summarise(out, design):
    rows = []
    for stat, part in out.groupby("statistic"):
        rows.append(dict(design=design, statistic=stat, counties=int(len(part)),
                         round28_gate=int((part.max_count_cv <= sg.MAX_VALIDATED_COUNT_CV).sum()),
                         validated=int(part.validated.sum()),
                         noise_median=float(part.noise_level.median()),
                         noise_max=float(part.noise_level.max())))
    return rows


def main(out_dir):
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=False)
    pov, inc = load()
    keep = ["GEOID", "statistic", "estimate", "naive_estimate", "se", "ci_lower", "ci_upper", "bias_correction",
            "validated", "noise_level", "max_count_cv", "tracts", "zero_total_tracts"]
    summary = []
    for design, long, groups in (("poverty_two_groups", pov, ["below", "above"]),
                                 ("income_three_groups", inc, list(BANDS))):
        neg = (long[list(REPLICATE_COLUMNS)] < 0).any(axis=1)
        refused = sorted(long.loc[neg, "GEOID"].str[:5].unique())
        long = long[~long.GEOID.str[:5].isin(refused)]
        f, rep = frame(long, groups)
        res = sg.segregation_replicate(f, groups, rep)
        summary.append(dict(design=design, refused_negative_replicates=refused))
        res[keep].to_csv(out_dir/f"{design}.csv", index=False)
        summary += summarise(res, design)
        h = res[res.statistic == "theil_h"].sort_values("estimate", ascending=False).head(5)
        print(design, "top H:", [(g, round(e, 3), round(lo, 3), round(hi, 3), v)
                                 for g, e, lo, hi, v in zip(h.GEOID, h.estimate, h.ci_lower, h.ci_upper, h.validated)])
    (out_dir/"summary.json").write_text(json.dumps(summary, indent=1)+"\n")
    for s in summary:
        print(s)


if __name__ == "__main__":
    main(sys.argv[1])
