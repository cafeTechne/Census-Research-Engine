# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 22 post hoc check (not pre-registered): heteroskedasticity-robust SEs for the registered m1/m2.

Why: the Round 22 spatial validation (docs/audits/spatial_hac_validation.md) shows that quasi-binomial
(Pearson X2) model SEs covered 0.728 of nominal 90% intervals even with no spatial correlation, when the
overdispersion is extra-binomial between-county variation (the variance then does not shrink with births,
so births-proportional weights are misspecified and X2 scaling does not repair the SE). The registered
study has Pearson dispersion 22. This script refits the registered formulas on the saved analysed frame
and reports HC0 sandwich SEs with the n/(n-k) factor (the Conley estimator's independence limit), plus an
equal-weight quasi-binomial fit, beside the registered SEs. Exploratory, post hoc; the registered
results are not changed.

Usage: .venv/bin/python scripts/r22_posthoc_robust_se.py [studies_output/r22/confirmatory]
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats

ANALYSES = {"m1": ("lbw ~ pov_rate + st", {"H1": "pov_rate"}),
            "m2": ("lbw ~ pov_rate + pct_bachelors + no_vehicle + cost_burden + st",
                   {"H2": "cost_burden", "H3": "no_vehicle"})}
ALPHA = 0.10


def holm(pvals):
    order = sorted(pvals, key=pvals.get)
    out, running = {}, 0.0
    for i, h in enumerate(order):
        running = max(running, min(1.0, (len(order) - i) * pvals[h]))
        out[h] = running
    return out


def main(argv):
    run = Path(argv[1] if len(argv) > 1 else "studies_output/r22/confirmatory")
    d = pd.read_parquet(run / "analysed" / "analysis_frame.parquet")
    d = d.dropna(subset=["lbw", "lbw_denominator", "pov_rate", "pct_bachelors", "no_vehicle", "cost_burden"])
    d = d.assign(st=d["GEOID"].str[:2])
    rows, p_reg, p_rob = [], {}, {}
    for _, (fm, terms) in ANALYSES.items():
        mod = smf.glm(fm, d, family=sm.families.Binomial(), var_weights=d["lbw_denominator"])
        x2, hc = mod.fit(scale="X2"), mod.fit(cov_type="HC0")
        eq = smf.glm(fm, d, family=sm.families.Binomial()).fit(scale="X2")
        n, k = len(d), len(x2.params)
        for h, t in terms.items():
            se_rob = float(hc.bse[t] * np.sqrt(n / (n - k)))
            p_reg[h] = float(stats.norm.sf(x2.params[t] / x2.bse[t]))
            p_rob[h] = float(stats.norm.sf(x2.params[t] / se_rob))
            rows.append({"hypothesis": h, "term": t, "n": n, "estimate": float(x2.params[t]),
                         "se_registered_x2": float(x2.bse[t]), "se_hc0_nk": se_rob,
                         "se_ratio": se_rob / float(x2.bse[t]),
                         "equal_weight_estimate": float(eq.params[t]), "equal_weight_se_x2": float(eq.bse[t])})
    hr, hb = holm(p_reg), holm(p_rob)
    for r in rows:
        h = r["hypothesis"]
        r.update(p_registered=p_reg[h], holm_registered=hr[h], p_robust=p_rob[h], holm_robust=hb[h],
                 supported_robust=bool(hb[h] < ALPHA))
    print(json.dumps({"status": "exploratory (post hoc)", "rows": rows}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
