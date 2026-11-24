#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 109 full validation harness: E3d (Fuller alpha=4 ecologic slope) and J3c (Joinpoint AAPC bootstrap-t)."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from census import repairs109_core as r109

SEED = 20289109
LEVEL = 0.90


def run_e3d(rng):
    R = 400
    beta_true = 1.5
    rows = []
    for icc in (0.05, 0.15):
        sigma_b = np.sqrt(icc)
        sigma_w = np.sqrt(1.0 - icc)
        for J in (50, 150):
            for nj in (80, 150, 300):
                cov, bias = [], []
                for _ in range(R):
                    mu_x = rng.normal(0.0, sigma_b, J)
                    mu_y = beta_true * mu_x + rng.normal(0.0, 0.5, J)
                    x_ind = mu_x[:, None] + rng.normal(0.0, sigma_w, (J, nj))
                    y_ind = mu_y[:, None] + 0.5 * (x_ind - mu_x[:, None]) + rng.normal(0.0, 1.0, (J, nj))
                    ax = x_ind.mean(axis=1)
                    ay = y_ind.mean(axis=1)
                    vx = x_ind.var(axis=1, ddof=1) / nj
                    res = r109.ecologic_fuller_slope(ax, ay, vx, alpha=4.0, level=LEVEL)
                    cov.append(res["lower"] <= beta_true <= res["upper"])
                    bias.append(res["estimate"] - beta_true)
                rows.append(dict(icc=icc, J=J, n_j=nj, coverage=float(np.mean(cov)), bias=float(np.mean(bias))))
    return rows


def run_j3c(rng):
    R = 300
    B = 150
    rows = []
    for T in (15, 20):
        x = np.arange(T, dtype=float)
        tau = T // 2
        for k_true in (0, 1):
            if k_true == 0:
                log_mu = -0.02 * x
            else:
                log_mu = -0.03 * x + 0.06 * np.maximum(x - tau, 0.0)
            true_slope = float((log_mu[-1] - log_mu[0]) / (x[-1] - x[0]))
            true_aapc = float(100.0 * (np.exp(true_slope) - 1.0))
            for events in (200, 1000):
                mu = events * np.exp(log_mu)
                cov, bias = [], []
                for _ in range(R):
                    d = np.maximum(rng.poisson(mu), 1)
                    y = np.log(d / 100000.0)
                    w = d.astype(float)
                    res = r109.joinpoint_aapc_bootstrap_t(x, y, w, k=k_true, B=B, level=LEVEL, rng=rng)
                    cov.append(res["lower"] <= true_aapc <= res["upper"])
                    bias.append(res["aapc"] - true_aapc)
                rows.append(dict(T=T, k_true=k_true, events=events,
                                 coverage=float(np.mean(cov)), bias=float(np.mean(bias))))
    return rows


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    print("Running E3d (Fuller alpha=4 ecologic slope)...", flush=True)
    e3d = run_e3d(rng)
    print("Running J3c (Joinpoint AAPC bootstrap-t)...", flush=True)
    j3c = run_j3c(rng)
    elapsed = time.time() - t0

    e3d_pass = all(r["coverage"] >= 0.86 for r in e3d)
    j3c_pass = all(r["coverage"] >= 0.86 for r in j3c)

    summary = {
        "elapsed_seconds": round(elapsed, 2),
        "verdicts": {"E3d": e3d_pass, "J3c": j3c_pass},
        "E3d": e3d,
        "J3c": j3c,
    }
    os.makedirs("docs/audits", exist_ok=True)
    with open("docs/audits/repairs109_validation.json", "w") as f:
        json.dump(summary, f, indent=2)

    lines = [
        "# Round 109 Validation Report — Fuller Ecologic Slope & Joinpoint AAPC Repairs",
        "",
        f"Runtime: {elapsed:.1f}s (`scripts/repairs109_validation.py`, seed `{SEED}`).",
        "",
        "## Verdicts",
        "",
        f"- **E3d** (Fuller alpha=4 ecologic slope, `n_j >= 80, J >= 50`, 12 cells): **{'PASS' if e3d_pass else 'FAIL'}** "
        f"(min coverage {min(r['coverage'] for r in e3d):.3f}, max {max(r['coverage'] for r in e3d):.3f})",
        f"- **J3c** (Joinpoint AAPC parametric residual bootstrap-t, 8 cells): **{'PASS' if j3c_pass else 'FAIL'}** "
        f"(min coverage {min(r['coverage'] for r in j3c):.3f}, max {max(r['coverage'] for r in j3c):.3f})",
        "",
        "## E3d",
        "| ICC | J | n_j | coverage | bias |",
        "| ---: | ---: | ---: | ---: | ---: |",
        *[f"| {r['icc']} | {r['J']} | {r['n_j']} | {r['coverage']:.3f} | {r['bias']:+.4f} |" for r in e3d],
        "",
        "## J3c",
        "| T | k_true | events | coverage | bias |",
        "| ---: | ---: | ---: | ---: | ---: |",
        *[f"| {r['T']} | {r['k_true']} | {r['events']} | {r['coverage']:.3f} | {r['bias']:+.4f} |" for r in j3c],
        "",
    ]
    with open("docs/audits/repairs109_validation.md", "w") as f:
        f.write("\n".join(lines))
    print(json.dumps(summary["verdicts"], indent=2))
    print(f"Done in {elapsed:.1f}s.")


if __name__ == "__main__":
    main()
