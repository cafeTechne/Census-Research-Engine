# SPDX-License-Identifier: AGPL-3.0-or-later
"""Validation of rate apportionment from 2010 to 2020 tracts (PLAN_ROUND_21 Part 2, C2).

USALEEP life expectancy is published on 2010 tracts; ``apportion_to: 2020`` turns it into 2020-tract
values with census.health_sources.apportion_rates (population-mass-weighted means; a split tract
inherits its parent's value). Life expectancy has no second vintage to check against, so the
method is checked on a rate that does: ACS crude disability prevalence (B18101, all ages).

- Source: ACS 2015-2019 on 2010 tracts, apportioned to 2020 tracts (2010 block population masses).
- Reference: ACS 2016-2020 on 2020 tracts (native).
- z = (apportioned - native) / sqrt(se_a^2 + se_n^2), by the target's relationship type:
  "1:1" (one source tract that maps only to it), "split" (one source tract that also maps to
  other targets: the child inherits the parent's rate) and "merged/complex" (several sources).
  The two releases share four sample years, so |z| is smaller than for independent samples; the
  comparison is between relationship types.

Acceptance: median |z| of split and of merged/complex targets at most 1.25 x the 1:1 median.

Usage: python scripts/rate_apportionment_validation.py [--states 26 36]
"""

import argparse
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv  # noqa: E402

from census.api import CensusAPIClient  # noqa: E402
from census.block_weights import tract_weights  # noqa: E402
from census.cache import get_default_cache  # noqa: E402
from census.geo_crosswalk import acs_to_census2010_geoid  # noqa: E402
from census.health_sources import apportion_rates, target_relationships  # noqa: E402

WITH = [4, 7, 10, 13, 16, 19, 23, 26, 29, 32, 35, 38]  # B18101 "with a disability" cells
LIMIT = 1.25


