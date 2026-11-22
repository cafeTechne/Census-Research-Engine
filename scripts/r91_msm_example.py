# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 91 exploratory example: Medicaid expansion and the state uninsured rate with time-varying unemployment.

Exploratory; author self-review, not independent; not a registered study. Panel from Round 78
(scripts/r78_medicaid_example.py: ACS 1-year S2701 percent uninsured, 50 states and DC, 2010-2023 without 2020, KFF
expansion years). Time-varying confounder: the state unemployment rate (ACS 1-year DP03_0009PE, checked by range),
which can respond to expansion and affect later adoption. Time zero 2010 (no state expanded before 2014).
IP-weighted marginal structural model (stabilized and truncated weights) beside ordinary regression on current
unemployment. Writes docs/audits/r91_msm_example.md.

Usage: scripts/r91_msm_example.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/"scripts"))
import pandas as pd  # noqa: E402

from census.api import CensusAPIClient  # noqa: E402
from census.msm import VALIDATED, marginal_structural_model  # noqa: E402
from r78_medicaid_example import YEARS, panel  # noqa: E402


def unemployment():
    c = CensusAPIClient(); rows = []
    for y in YEARS:
        d = c.fetch(y, "*", "DP03", geo_level="state", dataset="acs1/profile")
        if d is None:
            raise SystemExit(f"DP03 {y}: {c.last_error}")
        h = d[0]
        rows += [dict(GEOID=r[h.index("state")], Year=y, unemp=float(r[h.index("DP03_0009PE")])) for r in d[1:]
                 if r[h.index("state")] != "72"]
    u = pd.DataFrame(rows)
    assert u.unemp.between(1.5, 20).all(), "DP03_0009PE is not the unemployment rate in some year"
    return u


def main():
    f = panel().merge(unemployment(), on=["GEOID", "Year"])
    res = {k: marginal_structural_model(f, "uninsured", "first_treated", ["unemp"], truncate=t)
           for k, t in (("stabilized", False), ("truncated", True))}
    r = res["stabilized"]
    L = ["# Round 91 example: Medicaid expansion, uninsured rate and time-varying unemployment (exploratory)", "",
         "Author self-review, not independent; not a registered study. ACS 1-year, 50 states and DC, 2010-2023 without "
         f"2020 ({r['units']} units, {r['treated_units']} expanded within the panel). Outcome: percent uninsured "
         "(S2701); time-varying confounder: unemployment rate (DP03). Time zero 2010; strategy 'expand and stay "
         "expanded'. Effects are percentage points for the first, second and third expanded year versus never "
         "expanded.", "",
         "| Year of expansion | MSM, stabilized weights (90% CI) | MSM, truncated weights (90% CI) | Regression on current unemployment |",
         "| ---: | :--- | :--- | ---: |"]
    for i in range(3):
        a, b, n = res["stabilized"]["effects"][i], res["truncated"]["effects"][i], r["naive_adjusted"][i]
        L.append(f"| {a['duration']} | {a['estimate']:.2f} ({a['lower']:.2f} to {a['upper']:.2f}) | "
                 f"{b['estimate']:.2f} ({b['lower']:.2f} to {b['upper']:.2f}) | {n['estimate']:.2f} |")
    L += ["", f"Largest stabilized weight {r['max_weight']:.2f}. Validation status: stabilized "
          f"{'validated' if VALIDATED['stabilized'] else 'exploratory'}, truncated "
          f"{'validated' if VALIDATED['truncated'] else 'exploratory'} (`docs/audits/msm_validation.md`). "
          "Unemployment is the only time-varying confounder modelled; the no-unmeasured-confounding assumption is "
          "strong for state policy. The Round 78 staggered DiD on the same panel adjusted for nothing time-varying.", ""]
    (ROOT/"docs/audits/r91_msm_example.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
