# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 51 exploratory example: the counties Round 50 refused for negative replicate estimates.

Exploratory; author self-review, not independent; no registration. Reads the cached 2024 five-year tract
VRE files (B17001, B19001; HTTP blocked), as the Round 50 example does, and for each county with a
negative replicate estimate compares:
- ``clip``: all tracts, negative replicate group counts set to zero before the refits (Round 51 default);
- ``drop``: the affected tracts removed (a naive workaround, shown for comparison only: it changes the
  county being described).
Writes county rows (no tract data) and a summary.

Usage: CENSUS_VRE_DIR=<main>/.cache/vre scripts/r51_negative_replicates_example.py OUT_DIR
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/"scripts"))
import r50_segregation_example as r50  # noqa: E402
from census import segregation as sg  # noqa: E402
from census.variance import REPLICATE_COLUMNS  # noqa: E402

KEEP = ["GEOID", "statistic", "estimate", "se", "ci_lower", "ci_upper", "validated", "noise_level",
        "clipped_replicates", "tracts"]


def main(out_dir):
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=False)
    pov, inc = r50.load()
    summary = []
    for design, long, groups in (("poverty_two_groups", pov, ["below", "above"]),
                                 ("income_three_groups", inc, list(r50.BANDS))):
        neg = (long[list(REPLICATE_COLUMNS)] < 0).any(axis=1)
        bad_tracts = set(long.loc[neg, "GEOID"])
        counties = sorted({g[:5] for g in bad_tracts})
        sub = long[long.GEOID.str[:5].isin(counties)]
        f, rep = r50.frame(sub, groups)
        clip = sg.segregation_replicate(f, groups, rep)
        f2, rep2 = r50.frame(sub[~sub.GEOID.isin(bad_tracts)], groups)
        drop = sg.segregation_replicate(f2, groups, rep2)
        m = clip[KEEP].merge(drop[["GEOID", "statistic", "estimate", "se", "tracts"]], on=["GEOID", "statistic"],
                             suffixes=("", "_drop"))
        m.to_csv(out_dir/f"{design}.csv", index=False)
        summary.append(dict(design=design, counties=counties, affected_tracts=len(bad_tracts),
                            rows=int(len(m)), validated_clip=int(m.validated.sum()),
                            clipped_cells=dict(zip(m.GEOID, map(int, m.clipped_replicates))),
                            median_se_ratio_drop_over_clip=float((m.se_drop/m.se).median())))
        print(m[["GEOID", "statistic", "estimate", "se", "validated", "noise_level", "clipped_replicates",
                 "estimate_drop", "se_drop", "tracts", "tracts_drop"]].round(4).to_string())
    (out_dir/"summary.json").write_text(json.dumps(summary, indent=1)+"\n")
    for s in summary:
        print(s)


if __name__ == "__main__":
    main(sys.argv[1])
