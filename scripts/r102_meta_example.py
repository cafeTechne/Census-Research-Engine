# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 102 exploratory example: pooling state-specific county associations of uninsurance with poverty.

Exploratory; author self-review, not independent; not a registered study. ACS 2019-2023 counties in 12 Midwest and
Mid-Atlantic states: within each state, the OLS slope (HC1 SE) of percent uninsured (S2701_C05_001) on percent below
poverty (S1701_C03_001). Pooled with Paule-Mandel + Hartung-Knapp (truncated), the Q-profile tau^2 interval, the
(exploratory) prediction interval for another state, leave-one-out estimates, a meta-regression on state median
household income (B19013, exploratory) and the Egger test (exploratory). Writes docs/audits/r102_meta_example.md.

Usage: scripts/r102_meta_example.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from census.api import CensusAPIClient  # noqa: E402
from census.workflows_inference import combine_estimates  # noqa: E402

STATES = {"26": "MI", "36": "NY", "39": "OH", "42": "PA", "18": "IN", "17": "IL", "55": "WI", "27": "MN", "19": "IA",
          "29": "MO", "21": "KY", "54": "WV"}
C = CensusAPIClient()


def county(st, table, col, dataset):
    d = C.fetch(2023, st, table, geo_level="county", dataset=dataset)
    if d is None:
        raise SystemExit(C.last_error)
    f = pd.DataFrame(d[1:], columns=d[0]).loc[:, lambda x: ~x.columns.duplicated()]
    return pd.to_numeric(f.set_index(f.state+f.county)[col], errors="coerce")


def slope(y, x):
    X = np.column_stack([np.ones(len(x)), x]); b = np.linalg.lstsq(X, y, rcond=None)[0]; e = y-X @ b
    XtXi = np.linalg.inv(X.T @ X); n = len(y)
    V = n/(n-2)*XtXi @ (X.T*(e**2)) @ X @ XtXi
    return float(b[1]), float(np.sqrt(V[1, 1]))


def main():
    est, ses, labels, inc = [], [], [], []
    d = C.fetch(2023, "*", "B19013", geo_level="state", dataset="acs5")
    sinc = {r[d[0].index("state")]: float(r[d[0].index("B19013_001E")]) for r in d[1:]}
    for st, ab in STATES.items():
        f = pd.DataFrame({"u": county(st, "S2701", "S2701_C05_001E", "subject"), "p": county(st, "S1701", "S1701_C03_001E", "subject")}).dropna()
        b, s = slope(f.u.to_numpy(), f.p.to_numpy())
        est.append(b); ses.append(s); labels.append(ab); inc.append(sinc[st]/1000)
    r = combine_estimates("pool", estimates=est, ses=ses, labels=labels, moderators=inc, leave_one_out=True,
                          small_study_test=True)
    if not r["success"]:
        raise SystemExit(r["error"])
    p = r["pooled"]; h = r["heterogeneity"]; m = r["meta_regression"]; e = r["small_study_test"]
    loo = sorted(r["leave_one_out"], key=lambda z: z["estimate"])
    L = ["# Round 102 example: pooling state-specific uninsurance-poverty slopes (exploratory)", "",
         "Author self-review, not independent; not a registered study. ACS 2019-2023 counties; slope of percent uninsured "
         "on percent below poverty within each of 12 states (HC1 SEs).", "",
         "| State | Slope | SE |", "| :--- | ---: | ---: |"] + [f"| {a} | {b:.3f} | {s:.3f} |" for a, b, s in zip(labels, est, ses)]
    L += ["", f"**Pooled** (Paule-Mandel + Hartung-Knapp, truncated): {p['estimate']:.3f} (90% CI {p['lower']:.3f} to "
          f"{p['upper']:.3f}); I2 {h['I2']:.0%}; tau2 {p['tau2']:.4f} with Q-profile interval {h['tau2_interval']['lower']:.4f} "
          f"to {h['tau2_interval']['upper']:.4f} (validated).",
          f"Prediction interval for another state (exploratory): {p['prediction_interval'][0]:.3f} to {p['prediction_interval'][1]:.3f}.",
          f"Leave-one-out pooled estimates ranged {loo[0]['estimate']:.3f} (without {loo[0]['omitted']}) to "
          f"{loo[-1]['estimate']:.3f} (without {loo[-1]['omitted']}).",
          f"Meta-regression on state median household income ($1,000s; exploratory): {m['slope']:.4f} per $1,000 "
          f"({m['lower']:.4f} to {m['upper']:.4f}); permutation p = {m['p_permutation']:.3f}.",
          f"Egger test (exploratory): intercept {e['intercept']:.2f}, p = {e['p']:.2f}. These are not publications, so "
          "asymmetry would reflect state size and heterogeneity, not publication bias.", ""]
    (ROOT/"docs/audits/r102_meta_example.md").write_text("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
