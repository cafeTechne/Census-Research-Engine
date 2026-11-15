# SPDX-License-Identifier: AGPL-3.0-or-later
"""Simulation validation of census.models.fit_eiv (PLAN_ROUND_20 A2).

Design: n units; true covariate x ~ N(10, 3^2) and a binary factor g; outcome
y = 1 + 2 x + 0.5 g + N(0, 2^2). The published estimates carry heteroscedastic
sampling errors, x_obs = x + u and y_obs = y + v, with corr(u, v) = rho (both
estimated from the same survey sample). The mean error variance of x gives the
covariate reliability. Synthetic replicates scatter around the estimates,
x^(r) = x_obs + sqrt(s_x^2 / 4) z_r (and likewise y, with the same rho), so the
VRE formula 4/80 sum_r (x^(r) - x_obs)^2 estimates s_x^2 without bias.

Compared for the x coefficient (true value 2): naive OLS, regression
calibration (census.models.regression_calibration, which knows s_x but not
rho) and fit_eiv. Acceptance (PLAN_ROUND_20 A2): fit_eiv |bias| < 10% of the
naive bias, and 90% interval coverage of 0.87-0.93 at reliability >= 0.8.

Usage: python scripts/eiv_validation.py [--sims 500] [--n 800] [--workers 9] [--out docs/audits/eiv_validation.md]
"""

import argparse
import os
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from census.models import fit_eiv, regression_calibration  # noqa: E402
from census.variance import REPLICATE_COLUMNS  # noqa: E402

BETA = 2.0
RELIABILITIES = (0.95, 0.8, 0.6)
RHOS = (0.0, 0.5, -0.5)


def simulate(seed: int, n: int, rel: float, rho: float):
    rng = np.random.default_rng(seed)
    x = rng.normal(10, 3, n)
    g = rng.integers(0, 2, n)
    s2x = rng.uniform(0.2, 1.8, n) * 9 * (1 - rel) / rel
    s2y = rng.uniform(0.5, 1.5, n) * 4
    z1 = rng.standard_normal(n)
    z2 = rho * z1 + np.sqrt(1 - rho**2) * rng.standard_normal(n)
    xo = x + np.sqrt(s2x) * z1
    yo = 1 + BETA * x + 0.5 * g + rng.normal(0, 2, n) + np.sqrt(s2y) * z2
    Z1 = rng.standard_normal((n, 80))
    Z2 = rho * Z1 + np.sqrt(1 - rho**2) * rng.standard_normal((n, 80))
    xr = xo[:, None] + np.sqrt(s2x / 4)[:, None] * Z1
    yr = yo[:, None] + np.sqrt(s2y / 4)[:, None] * Z2
    geo = [f"{i:011d}" for i in range(n)]
    frame = pd.DataFrame({"GEOID": geo, "x": xo, "x_se": np.sqrt(s2x), "y": yo, "y_se": np.sqrt(s2y),
                          "g": g.astype(str)})
    reps = pd.concat([
        pd.DataFrame({"GEOID": geo, "variable": "x", "estimate": xo, **dict(zip(REPLICATE_COLUMNS, xr.T))}),
        pd.DataFrame({"GEOID": geo, "variable": "y", "estimate": yo, **dict(zip(REPLICATE_COLUMNS, yr.T))}),
    ], ignore_index=True)
    return frame, reps


