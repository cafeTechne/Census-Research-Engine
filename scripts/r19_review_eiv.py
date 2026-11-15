"""Round 19 review check (exploratory): errors-in-variables in the H2 slopes.

pct_bachelors is itself an ACS estimate with sampling error, so the
cross-tract OLS slope of mean income on it is attenuated by the covariate's
reliability, and shifted by the covariance between the two estimates' sampling
errors. If the two periods differ in reliability, the change in slope (H2) is
biased. This script measures both from the run's analysed replicates and
reports the method-of-moments corrected per-period slopes:

    beta = (Cov(x, y) - mean err_cov(x, y)) / (Var(x) - mean err_var(x))

computed within state and period (state demeaning per period, a slight
simplification of the registered model's common state intercepts).

Usage: python scripts/r19_review_eiv.py <run_output_dir> <out.json>
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

REPS = [f"rep_{i}" for i in range(1, 81)]


def main(run_dir: str, out_path: str) -> dict:
    path = Path(run_dir) / "analysed" / "replicates.parquet"
    r = pd.read_parquet(path)
    x = r[r.variable == "pct_bachelors"].set_index(["GEOID", "Year"])
    y = r[r.variable == "mean_hh_income"].set_index(["GEOID", "Year"])
    idx = x.index.intersection(y.index)
    x, y = x.loc[idx], y.loc[idx]
    cols = REPS + ["estimate"]
    ok = x[cols].notna().all(axis=1) & y[cols].notna().all(axis=1)
    x, y = x[ok], y[ok]
    dx = x[REPS].sub(x.estimate, axis=0).to_numpy()
    dy = y[REPS].sub(y.estimate, axis=0).to_numpy()
    d = pd.DataFrame(
        {
            "x": x.estimate,
            "y": y.estimate,
            "err_var_x": 4 / 80 * (dx**2).sum(axis=1),
            "err_cov_xy": 4 / 80 * (dx * dy).sum(axis=1),
        },
        index=x.index,
    ).reset_index()
    d["state"] = d.GEOID.str[:2]

    periods = {}
    for year, g in d.groupby("Year"):
        xc = g.x - g.groupby("state").x.transform("mean")
        yc = g.y - g.groupby("state").y.transform("mean")
        sxx, sxy = float((xc**2).mean()), float((xc * yc).mean())
        ev, ec = float(g.err_var_x.mean()), float(g.err_cov_xy.mean())
        periods[str(year)] = {
            "n": int(len(g)),
            "var_x_within_state": sxx,
            "mean_error_var_x": ev,
            "reliability_x": 1 - ev / sxx,
            "mean_error_cov_xy": ec,
            "slope_naive": sxy / sxx,
            "slope_corrected": (sxy - ec) / (sxx - ev),
        }
    p19, p24 = periods["2019"], periods["2024"]
    result = {
        "label": "exploratory review check, not confirmatory",
        "replicates_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "periods": periods,
        "slope_change_naive": p24["slope_naive"] - p19["slope_naive"],
        "slope_change_corrected": p24["slope_corrected"] - p19["slope_corrected"],
    }
    result["share_of_naive_change_from_measurement_error"] = 1 - (
        result["slope_change_corrected"] / result["slope_change_naive"]
    )
    Path(out_path).write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    res = main(sys.argv[1], sys.argv[2])
    print(json.dumps({k: v for k, v in res.items() if k != "periods"}, indent=2))
    for year, p in res["periods"].items():
        print(year, {k: round(v, 4) if isinstance(v, float) else v for k, v in p.items()})
