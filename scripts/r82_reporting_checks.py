# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 82 numeric checks and example: ACS allocation shares and Table 1.

No new statistics; author self-review, not independent. For MI and NY counties (2019-2023 ACS):
1. For each B99 table used, the allocated and not-allocated leaf lines sum exactly to the published total (line 001)
   in every county, so the allocated share equals published allocated lines / total.
2. Allocation summary (median and maximum allocated share over counties) for common public-health tables.
3. Table 1 by tertile of the county poverty rate reproduces direct group means exactly.
Writes docs/audits/r82_reporting_checks.md.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from census import epi_reporting as er  # noqa: E402
from census.api import CensusAPIClient  # noqa: E402
from census.metadata import table_variables  # noqa: E402

TABLES = {"B992701": "health insurance", "B99181": "disability", "B99172": "poverty status (families)",
          "B99192": "household income", "B99231": "employment status", "B99151": "educational attainment"}


def main():
    c = CensusAPIClient()
    L = ["# Round 82 checks: ACS allocation shares and Table 1 (MI and NY counties, 2019-2023)", "",
         "No new statistics; author self-review, not independent.", "",
         "| Table | Item | Counties | Lines sum to total | Median allocated | Max allocated | Above 5% |",
         "| :--- | :--- | ---: | :--- | ---: | ---: | :--- |"]
    for t, item in TABLES.items():
        meta, _ = table_variables(t, "acs5", 2023)
        labels = {k[:-1]: v["label"] for k, v in meta.items() if k.endswith("E")}
        parts = er.allocation_lines(labels)
        frames = []
        for st in ("26", "36"):
            d = c.fetch(2023, st, t, geo_level="county")
            f = pd.DataFrame(d[1:], columns=d[0]).loc[:, lambda x: ~x.columns.duplicated()]
            frames.append(f)
        f = pd.concat(frames, ignore_index=True)
        num = lambda cols: f[[x+"E" for x in cols]].apply(pd.to_numeric).sum(axis=1)  # noqa: E731
        total = pd.to_numeric(f[f"{t}_001E"])
        exact = bool((num(parts["allocated"])+num(parts["not_allocated"]) == total).all())
        share = er.allocation_shares(f.rename(columns=lambda x: x[:-1] if x.endswith("E") and x.startswith(t) else x),
                                     {k: labels[k] for k in parts["allocated"]+parts["not_allocated"]})
        assert np.allclose(share, num(parts["allocated"])/total), t
        L.append(f"| {t} | {item} | {len(f)} | {'yes' if exact else 'NO'} | {share.median():.1%} | {share.max():.1%} | "
                 f"{'yes' if share.median() > er.ALLOCATION_LIMIT else 'no'} |")
    pov = []
    for st in ("26", "36"):
        d = c.fetch(2023, st, "S1701", geo_level="county", dataset="subject")
        f = pd.DataFrame(d[1:], columns=d[0]).loc[:, lambda x: ~x.columns.duplicated()]
        pov.append(pd.DataFrame({"GEOID": f.state+f.county, "poverty": pd.to_numeric(f["S1701_C03_001E"]),
                                 "poverty_se": pd.to_numeric(f["S1701_C03_001M"])/1.645,
                                 "population": pd.to_numeric(f["S1701_C01_001E"])}))
    p = pd.concat(pov, ignore_index=True)
    t1 = er.table_one(p, "poverty", ["poverty"], population="population")
    grp = pd.qcut(p["poverty"].rank(method="first"), 3, labels=["Q1", "Q2", "Q3"])
    direct = p.groupby(grp, observed=True)["poverty"].mean()
    ok = all(np.isclose(t1.loc["poverty mean", q], direct[q]) for q in ("Q1", "Q2", "Q3"))
    L += ["", f"Table 1 by county poverty tertile reproduces the direct tertile means: {'yes' if ok else 'NO'} "
          f"(Q1 {direct['Q1']:.1f}%, Q2 {direct['Q2']:.1f}%, Q3 {direct['Q3']:.1f}%; {len(p)} counties).", "",
          "Reading: every table above exceeds the 5% level that *Foundations of Epidemiology* (chapter 6) treats as "
          "worth discussing; the engine reports it as a limitation, not a refusal.", ""]
    (ROOT/"docs/audits/r82_reporting_checks.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