def run_cell(cell):
    rel, rho, sims, n = cell
    warnings.simplefilter("ignore")
    rec = {k: [] for k in ("eiv", "eiv_cov", "eiv_se", "naive", "rc", "rc_cov")}
    for s in range(sims):
        frame, reps = simulate(1000 * s + 7, n, rel, rho)
        c = fit_eiv("y ~ x + C(g)", frame, reps).coefficients.set_index("term").loc["x"]
        rec["eiv"].append(c["estimate"])
        rec["eiv_se"].append(c["se_total"])
        rec["eiv_cov"].append(c["ci_lower"] <= BETA <= c["ci_upper"])
        rec["naive"].append(c["naive_estimate"])
        rcx = regression_calibration("y ~ x + C(g)", frame, ["x"], n_boot=100, seed=s) \
            .coefficients.set_index("term").loc["x"]
        rec["rc"].append(rcx["estimate"])
        rec["rc_cov"].append(rcx["ci_lower"] <= BETA <= rcx["ci_upper"])
    eiv_bias = float(np.mean(rec["eiv"]) - BETA)
    naive_bias = float(np.mean(rec["naive"]) - BETA)
    return {
        "reliability": rel, "rho": rho, "sims": sims,
        "naive_bias": naive_bias, "rc_bias": float(np.mean(rec["rc"]) - BETA),
        "eiv_bias": eiv_bias,
        "eiv_bias_share_of_naive": abs(eiv_bias / naive_bias) if naive_bias else float("nan"),
        "eiv_sd": float(np.std(rec["eiv"], ddof=1)), "eiv_mean_se": float(np.mean(rec["eiv_se"])),
        "eiv_coverage": float(np.mean(rec["eiv_cov"])), "rc_coverage": float(np.mean(rec["rc_cov"])),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sims", type=int, default=500)
    ap.add_argument("--n", type=int, default=800)
    ap.add_argument("--out", default="docs/audits/eiv_validation.md")
    ap.add_argument("--workers", type=int, default=min(9, os.cpu_count() or 1))
    args = ap.parse_args(argv)
    warnings.simplefilter("ignore")
    t0 = time.time()
    cells = [(rel, rho, args.sims, args.n) for rel in RELIABILITIES for rho in RHOS]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(run_cell, cells))
    for r in rows:
        print(r, flush=True)
    df = pd.DataFrame(rows)
    ok = df[df.reliability >= 0.8]
    passed = bool(((ok.eiv_bias_share_of_naive < 0.10) | (ok.eiv_bias.abs() < 0.01)).all()
                  and ok.eiv_coverage.between(0.87, 0.93).all())
    mc = 1.645 * np.sqrt(0.9 * 0.1 / args.sims)
    lines = [
        "# fit_eiv simulation validation",
        "",
        f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC by `scripts/eiv_validation.py` "
        f"({args.sims} simulated data sets per cell, n = {args.n} units, {time.time() - t0:.0f} s). "
        "PLAN_ROUND_20 A2.",
        "",
        "Design: y = 1 + 2x + 0.5g + N(0, 4); published estimates x + u, y + v with heteroscedastic sampling "
        "errors and corr(u, v) = rho; synthetic replicates whose VRE variance formula reproduces the error "
        "variances. Coefficient of x, true value 2. Regression calibration (`rc`) knows the covariate's SE but "
        "not the outcome-covariate error correlation.",
        "",
        "| Reliability | rho | Naive bias | RC bias | fit_eiv bias | fit_eiv SD | fit_eiv mean SE | fit_eiv 90% coverage | RC 90% coverage |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for r in rows:
        lines.append(f"| {r['reliability']} | {r['rho']:+.1f} | {r['naive_bias']:+.4f} | {r['rc_bias']:+.4f} | "
                     f"{r['eiv_bias']:+.4f} | {r['eiv_sd']:.4f} | {r['eiv_mean_se']:.4f} | "
                     f"{r['eiv_coverage']:.3f} | {r['rc_coverage']:.3f} |")
    lines += [
        "",
        f"Monte Carlo 90% band for a true coverage of 0.90 with {args.sims} simulations: +/- {mc:.3f}.",
        "",
        f"**Acceptance** (reliability >= 0.8: fit_eiv |bias| < 10% of the naive bias, coverage 0.87-0.93): "
        f"**{'PASSED' if passed else 'FAILED'}**.",
        "",
        "Reading: naive OLS is biased by attenuation and, when the outcome's and the covariate's sampling errors "
        "are correlated, by that correlation too (negative rho adds to the attenuation, positive rho offsets it). "
        "Regression calibration removes the attenuation but not the correlated-error term. fit_eiv removes both. "
        "At reliability 0.6 the correction still removes the bias but its variance grows.",
        "",
    ]
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    print("written", args.out, "passed" if passed else "FAILED")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
