# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 95 exploratory example: national YPLL-75 by cause and aberration flags for state uninsured rates.

Exploratory; author self-review, not independent; not a registered study.
(a) Age-adjusted YPLL-75 by underlying cause, US, 2013-2017 and 2018-2022, from the owner's national WONDER manual
    exports (external_data/wonder/ucd/*/national_age_sex; national counts only).
(b) Historical-limits flags for 2023 state uninsured rates (ACS 1-year S2701, the Round 78 panel) against the five
    previous observed years (2017-2022 without 2020), with a CDC-style deviation chart.
Writes docs/audits/r95_surveillance_example.md and docs/audits/r95_deviation_chart.png.

Usage: scripts/r95_surveillance_example.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/"scripts"))
import numpy as np  # noqa: E402

from census.surveillance import aberration, deviation_chart, ypll_from_wonder  # noqa: E402
from r78_medicaid_example import panel  # noqa: E402

CAUSES = ["all_causes", "heart_disease", "cancer", "unintentional_injury", "drug_overdose", "suicide", "firearm",
          "liver_disease", "diabetes", "stroke", "clrd", "kidney_disease", "alcohol_induced"]
W = ROOT/"external_data/wonder/ucd"


def main():
    L = ["# Round 95 example: national YPLL-75 by cause and state uninsured aberration flags (exploratory)", "",
         "Author self-review, not independent; not a registered study.", "",
         "## Age-adjusted YPLL-75 per 100,000 person-years, United States", "",
         "National WONDER manual exports (Underlying Cause of Death), ten-year age groups below 75, 2000 US standard; "
         "90% Fay-Feuer intervals (validated).", "",
         "| Cause | 2013-2017 | 2018-2022 | Change |", "| :--- | ---: | ---: | ---: |"]
    for c in CAUSES:
        a, b = ypll_from_wonder(str(W/"2013-2017/national_age_sex"/f"{c}.tsv")), ypll_from_wonder(str(W/"2018-2022/national_age_sex"/f"{c}.tsv"))
        cell = lambda x: (f"{x['adjusted_rate']:,.0f} ({x['lower']:,.0f}-{x['upper']:,.0f})" if "adjusted_rate" in x
                          else f"bounds {x['adjusted_rate_lower']:,.1f}-{x['adjusted_rate_upper']:,.1f}*")  # noqa: E731
        mid = lambda x: x.get("adjusted_rate", (x.get("adjusted_rate_lower", 0)+x.get("adjusted_rate_upper", 0))/2)  # noqa: E731
        L.append(f"| {c.replace('_', ' ')} | {cell(a)} | {cell(b)} | {100*(mid(b)/mid(a)-1):+.0f}% |")
    L += ["", "\\* Some national age-by-sex cells are suppressed (1-9 deaths): bounds with each suppressed cell at 1 and "
          "at 9; the change uses the bound midpoints."]
    f = panel()
    f = f[f.Year >= 2017]
    names, ratios, lows, highs, flags = [], [], [], [], []
    for g, d in f.sort_values("Year").groupby("GEOID"):
        r = aberration(d.Year.tolist(), d.uninsured.tolist(), d.se.tolist())
        names.append(g); ratios.append(r["ratio"]); lows.append(r["lower_limit"]/r["baseline_mean"])
        highs.append(r["upper_limit"]/r["baseline_mean"]); flags.append(r["flag"])
    flags = np.array(flags)
    order = np.argsort(ratios)
    chart = deviation_chart([names[i] for i in order], [ratios[i] for i in order], [lows[i] for i in order],
                            [highs[i] for i in order], str(ROOT/"docs/audits/r95_deviation_chart.png"),
                            "2023 state uninsured rate vs 2017-2022 (ACS 1-year)")
    L += ["", "## Historical-limits flags, 2023 state uninsured rates", "",
          f"ACS 1-year percent uninsured, 50 states and DC; baseline 2017, 2018, 2019, 2021, 2022 (2020 has no "
          f"standard release). Flags: high {int((flags == 'high').sum())}, low {int((flags == 'low').sum())}, none "
          f"{int((flags == 'none').sum())}. Rates fell broadly through 2022 (a trend), so 'low' flags partly reflect the "
          "trend, which the method does not model. Chart: `docs/audits/r95_deviation_chart.png` (FIPS codes).", ""]
    (ROOT/"docs/audits/r95_surveillance_example.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
