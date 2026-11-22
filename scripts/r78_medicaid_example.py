# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 78 exploratory example: ACA Medicaid expansion and the state uninsured rate (staggered DiD).

Exploratory; author self-review, not independent; no registration and not a replication. ACS 1-year S2701 percent
uninsured (all ages; S2701_C03_001 through 2014, S2701_C05_001 from 2015; checked: 2015-2016 C03 is percent insured) for the 50 states and DC, 2010-2023
without 2020 (no standard 1-year release); SE = MOE / 1.645. First treated year = the first calendar year with
expansion in effect for most of the year (KFF expansion dates; 2020 adopters ID and UT map to 2021; adopters after
2023 (SD, NC) are never treated within the panel). Sun-Abraham (default) and Callaway-Sant'Anna with the ACS
variance. The published literature finds reductions of roughly 3-5 points (e.g. Courtemanche et al. 2017); this is
a descriptive comparison only.
Writes docs/audits/r78_medicaid_example.md.

Usage: scripts/r78_medicaid_example.py   (uses the API cache; needs the Census API key for uncached years)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from census.api import CensusAPIClient  # noqa: E402
from census.staggered import staggered_did  # noqa: E402

FIRST = {"04": 2014, "05": 2014, "06": 2014, "08": 2014, "09": 2014, "10": 2014, "11": 2014, "15": 2014, "17": 2014,
         "19": 2014, "21": 2014, "24": 2014, "25": 2014, "26": 2014, "27": 2014, "32": 2014, "34": 2014, "35": 2014,
         "36": 2014, "38": 2014, "39": 2014, "41": 2014, "44": 2014, "50": 2014, "53": 2014, "54": 2014,
         "33": 2015, "42": 2015, "18": 2015, "02": 2016, "30": 2016, "22": 2017, "51": 2019, "23": 2019,
         "16": 2020, "49": 2020, "31": 2021, "40": 2022, "29": 2022}
YEARS = [y for y in range(2010, 2024) if y != 2020]


def panel():
    c = CensusAPIClient(); rows = []
    for y in YEARS:
        d = c.fetch(y, "*", "S2701", geo_level="state", dataset="acs1/subject")
        if d is None:
            raise SystemExit(f"S2701 {y}: {c.last_error}")
        h = d[0]; col = "S2701_C03_001" if y <= 2014 else "S2701_C05_001"
        for r in d[1:]:
            st = r[h.index("state")]
            if st == "72":
                continue
            rows.append(dict(GEOID=st, Year=y, uninsured=float(r[h.index(col+"E")]),
                             se=float(r[h.index(col+"M")])/1.645, first_treated=FIRST.get(st, np.nan)))
    return pd.DataFrame(rows)


def main():
    f = panel()
    assert f.uninsured.between(1, 30).all(), "unexpected uninsured percentages"
    sa = staggered_did(f, "uninsured", "first_treated", se=None)
    cs = staggered_did(f, "uninsured", "first_treated", se="se", method="callaway_santanna")
    L = ["# Round 78 example: Medicaid expansion and the state uninsured rate (ACS 1-year, 2010-2023 without 2020)", "",
         "Exploratory; author self-review, not independent; not a registered replication. Percent uninsured (S2701), "
         f"{sa['units']} units, cohorts {sa['cohorts']}, {sa['never_treated']} never treated within the panel. "
         "Event times count observed periods (2020 is skipped).", "",
         "| Method | Overall ATT (points) | 90% CI | Validated |", "| :--- | ---: | :--- | :--- |"]
    for name, r in (("Sun-Abraham", sa), ("Callaway-Sant'Anna + ACS variance", cs)):
        o = r["overall"]
        L.append(f"| {name} | {o['estimate']:.2f} | {o['ci_lower']:.2f} to {o['ci_upper']:.2f} | {'yes' if r['validated'] else 'no'} |")
    L += ["", "Sun-Abraham event study (event time 0 = first treated year):", "",
          "| Event time | Estimate | 90% CI |", "| ---: | ---: | :--- |"]
    for _, r in sa["event_study"].iterrows():
        if -5 <= r.event_time <= 6:
            L.append(f"| {int(r.event_time)} | {r.estimate:.2f} | {r.ci_lower:.2f} to {r.ci_upper:.2f} |")
    L += ["", f"Pre-trend check (smallest Holm-adjusted p over pre-treatment event times): {sa['pretrend_min_holm_p']:.3f}.",
          "The literature's 3-5 point reductions concern low-income adults; this all-ages rate dilutes them (most "
          "residents were not in the expansion population), so a smaller all-ages effect is expected. Descriptive "
          "comparison only.", ""]
    (ROOT/"docs/audits/r78_medicaid_example.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
