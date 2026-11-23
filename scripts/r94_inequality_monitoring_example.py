# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 94 exploratory example: WHO inequality monitoring of family poverty by race/ethnicity, Michigan counties.

Exploratory; author self-review, not independent; not a registered study. VRE files B17010, B17010H, B17010I (lines
1-2), 2020-2024: White alone not Hispanic, Hispanic or Latino, and all other non-Hispanic families (derived on every
replicate), as in Round 76 (scripts/r76_disparity_example.py); WHO measures with the data-selected best group.
The 2015-2019 VRE list has no race-iterated tables, so the change between releases uses person poverty by age group
(B17001: under 18, 18-64, 65+; both releases) instead. Counties where any group
has a rate CV above .30 are reported as outside the validated range. Writes docs/audits/r94_inequality_monitoring_example.md.

Usage: scripts/r94_inequality_monitoring_example.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from census.inequality_monitoring import monitoring_measures  # noqa: E402
from census.replicate import REPLICATE_COLUMNS, fetch_vre  # noqa: E402

COLS = ["estimate"]+REPLICATE_COLUMNS
GROUPS = ["r_wnh", "r_hisp", "r_oth"]; POPS = ["n_wnh", "n_hisp", "n_oth"]


def inputs(year, st="26"):
    def lines(table):
        f = fetch_vre(table, year, "county", state_code=st, lines=[1, 2])
        f["line"] = f["variable"].str[-3:].astype(int)
        return {ln: g.set_index("GEOID")[COLS].astype(float) for ln, g in f.groupby("line")}
    tot, h, i = lines("B17010"), lines("B17010H"), lines("B17010I")
    geo = tot[1].index
    n = {"wnh": h[1].reindex(geo), "hisp": i[1].reindex(geo)}; b = {"wnh": h[2].reindex(geo), "hisp": i[2].reindex(geo)}
    n["oth"] = tot[1]-n["wnh"]-n["hisp"]; b["oth"] = tot[2]-b["wnh"]-b["hisp"]
    f = pd.DataFrame(index=geo); reps = []
    for g in ("wnh", "hisp", "oth"):
        with np.errstate(divide="ignore", invalid="ignore"):
            rate = b[g]/n[g]
        f[f"r_{g}"] = rate["estimate"]; f[f"n_{g}"] = n[g]["estimate"]
        for name, val in ((f"r_{g}", rate), (f"n_{g}", n[g])):
            reps.append(val.assign(variable=name, Year=year).reset_index())
    return f.reset_index().assign(Year=year), pd.concat(reps, ignore_index=True)


AGE = {"a_lt18": range(0, 6), "a_18_64": range(6, 11), "a_65p": range(11, 13)}


def age_inputs(year, st="26"):
    below = [4+k for k in range(13)]+[18+k for k in range(13)]
    above = [33+k for k in range(13)]+[47+k for k in range(13)]
    f = fetch_vre("B17001", year, "county", state_code=st, lines=below+above)
    f["line"] = f["variable"].str[-3:].astype(int)
    t = {ln: g.set_index("GEOID")[COLS].astype(float) for ln, g in f.groupby("line")}
    out = pd.DataFrame(index=t[4].index); reps = []
    for band, idx in AGE.items():
        b = sum(t[below[k]]+t[below[13+k]] for k in idx); a = sum(t[above[k]]+t[above[13+k]] for k in idx)
        n = a+b; r = b/n
        out[f"r_{band}"] = r["estimate"]; out[f"n_{band}"] = n["estimate"]
        for name, val in ((f"r_{band}", r), (f"n_{band}", n)):
            reps.append(val.assign(variable=name, Year=year).reset_index())
    return out.reset_index().assign(Year=year), pd.concat(reps, ignore_index=True)


def main():
    f2, r2 = inputs(2024)
    frame = f2[(f2[GROUPS] > 0).all(axis=1) & (f2[POPS] > 0).all(axis=1)]
    cur = monitoring_measures(frame, GROUPS, POPS, r2, reference="best")
    (a1, ar1), (a2, ar2) = age_inputs(2019), age_inputs(2024)
    ag = [f"r_{b}" for b in AGE]; ap = [f"n_{b}" for b in AGE]
    chg = monitoring_measures(pd.concat([a1, a2], ignore_index=True), ag, ap, pd.concat([ar1, ar2], ignore_index=True),
                              reference="best", compare_years=[2019, 2024])
    par = cur[cur.measure == "par"]; v = par[par.validated]
    big = v.assign(p=v.estimate*100).sort_values("estimate", ascending=False).head(5)
    names = {"r_wnh": "White non-Hispanic", "r_hisp": "Hispanic", "r_oth": "other non-Hispanic"}
    best_share = par.reference.map(names).value_counts()
    cp = chg[(chg.measure == "par") & chg.validated]
    L = ["# Round 94 example: WHO inequality monitoring, family poverty by race/ethnicity, Michigan counties (exploratory)", "",
         "Author self-review, not independent; not a registered study. Family poverty rates (B17010, B17010H, B17010I "
         "with VRE replicates) for White non-Hispanic, Hispanic and other non-Hispanic families, 2020-2024 "
         "releases. Reference: the best (lowest-rate) group, re-selected in every replicate.", "",
         f"**2020-2024:** {par.GEOID.nunique()} counties; {len(v)} within the validated range (all group CVs <= .50). "
         "Best group: " + ", ".join(f"{k} in {n}" for k, n in best_share.items()) + ".", "",
         "Largest population attributable risks (percentage points of family poverty above the best group's rate), validated rows:", "",
         "| County | PAR (points) | 90% CI | PAR % |", "| :--- | ---: | :--- | ---: |"]
    pct = cur[cur.measure == "par_pct"].set_index("GEOID").estimate
    L += [f"| {r.GEOID} | {100*r.estimate:.1f} | {100*r.ci_lower:.1f} to {100*r.ci_upper:.1f} | {pct[r.GEOID]:.0f}% |"
          for r in big.itertuples()]
    inc = int((cp.ci_lower > 0).sum()); dec = int((cp.ci_upper < 0).sum())
    L += ["", f"**Change 2015-2019 to 2020-2024 in age-group poverty inequality** (B17001; groups under 18, 18-64, 65+; "
          f"reference the best age group): PAR change validated in {len(cp)} counties (group CVs <= .30 in both releases); "
          f"interval above zero in {inc}, below zero in {dec}, spanning zero in {len(cp) - inc - dec}; median change "
          f"{100*cp.change.median():.2f} points.", "",
          "Mean differences (mdm, mdb) are reported in the output but are exploratory (biased upward when groups are "
          "close; Round 94 validation).", ""]
    (ROOT/"docs/audits/r94_inequality_monitoring_example.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
