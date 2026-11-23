# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 99 exploratory example: Medicaid expansion as a triple difference, and matching estimates for metro status.

Exploratory; author self-review, not independent; not a registered study.
(a) Triple difference: ACS 1-year B27010, states, 2010-2019. Group A = adults 19-64 (18-64 in 2010-2012 labels: lines
    18/34 and 33/50), group B = 65+ (lines 51/66, almost all on Medicare, so unaffected). Treated = the 2014 expansion
    cohort (Round 78 dates); comparison = states not expanded by 2019; later adopters (2015-2019) dropped.
(b) Matching: the Round 90 county frame (MI/NY/OH/PA, ACS 2019-2023 uninsured %, ERS metro status, poverty and 65+
    share): bias-corrected nearest-neighbour ATE and coarsened exact matching ATT.
Writes docs/audits/r99_matching_ddd_example.md.

Usage: scripts/r99_matching_ddd_example.py OUT_DIR
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/"scripts"))
import pandas as pd  # noqa: E402

from census.api import CensusAPIClient  # noqa: E402
from census.workflows_inference import estimate_effect  # noqa: E402
from census.workflows_microdata import difference_in_differences  # noqa: E402
from r78_medicaid_example import FIRST  # noqa: E402

YEARS = list(range(2010, 2020))


def panel():
    c = CensusAPIClient(); rows = []
    for y in YEARS:
        d = c.fetch(y, "*", "B27010", geo_level="state", dataset="acs1")
        if d is None:
            raise SystemExit(c.last_error)
        h = d[0]
        for r in d[1:]:
            st = r[h.index("state")]
            if st == "72":
                continue
            v = lambda ln: float(r[h.index(f"B27010_{ln:03}E")])  # noqa: E731
            first = FIRST.get(st)
            if first is not None and first != 2014:
                continue          # later adopters dropped
            tr = int(first == 2014)
            rows.append(dict(GEOID=st, Year=y, group="19-64", uninsured=100*(v(33)+v(50))/(v(18)+v(34)), treated=tr))
            rows.append(dict(GEOID=st, Year=y, group="65+", uninsured=100*v(66)/v(51), treated=tr))
    return pd.DataFrame(rows)


def main(out):
    od = Path(out); od.mkdir(parents=True, exist_ok=False)
    p = od/"panel.csv"; f = panel(); f.to_csv(p, index=False)
    r = difference_in_differences(str(p), "uninsured", "treated", 2014, design="triple", group="group",
                                  affected_group="19-64", product="1-year")
    if not r["success"]:
        raise SystemExit(r["error"])
    sys.argv = ["x"]
    import r90_positivity_example as r90
    import warnings
    warnings.simplefilter("ignore")
    from census.context_sources import fetch_ers
    parts = []
    for st in r90.STATES:
        u = r90.get(st, "S2701", ["S2701_C05_001E"], "subject"); pv = r90.get(st, "S1701", ["S1701_C03_001E"], "subject")
        a = r90.get(st, "DP05", ["DP05_0024PE"], "profile"); parts.append(u.join(pv).join(a))
    g = pd.concat(parts).rename(columns={"S2701_C05_001E": "unins", "S1701_C03_001E": "pov", "DP05_0024PE": "age65"})
    ers, _ = fetch_ers()
    g = g.join(ers["Metro2013"].rename("metro"), how="inner").dropna().reset_index()
    g["metro"] = pd.to_numeric(g.metro).astype(int)
    q = od/"counties.csv"; g.to_csv(q, index=False)
    nn = estimate_effect(str(q), "matching", "unins", treatment="metro", confounders=["pov", "age65"], method="nn")
    ce = estimate_effect(str(q), "matching", "unins", treatment="metro", confounders=["pov", "age65"], method="cem")
    e = r["effect"]
    L = ["# Round 99 example: Medicaid expansion as a triple difference, and matching (exploratory)", "",
         "Author self-review, not independent; not a registered study.", "",
         f"**Triple difference** (ACS 1-year B27010, 2010-2019; {f[f.treated == 1].GEOID.nunique()} states expanding in "
         f"2014 vs {f[f.treated == 0].GEOID.nunique()} not expanded by 2019; adults 19-64 vs 65+): "
         f"{e['estimate']:.2f} points of uninsurance (90% CI {e['lower']:.2f} to {e['upper']:.2f}; {e['clusters']} "
         f"states clustered; {'validated' if r['validated'] else 'exploratory'}). Round 78's staggered DiD found "
         "-1.23 points on all-age uninsurance (-2.18 to -0.27); the 65+ group absorbs state-specific shocks common to "
         "both age groups.", "",
         f"**Matching, metro status and county uninsured % (MI/NY/OH/PA, 2019-2023):** nearest-neighbour ATE "
         f"{nn['effect']['estimate']:.2f} ({nn['effect']['lower']:.2f} to {nn['effect']['upper']:.2f}); coarsened exact "
         f"matching ATT {ce['effect']['estimate']:.2f} ({ce['effect']['lower']:.2f} to {ce['effect']['upper']:.2f}; "
         f"{ce['effect']['share_treated_matched']:.0%} of metro counties matched). Round 90's overlap-weighted "
         "estimate was -1.66.", ""]
    (ROOT/"docs/audits/r99_matching_ddd_example.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main(sys.argv[1])
