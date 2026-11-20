# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 63 demonstration (simulated input; not a data example, not a study).

One simulated 17-point annual series (AR(1) errors, phi .5, level change 1, slope change .2, interruption at point 9)
with every interrupted-series method, showing which are validated at 17 points. Fixed seed.

Usage: scripts/r63_demonstration.py OUT_DIR
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


def main(out_dir):
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=False)
    rng = np.random.default_rng(20280863)
    n, phi = 17, .5
    e = rng.standard_normal(n); u = np.empty(n); u[0] = e[0]/np.sqrt(1-phi**2)
    for t in range(1, n):
        u[t] = phi*u[t-1]+e[t]
    y = mi.its_design(n, 9) @ np.array([10., .1, 1., .2])+u
    rows = []
    for method in ("bootstrap_t_cons", "bootstrap_t_bb", "bootstrap_t_bc", "reml"):
        r = interrupted_series(y, 8, method=method)
        for name in ("level_change", "slope_change"):
            c = r[name]
            rows.append(dict(method=method, quantity=name, estimate=c["estimate"], lower=c["lower"], upper=c["upper"],
                             validated=r["validated"]))
    out = pd.DataFrame(rows); out.to_csv(out_dir/"interrupted_series.csv", index=False)
    print(out.round(3).to_string(index=False))
    (out_dir/"summary.json").write_text(json.dumps(dict(points=n, true_level_change=1., true_slope_change=.2), indent=1)+"\n")


if __name__ == "__main__":
    main(sys.argv[1])
