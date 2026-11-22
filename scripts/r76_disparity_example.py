# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 76 exploratory example: family poverty disparities by race/ethnicity and a Kitagawa decomposition.

Exploratory; author self-review, not independent; no registration. 2020-2024 county VRE files (MI, NY):
- B17010, B17010H, B17010I lines 1-2 (families; families below poverty). Mutually exclusive groups: White alone
  not Hispanic (H), Hispanic or Latino (I) and all other non-Hispanic families (total - H - I, derived on every
  replicate). Reference: White non-Hispanic. (The plan named B17020A-I child poverty; B17020 has no VRE file, so
  the family table with replicates is used.)
- B17001 (poverty by sex by age): Kitagawa decomposition of the person poverty-rate difference, Wayne County
  (26163) minus Oakland County (26125), across eight age strata (<18, 18-24, ..., 65-74, 75+).
Writes docs/audits/r76_disparity_example.md (summary only; no raw tables).

Usage: scripts/r76_disparity_example.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from census.disparity import disparity_measures, kitagawa_decomposition  # noqa: E402
from census.replicate import fetch_vre, REPLICATE_COLUMNS  # noqa: E402

COLS = ["estimate"]+REPLICATE_COLUMNS
BANDS = {"lt18": [0, 1, 2, 3, 4, 5], "a18_24": [6], "a25_34": [7], "a35_44": [8], "a45_54": [9], "a55_64": [10],
         "a65_74": [11], "a75p": [12]}


def lines(table, state, ls):
    f = fetch_vre(table, 2024, "county", state_code=state, lines=ls)
    f["line"] = f["variable"].str[-3:].astype(int)
    return {ln: g.set_index("GEOID")[COLS].astype(float) for ln, g in f.groupby("line")}


def disparity_inputs():
    frames, reps = [], []
    for st in ("26", "36"):
        tot, h, i = (lines(t, st, [1, 2]) for t in ("B17010", "B17010H", "B17010I"))
        geo = tot[1].index
        n = {"wnh": h[1].reindex(geo), "hisp": i[1].reindex(geo)}
        b = {"wnh": h[2].reindex(geo), "hisp": i[2].reindex(geo)}
        n["oth"] = tot[1]-n["wnh"]-n["hisp"]; b["oth"] = tot[2]-b["wnh"]-b["hisp"]
        f = pd.DataFrame(index=geo)
        for g in ("wnh", "hisp", "oth"):
            with np.errstate(divide="ignore", invalid="ignore"):
                rate = b[g]/n[g]
            f[f"r_{g}"] = rate["estimate"]; f[f"n_{g}"] = n[g]["estimate"]
            for name, val in ((f"r_{g}", rate), (f"n_{g}", n[g])):
                reps.append(val.assign(variable=name).reset_index())
        frames.append(f.reset_index())
    frame = pd.concat(frames, ignore_index=True)
    return frame, pd.concat(reps, ignore_index=True)


def kitagawa_inputs():
    reps, rows = [], {}
    below = [4+k for k in range(13)]+[18+k for k in range(13)]
    above = [33+k for k in range(13)]+[47+k for k in range(13)]
    t = lines("B17001", "26", below+above)
    for geo in ("26163", "26125"):
        rows[geo] = {}
    for band, idx in BANDS.items():
        b = sum(t[below[k]]+t[below[13+k]] for k in idx)
        a = sum(t[above[k]]+t[above[13+k]] for k in idx)
        n = a+b; r = b/n
        for name, val in ((f"r_{band}", r), (f"n_{band}", n)):
            v = val.loc[["26163", "26125"]]
            reps.append(v.assign(variable=name).reset_index())
            for geo in rows:
                rows[geo][name] = v.loc[geo, "estimate"]
    frame = pd.DataFrame([{"GEOID": g, **v} for g, v in rows.items()])
    return frame, pd.concat(reps, ignore_index=True)


def main():
    frame, reps = disparity_inputs()
    usable = frame[(frame[["n_wnh", "n_hisp", "n_oth"]] > 0).all(axis=1) & (frame[["r_wnh", "r_hisp", "r_oth"]] > 0).all(axis=1)]
    out = disparity_measures(usable, ["r_wnh", "r_hisp", "r_oth"], "r_wnh", ["n_wnh", "n_hisp", "n_oth"],
                             replicates=reps, omitted_groups=[])
    L = ["# Round 76 example: family poverty disparities by race/ethnicity (MI and NY counties, 2020-2024)", "",
         "Exploratory; author self-review, not independent; no registration. Groups: White alone not Hispanic "
         "(reference), Hispanic or Latino, all other non-Hispanic families (derived on every replicate). Rates: "
         "families below poverty / families (B17010, B17010H, B17010I VRE; B17020 child poverty has no VRE file). "
         f"{len(frame)} counties; {len(usable)} have every group present with a nonzero rate.", "",
         "| Measure | Counties validated | Median estimate | Median 90% CI width |", "| :--- | ---: | ---: | ---: |"]
    for m in ("rd", "log_rr", "idisp", "bgv", "theil", "mld"):
        sub = out[out.measure == m]
        L.append(f"| {m} | {int(sub.validated.sum())} of {len(sub)} rows | {sub.estimate.median():.4g} | "
                 f"{(sub.ci_upper-sub.ci_lower).median():.4g} |")
    L += ["", "Largest counties (90% intervals; ✓ = inside the validated range):", "",
          "| County | Hispanic RR vs White NH | Other NH RR | Index of Disparity | Max group CV |",
          "| :--- | :--- | :--- | :--- | ---: |"]
    for g in ("26163", "26081", "26125", "36047", "36005", "36081", "36055"):
        s = out[out.GEOID == g]
        if s.empty:
            continue
        def fmt(row, exp=False):  # noqa: E306
            f = np.exp if exp else (lambda x: x)
            return f"{f(row.estimate):.2f} ({f(row.ci_lower):.2f}–{f(row.ci_upper):.2f}){' ✓' if row.validated else ''}"
        rr = s[s.measure == "log_rr"].set_index("group")
        idp = s[s.measure == "idisp"].iloc[0]
        L.append(f"| {g} | {fmt(rr.loc['r_hisp'], True)} | {fmt(rr.loc['r_oth'], True)} | {fmt(idp)} | "
                 f"{idp.max_group_cv:.2f} |")
    kf, kr = kitagawa_inputs()
    strata = list(BANDS)
    k = kitagawa_decomposition(kf, "26163", "26125", [f"r_{b}" for b in strata], [f"n_{b}" for b in strata],
                               replicates=kr)
    L += ["", "## Kitagawa: person poverty rate, Wayne (26163) minus Oakland (26125), eight age strata (B17001)", "",
          "| Component | Estimate (percentage points) | 90% CI | Validated |", "| :--- | ---: | :--- | :--- |"]
    for _, row in k.iterrows():
        L.append(f"| {row.component} | {100*row.estimate:.2f} | {100*row.ci_lower:.2f} to {100*row.ci_upper:.2f} | "
                 f"{'yes' if row.validated else 'no'} |")
    L += ["", f"Largest stratum-rate CV: {k.max_stratum_cv.iloc[0]:.3f}.", ""]
    (ROOT/"docs/audits/r76_disparity_example.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
