# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 84 exploratory example: county disability prevalence and poverty (MI and NY, 2019-2023 ACS).

Exploratory; author self-review, not independent. Outcome: share with a disability (S1810_C03_001 / 100, trials
S1810_C01_001, ACS's own measure per the circularity rule); exposure: percent below poverty (S1701_C03_001).
Binomial (quasi) model with a NY indicator; marginal RR and RD for poverty at its 80th vs 20th percentile, the
attributable fraction for every county at the 20th percentile, and a dose-response test over poverty quintiles.
Ecologic and cross-sectional: describes counties, not people. Writes docs/audits/r84_marginal_example.md.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from census.api import CensusAPIClient  # noqa: E402
from census.epi_measures import area_marginal_measures  # noqa: E402


def main():
    c = CensusAPIClient(); rows = []
    for st in ("26", "36"):
        d = c.fetch(2023, st, "S1810", geo_level="county", dataset="subject"); a = pd.DataFrame(d[1:], columns=d[0]).loc[:, lambda x: ~x.columns.duplicated()]
        d = c.fetch(2023, st, "S1701", geo_level="county", dataset="subject"); b = pd.DataFrame(d[1:], columns=d[0]).loc[:, lambda x: ~x.columns.duplicated()]
        f = pd.DataFrame({"GEOID": a.state+a.county, "dis": pd.to_numeric(a["S1810_C03_001E"])/100,
                          "trials": pd.to_numeric(a["S1810_C01_001E"])}).merge(
            pd.DataFrame({"GEOID": b.state+b.county, "poverty": pd.to_numeric(b["S1701_C03_001E"])}), on="GEOID")
        rows.append(f.assign(NY=float(st == "36")))
    f = pd.concat(rows, ignore_index=True)
    q20, q80 = np.quantile(f.poverty, [.2, .8])
    r = area_marginal_measures(f, "dis ~ poverty + NY", "trials", "poverty", [q20, q80], dose_levels=5)
    dr = r["dose_response"]
    L = ["# Round 84 example: county disability prevalence and poverty (MI and NY, 2019-2023 ACS)", "",
         "Exploratory; author self-review, not independent. Ecologic and cross-sectional: describes counties, not people.", "",
         f"{len(f)} counties; overall disability prevalence {r['prevalence']:.1%}. Poverty 20th percentile {q20:.1f}%, "
         f"80th {q80:.1f}%.", "",
         "| Measure | Estimate | 90% CI |", "| :--- | ---: | :--- |",
         f"| Marginal risk at poverty {q20:.1f}% | {r['risk_low']:.2%} | |",
         f"| Marginal risk at poverty {q80:.1f}% | {r['risk_high']:.2%} | |",
         f"| Risk ratio (80th vs 20th) | {r['rr']:.3f} | {r['rr_lower']:.3f} to {r['rr_upper']:.3f} |",
         f"| Risk difference (points) | {100*r['rd']:.2f} | {100*r['rd_lower']:.2f} to {100*r['rd_upper']:.2f} |",
         f"| Attributable fraction (all counties at the 20th percentile) | {r['paf']:.3f} | {r['paf_lower']:.3f} to {r['paf_upper']:.3f} |",
         "", f"Dose-response over poverty quintiles: marginal risks {', '.join(f'{x:.2%}' for x in dr['risks'])}; "
         f"linear trend p = {dr['trend_p']:.3g}; departure from linearity p = {dr.get('nonlinearity_p', float('nan')):.3g}.",
         "", "The prevalence of disability among counties at the 80th poverty percentile was "
         f"{r['rr']:.2f} times as high as among counties at the 20th percentile (an association between areas).", ""]
    (ROOT/"docs/audits/r84_marginal_example.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
