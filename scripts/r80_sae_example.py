# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 80 exploratory example: small-area uninsured rates in Michigan.

Exploratory; author self-review, not independent. S2701 percent uninsured (C05_001 2019-2023; C03_001 2014-2018,
checked by range) with S1701 percent below poverty as the covariate.
- Arcsine Fay-Herriot (P1) on MI tracts, 2019-2023 (n_eff from the published estimate and MOE; only tracts with
  0 < p < 100, since n_eff is undefined at 0 or 100 without a sample-size column).
- Rao-Yu temporal FH (T1) on MI counties over 2014-2018 and 2019-2023 (tract IDs changed between these releases).
Writes docs/audits/r80_sae_example.md (summary only).

Usage: scripts/r80_sae_example.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from census.api import CensusAPIClient  # noqa: E402
from census.sae_extensions import arcsine_small_area, temporal_small_area  # noqa: E402

C = CensusAPIClient()


def get(year, table, level, cols):
    d = C.fetch(year, "26", table, geo_level=level, dataset="subject")
    if d is None:
        raise SystemExit(f"{table} {year} {level}: {C.last_error}")
    f = pd.DataFrame(d[1:], columns=d[0]).loc[:, lambda x: ~x.columns.duplicated()]
    f["GEOID"] = f.state+f.county+(f.tract if level == "tract" else "")
    return f.set_index("GEOID")[cols].apply(pd.to_numeric, errors="coerce")


def frame(year, level):
    col = "S2701_C05_001" if year >= 2017 else "S2701_C03_001"
    u = get(year, "S2701", level, [col+"E", col+"M"]); p = get(year, "S1701", level, ["S1701_C03_001E"])
    f = u.join(p, how="inner")
    out = pd.DataFrame({"unins": f[col+"E"], "unins_se": f[col+"M"]/1.645, "pov": f["S1701_C03_001E"]}).dropna()
    assert out.unins.median() < 25, "percent-uninsured column check"
    return out.reset_index().assign(Year=year)


def main():
    t = frame(2023, "tract")
    t = t[(t.unins > 0) & (t.unins < 100) & (t.unins_se > 0)]
    a = arcsine_small_area(t, "unins ~ pov", "unins_se", percent=True)
    w_dir = (2*1.645*t.unins_se).median(); w_fh = (a.ci_upper-a.ci_lower).median()
    c = pd.concat([frame(2018, "county"), frame(2023, "county")])
    c = c[c.GEOID.isin(set(c.GEOID[c.Year == 2018]) & set(c.GEOID[c.Year == 2023]))]
    r = temporal_small_area(c, "unins ~ pov", "unins_se", release_column="Year")
    L = ["# Round 80 example: small-area uninsured rates in Michigan (exploratory)", "",
         "Author self-review, not independent. S2701 percent uninsured; covariate S1701 percent below poverty.", "",
         f"**Arcsine Fay-Herriot, {len(a)} MI tracts (2019-2023; tracts with a published 0% or 100% omitted):** median "
         f"90% interval width {w_fh:.2f} points against {w_dir:.2f} for the direct estimates; model variance "
         f"{a.attrs['sigma2_u']:.4g} (arcsine scale); median |estimate - direct| "
         f"{(a.estimate-a.direct).abs().median():.2f} points; {'validated' if a.attrs['validated'] else 'exploratory'}.", "",
         f"**Rao-Yu temporal FH, {r.GEOID.nunique()} MI counties (2014-2018 and 2019-2023; latest release):** median "
         f"interval width {(r.ci_upper-r.ci_lower).median():.2f} points against {(2*1.645*c[c.Year == 2023].unins_se).median():.2f} "
         f"direct; rho {r.attrs['rho']:.2f}, area variance {r.attrs['sigma2_v']:.3g}, area-time variance "
         f"{r.attrs['sigma2_u']:.3g}. Counties have precise direct estimates, so the gain is small; the validation "
         "found the largest gains on tracts (10-24% MSE).", "",
         "| Tract estimate quantile | Direct % | Arcsine FH % |", "| :--- | ---: | ---: |"]
    for q in (.1, .5, .9):
        L.append(f"| {q:.0%} | {t.unins.quantile(q):.1f} | {a.estimate.quantile(q):.1f} |")
    L.append("")
    (ROOT/"docs/audits/r80_sae_example.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
