# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 55 demonstration (simulated inputs; not a data example, not a study).

No suitable real series or ACS-estimated reference population is available offline (see the Round 55 plan), so
this shows the engine output on one simulated 22-point annual series (AR(1) errors, phi .5, level change 1,
slope change .2, interruption at point 12) for every interrupted-series method, and one simulated SMR with and
without the reference-population SE. Fixed seed; writes a CSV and a summary.

Usage: scripts/r55_demonstration.py OUT_DIR
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from census import mci_core as mi  # noqa: E402
from census.missing_censored_its import interrupted_series  # noqa: E402
from census.standardize import indirect_standardize  # noqa: E402


def main(out_dir):
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=False)
    rng = np.random.default_rng(20280155)
    n, phi = 22, .5
    e = rng.standard_normal(n); u = np.empty(n); u[0] = e[0]/np.sqrt(1-phi**2)
    for t in range(1, n):
        u[t] = phi*u[t-1]+e[t]
    y = mi.its_design(n, 12) @ np.array([10., .1, 1., .2])+u
    rows = []
    for method in ("bootstrap_t_bc", "bootstrap_t", "reml", "ewc", "ar1"):
        r = interrupted_series(y, 11, method=method)
        for name in ("level_change", "slope_change"):
            c = r[name]
            rows.append(dict(method=method, quantity=name, estimate=c["estimate"], lower=c["lower"], upper=c["upper"],
                             validated=r["validated"]))
    its = pd.DataFrame(rows); its.to_csv(out_dir/"interrupted_series.csv", index=False)
    print(its.round(3).to_string(index=False))
    rates = np.array([.0005, .001, .003, .01, .04]); D = np.array([40, 60, 150, 300, 600])
    P = D/rates
    obs = pd.Series([150], index=["demo"]); pop = pd.DataFrame([[20000, 15000, 12000, 6000, 2500.]], index=obs.index)
    a = indirect_standardize(obs, pop, rates, None, reference_counts=D).iloc[0]
    b = indirect_standardize(obs, pop, rates, None, reference_counts=D, reference_population_se=.05*P).iloc[0]
    smr = pd.DataFrame([dict(reference="person-years fixed", smr=a.smr, lower=a.smr_lower, upper=a.smr_upper),
                        dict(reference="person-years CV .05", smr=b.smr, lower=b.smr_lower, upper=b.smr_upper)])
    smr.to_csv(out_dir/"smr.csv", index=False)
    print(smr.round(4).to_string(index=False))
    (out_dir/"summary.json").write_text(json.dumps(dict(series_points=n, true_level_change=1., true_slope_change=.2,
                                                        smr_interval_widening=float((b.smr_upper-b.smr_lower)/(a.smr_upper-a.smr_lower)))
                                                   , indent=1)+"\n")


if __name__ == "__main__":
    main(sys.argv[1])
