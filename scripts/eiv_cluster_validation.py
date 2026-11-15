# SPDX-License-Identifier: AGPL-3.0-or-later
"""Simulation validation of fit_eiv's cluster-robust sandwich (PLAN_ROUND_21 B1; Round 20 friction F6).

Design: G clusters (counties) of m units (tracts), n = G*m. The true covariate and the model
error share a cluster component with intra-cluster correlation icc:
    x = 10 + 3 (sqrt(icc) a_g + sqrt(1-icc) z_i),   eps = 2 (sqrt(icc) b_g + sqrt(1-icc) z'_i),
    y = 1 + 2 x + eps.
The covariate is published with heteroscedastic ACS-type sampling error (reliability 0.8) and
synthetic replicates (as in scripts/eiv_validation.py). The outcome is either
- "acs": published with ACS-type error correlated 0.5 with the covariate's, with replicates; or
- "external": a model-based outcome (e.g. CDC PLACES) with independent error that itself has a
  cluster-shared part (a county random-effect draw) and no replicates, held fixed
  (fixed_variables).
Each fit reports the clustered se_total (cluster = GEOID.str[:5]) and the independence sandwich
(diagnostics["se_total_independent"]). Coefficient of x, true value 2.

Acceptance (PLAN_ROUND_21 B1): clustered 90% coverage 0.87-0.93 for G >= 60 in every cell; bias
below 10% of the naive bias (or |bias| < 0.01). G = 30 is reported.

Usage: python scripts/eiv_cluster_validation.py [--sims 500] [--n 3000] [--workers 12]
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

from census.models import fit_eiv  # noqa: E402
from census.variance import REPLICATE_COLUMNS  # noqa: E402

BETA = 2.0
REL = 0.8
GS = (30, 60, 150)
ICCS = (0.0, 0.2, 0.5)
OUTCOMES = ("acs", "external")


def simulate(seed, n, G, icc, outcome):
    rng = np.random.default_rng(seed)
    g = np.repeat(np.arange(G), int(np.ceil(n / G)))[:n]
    a, b, c = rng.standard_normal(G), rng.standard_normal(G), rng.standard_normal(G)
    x = 10 + 3 * (np.sqrt(icc) * a[g] + np.sqrt(1 - icc) * rng.standard_normal(n))
    eps = 2 * (np.sqrt(icc) * b[g] + np.sqrt(1 - icc) * rng.standard_normal(n))
    y = 1 + BETA * x + eps
    s2x = rng.uniform(0.2, 1.8, n) * 9 * (1 - REL) / REL
    z1 = rng.standard_normal(n)
    xo = x + np.sqrt(s2x) * z1
    Z1 = rng.standard_normal((n, 80))
    xr = xo[:, None] + np.sqrt(s2x / 4)[:, None] * Z1
    geo = [f"{gi:05d}{i:06d}" for i, gi in enumerate(g)]
    parts = [pd.DataFrame({"GEOID": geo, "variable": "x", "estimate": xo, **dict(zip(REPLICATE_COLUMNS, xr.T))})]
    if outcome == "acs":
        rho = 0.5
        s2y = rng.uniform(0.5, 1.5, n) * 4
        z2 = rho * z1 + np.sqrt(1 - rho**2) * rng.standard_normal(n)
        yo = y + np.sqrt(s2y) * z2
        Z2 = rho * Z1 + np.sqrt(1 - rho**2) * rng.standard_normal((n, 80))
        yr = yo[:, None] + np.sqrt(s2y / 4)[:, None] * Z2
        parts.append(pd.DataFrame({"GEOID": geo, "variable": "y", "estimate": yo,
                                   **dict(zip(REPLICATE_COLUMNS, yr.T))}))
    else:  # model-based outcome: independent error with a shared county draw, no replicates
        s2y = rng.uniform(0.5, 1.5, n) * 2
        yo = y + np.sqrt(s2y) * (np.sqrt(0.5) * c[g] + np.sqrt(0.5) * rng.standard_normal(n))
    frame = pd.DataFrame({"GEOID": geo, "x": xo, "x_se": np.sqrt(s2x), "y": yo, "y_se": np.sqrt(s2y)})
    return frame, pd.concat(parts, ignore_index=True)


def run_cell(cell):
    G, icc, outcome, sims, n = cell
    warnings.simplefilter("ignore")
    est, naive, se_c, se_i, cov_c, cov_i = [], [], [], [], [], []
    for s in range(sims):
        frame, reps = simulate(7919 * s + 13 * G + int(100 * icc) + (0 if outcome == "acs" else 1), n, G, icc,
                               outcome)
        res = fit_eiv("y ~ x", frame, reps, cluster="GEOID.str[:5]", replicate_policy="strict",
                      fixed_variables=["y"] if outcome == "external" else ())
        row = res.coefficients.set_index("term").loc["x"]
        e, sc = float(row["estimate"]), float(row["se_total"])
        si = float(res.diagnostics["se_total_independent"]["x"])
        z = float(row["ci_upper"] - row["estimate"]) / sc  # the interval's own critical value
        est.append(e)
        naive.append(float(row["naive_estimate"]))
        se_c.append(sc)
        se_i.append(si)
        cov_c.append(abs(e - BETA) <= z * sc)
        cov_i.append(abs(e - BETA) <= z * si)
    bias, nbias = float(np.mean(est) - BETA), float(np.mean(naive) - BETA)
    return {"G": G, "icc": icc, "outcome": outcome, "sims": sims, "naive_bias": nbias, "bias": bias,
            "bias_share": abs(bias / nbias) if nbias else float("nan"), "sd": float(np.std(est, ddof=1)),
            "mean_se_clustered": float(np.mean(se_c)), "mean_se_independent": float(np.mean(se_i)),
            "coverage_clustered": float(np.mean(cov_c)), "coverage_independent": float(np.mean(cov_i))}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sims", type=int, default=500)
    ap.add_argument("--n", type=int, default=3000)
    ap.add_argument("--out", default="docs/audits/eiv_cluster_validation.md")
    ap.add_argument("--workers", type=int, default=min(12, os.cpu_count() or 1))
    args = ap.parse_args(argv)
    t0 = time.time()
    cells = [(G, icc, o, args.sims, args.n) for G in GS for icc in ICCS for o in OUTCOMES]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(run_cell, cells))
    for r in rows:
        print(r, flush=True)
    df = pd.DataFrame(rows)
    big = df[df.G >= 60]
    passed = bool(big.coverage_clustered.between(0.87, 0.93).all()
                  and ((df.bias_share < 0.10) | (df.bias.abs() < 0.01)).all())
    mc = 1.645 * np.sqrt(0.9 * 0.1 / args.sims)
    lines = [
        "# fit_eiv cluster-robust sandwich: simulation validation",
        "",
        f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC by "
        f"`scripts/eiv_cluster_validation.py` ({args.sims} simulated data sets per cell, n = {args.n} units, "
        f"{time.time() - t0:.0f} s). PLAN_ROUND_21 B1 (Round 20 friction F6).",
        "",
        "Design: G clusters of n/G units; the true covariate and the model error share a cluster component with "
        "intra-cluster correlation `icc`; y = 1 + 2x + error. The covariate carries heteroscedastic ACS-type "
        "sampling error (reliability 0.8) with synthetic replicates. Outcome `acs`: ACS-type error correlated 0.5 "
        "with the covariate's, with replicates. Outcome `external`: a model-based outcome (as CDC PLACES) with "
        "independent error that has a shared cluster draw, no replicates, held fixed (`fixed_variables`). "
        "Clustered = `cluster=\"GEOID.str[:5]\"` (CR1: G/(G-1) x (n-1)/(n-k)); independent = the independence "
        "sandwich of the same fit. Coefficient of x, true value 2.",
        "",
        "| G | icc | outcome | naive bias | fit_eiv bias | SD | mean SE clustered | mean SE independent | "
        "coverage clustered | coverage independent |",
        "| ---: | ---: | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for r in rows:
        lines.append(f"| {r['G']} | {r['icc']} | {r['outcome']} | {r['naive_bias']:+.4f} | {r['bias']:+.4f} | "
                     f"{r['sd']:.4f} | {r['mean_se_clustered']:.4f} | {r['mean_se_independent']:.4f} | "
                     f"{r['coverage_clustered']:.3f} | {r['coverage_independent']:.3f} |")
    lines += [
        "",
        f"Monte Carlo 90% band for a true coverage of 0.90 with {args.sims} simulations: +/- {mc:.3f}.",
        "",
        f"**Acceptance** (G >= 60: clustered coverage 0.87-0.93 in every cell; bias < 10% of the naive bias or "
        f"|bias| < 0.01 everywhere): **{'PASSED' if passed else 'FAILED'}**.",
        "",
        "Reading: with no clustering (icc 0) both sandwiches cover. When the covariate and the errors share "
        "cluster components, the independence sandwich understates the SE and under-covers, increasingly with "
        "icc and cluster size; the clustered sandwich restores coverage. With few clusters (G = 30) CR1 tends to "
        "be slightly liberal, the known small-G behaviour (Cameron & Miller 2015); prefer G >= 50.",
        "",
    ]
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    print("written", args.out, "passed" if passed else "FAILED")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