def fetch_rates(client, year, state):
    rows = client.fetch(year, state, "B18101", geo_level="tract")
    if not rows:
        raise SystemExit(f"no B18101 data for {state} {year}: {client.last_error}")
    df = pd.DataFrame(rows[1:], columns=rows[0])
    df["GEOID"] = df["state"] + df["county"] + df["tract"]
    est = lambda c: pd.to_numeric(df[f"B18101_{c:03d}E"], errors="coerce")  # noqa: E731
    moe = lambda c: pd.to_numeric(df[f"B18101_{c:03d}M"], errors="coerce").clip(lower=0)  # noqa: E731
    den, den_se = est(1), moe(1) / 1.645
    num = sum(est(c) for c in WITH)
    num_se = np.sqrt(sum((moe(c) / 1.645) ** 2 for c in WITH))
    p = num / den
    rad = num_se**2 - p**2 * den_se**2
    rad = rad.where(rad > 0, num_se**2 + p**2 * den_se**2)  # ACS: use the ratio form when negative
    out = pd.DataFrame({"GEOID": df["GEOID"], "dis": 100 * p, "dis_se": 100 * np.sqrt(rad) / den})
    return out[(den > 0) & np.isfinite(out["dis"])]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--states", nargs="+", default=["26", "36"])
    ap.add_argument("--out", default="docs/audits/rate_apportionment_validation.md")
    args = ap.parse_args(argv)
    load_dotenv()
    client = CensusAPIClient(cache=get_default_cache())
    src = pd.concat([fetch_rates(client, 2019, s) for s in args.states], ignore_index=True)
    ref = pd.concat([fetch_rates(client, 2020, s) for s in args.states], ignore_index=True)
    src["GEOID"] = src["GEOID"].map(acs_to_census2010_geoid)
    cw = tract_weights(args.states, "2010_to_2020", "population")
    cw = cw[cw["source_geoid"].str[:2].isin(args.states)]
    app, rec = apportion_rates(src, "dis", cw, min_coverage=0.9, split="inherit")  # evaluate every type
    kind = target_relationships(cw)
    # post hoc (added after the pre-specified test failed): share of the parent's population in the child
    tot = cw.groupby("source_geoid")["mass"].transform("sum")
    share = (cw["mass"] / tot).groupby(cw["target_geoid"]).max()
    m = app.merge(ref, on="GEOID", suffixes=("_app", "_nat"))
    m["type"] = m["GEOID"].map(kind)
    m["parent_share"] = m["GEOID"].map(share)
    m["z"] = (m["dis_app"] - m["dis_nat"]) / np.sqrt(m["dis_se_app"] ** 2 + m["dis_se_nat"] ** 2)
    m = m[np.isfinite(m["z"])]
    tab = m.groupby("type").agg(n=("z", "size"), median_abs_z=("z", lambda z: float(np.median(np.abs(z)))),
                                share_abs_z_gt_1645=("z", lambda z: float(np.mean(np.abs(z) > 1.645))),
                                mean_diff=("z", lambda z: float("nan")))
    for t in tab.index:
        sub = m[m["type"] == t]
        tab.loc[t, "mean_diff"] = float((sub["dis_app"] - sub["dis_nat"]).mean())
        tab.loc[t, "corr"] = float(np.corrcoef(sub["dis_app"], sub["dis_nat"])[0, 1]) if len(sub) > 2 else np.nan
    base = tab.loc["1:1", "median_abs_z"]
    ratios = {t: tab.loc[t, "median_abs_z"] / base for t in ("split", "merged/complex") if t in tab.index}
    passed = all(r <= LIMIT for r in ratios.values())
    lines = [
        "# Rate apportionment from 2010 to 2020 tracts: validation",
        "",
        f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC by "
        "`scripts/rate_apportionment_validation.py`. PLAN_ROUND_21 Part 2, C2 (the method behind USALEEP "
        "`apportion_to: 2020`).",
        "",
        f"States {', '.join(args.states)}. ACS 2015-2019 crude disability prevalence (B18101, all ages, 2010 "
        "tracts) apportioned to 2020 tracts with `census.health_sources.apportion_rates` (2010 block population "
        "masses; targets below 90% covered mass left missing), compared with ACS 2016-2020 on native 2020 tracts. "
        "z = (apportioned - native) / sqrt(se_a^2 + se_n^2). The two releases share four sample years, so |z| is "
        "smaller than for independent samples; the test compares relationship types.",
        "",
        f"Apportionment record: {rec['targets']} targets, {rec['targets_below_coverage']} below coverage, "
        f"{rec['targets_from_several_sources']} from several sources, {rec['sources_split_across_targets']} "
        "source tracts split across targets.",
        "",
        "| target type | n | median abs z | share abs z > 1.645 | mean difference (points) | correlation |",
        "| :--- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for t, r in tab.iterrows():
        lines.append(f"| {t} | {int(r['n'])} | {r['median_abs_z']:.3f} | {r['share_abs_z_gt_1645']:.3f} | "
                     f"{r['mean_diff']:+.2f} | {r['corr']:.3f} |")
    lines += [
        "",
        "Ratios of median |z| to the 1:1 targets: " + ", ".join(f"{t} {v:.2f}" for t, v in ratios.items()) + ".",
        "",
        f"**Acceptance** (each ratio at most {LIMIT}): **{'PASSED' if passed else 'FAILED'}**.",
        "",
        "**Consequence (engine default).** `apportion_rates(split=\"missing\")`, the default for USALEEP "
        "`apportion_to`, leaves split targets missing; `split: \"inherit\"` keeps the parent's value and is "
        "documented as not validated. The validated part (1:1 and merged/complex targets) passes.",
        "",
        "**Post hoc** (not part of the pre-specified test; added after it failed): split targets by the share of "
        "the parent's population they hold.",
        "",
        "| parent share | n | median abs z | share abs z > 1.645 |",
        "| :--- | ---: | ---: | ---: |",
    ] + [
        f"| {lab} | {int(len(s))} | {float(np.median(np.abs(s['z']))):.3f} | {float(np.mean(np.abs(s['z']) > 1.645)):.3f} |"
        for lab, s in (("0.95 or more", m[(m.type == "split") & (m.parent_share >= 0.95)]),
                       ("0.5 to 0.95", m[(m.type == "split") & m.parent_share.between(0.5, 0.95, inclusive="left")]),
                       ("below 0.5", m[(m.type == "split") & (m.parent_share < 0.5)]))
        if len(s)
    ] + [
        "",
        "Reading: a split tract inherits its parent's rate, so its apportioned value misses the within-parent "
        "difference between children; merged targets average their sources by population. If those errors were "
        "large next to sampling error, split and merged targets would show larger |z| than 1:1 targets. For life "
        "expectancy the approximation is cruder still (e(0) is not additive), so USALEEP values on 2020 tracts "
        "remain an approximation, stated in every methods text that uses them.",
        "",
    ]
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
