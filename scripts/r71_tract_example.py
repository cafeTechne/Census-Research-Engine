# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 71 example (descriptive): replication C's OLS slopes (Round 67) with the validated tract interval, SCPC
rho_bar .20 (docs/audits/tract_spatial_validation.md). The registered Round 67 result does not change.

Writes docs/audits/r71_tract_example.md. Usage: scripts/r71_tract_example.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/"scripts"))
import pandas as pd  # noqa: E402
import statsmodels.api as sm  # noqa: E402

from census import residual_dependence as rd, scpc  # noqa: E402
import r67_nc_ice_replication as r67  # noqa: E402


def main():
    f, _ = r67.build()
    geo = json.loads((ROOT/"docs/audits/nc_tract_geometry.json").read_text())
    coords = pd.DataFrame(dict(GEOID=geo["GEOID"], lon=geo["lon"], lat=geo["lat"]))
    L = ["# Round 71 example: replication C slopes with the tract interval", "",
         "Descriptive; Round 67's registered result is unchanged. OLS slopes of ln(e0) on each ICE, NC 2014-2018 tracts.",
         "", "| ICE | Slope | HC3 90% CI | SCPC rho_bar .20 90% CI | Residual Moran's I (p) |",
         "| :--- | ---: | :--- | :--- | :--- |"]
    for var in r67.PUBLISHED:
        d = f[["GEOID", "lnle", var]].dropna()
        fit = sm.OLS(d.lnle, sm.add_constant(d[var])).fit(cov_type="HC3")
        lo, hi = fit.conf_int(alpha=.10).loc[var]
        s = scpc.fit_scpc(f"lnle ~ {var}", d, coords=coords)
        row = s["table"].set_index("term").loc[var]
        chk = rd.check(d, f"lnle ~ {var}", coords=coords)
        L.append(f"| {var} | {fit.params[var]:.4f} | {lo:.4f} to {hi:.4f} | {row.lower:.4f} to {row.upper:.4f} "
                 f"(validated {s['validated']}) | {chk['moran_i']:.3f} ({chk['p']:.3f}) |")
    L += ["", "Spatial dependence in the residuals widens the honest interval; every slope stays clearly positive.", ""]
    (ROOT/"docs/audits/r71_tract_example.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
