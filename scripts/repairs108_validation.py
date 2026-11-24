#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 108 full validation harness: M5b (vector multi-confounder g-formula), E3c (ecologic slope n_j >= 80),
and S2b (Shannon entropy SDR bias correction n_resp >= 150)."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from census import repairs108_core as r108
from census import spatial_models_core as smc

SEED = 20288108
LEVEL = 0.90


def _sim_vector_panel(rng, G, K, p, feedback, psi):
    """Simulate balanced panel of G units x K annual periods with p correlated time-varying confounders,
    VAR(1) cross-confounder feedback Phi, treatment-confounder feedback gamma_A, and start-and-stay treatment."""
    if p == 2:
        Phi = np.array([[0.50, 0.15], [0.10, 0.45]])
        gamma_A = np.array([feedback, -0.5 * feedback])
        delta = np.array([0.80, -0.60])
        beta_A = np.array([0.55, -0.35])
    else:
        Phi = np.array([[0.50, 0.12, 0.08], [0.10, 0.45, 0.10], [0.05, 0.10, 0.40]])
        gamma_A = np.array([feedback, -0.5 * feedback, 0.4 * feedback])
        delta = np.array([0.80, -0.60, 0.50])
        beta_A = np.array([0.50, -0.30, 0.25])

    # Analytical true total effects for durations 1, 2, 3
    truth = np.zeros(3)
    dL = np.zeros(p)
    for d in range(3):
        if d > 0:
            dL = gamma_A + Phi @ dL
        truth[d] = psi + float(delta @ dL)

    unit = np.repeat(np.arange(G), K)
    year = np.tile(np.arange(1, K + 1), G)
    L = np.zeros((G, K, p))
    A = np.zeros((G, K))
    Y = np.zeros((G, K))
    u_eff = rng.normal(0.0, 0.6, G)
    t_eff = np.linspace(0.0, 1.0, K)

    L[:, 0, :] = rng.normal(0.0, 1.0, (G, p))
    for t in range(1, K):
        L[:, t, :] = L[:, t - 1, :] @ Phi.T + A[:, t - 1, None] * gamma_A[None, :] + rng.normal(0.0, 0.7, (G, p))
        if t >= 2:
            # Start-and-stay treatment hazard driven by L_t
            lin = -2.2 + L[:, t, :] @ beta_A
            prob = 1.0 / (1.0 + np.exp(-lin))
            start = (A[:, t - 1] == 0) & (rng.random(G) < prob)
            A[:, t] = np.where((A[:, t - 1] == 1) | start, 1.0, 0.0)
    for t in range(K):
        Y[:, t] = 10.0 + u_eff + t_eff[t] + psi * A[:, t] + L[:, t, :] @ delta + rng.normal(0.0, 0.6, G)

    return Y.reshape(-1), A.reshape(-1), L.reshape(-1, p), unit, year, truth


def run_m5b(rng):
    R = 400
    G = 51
    rows = []
    for p in (2, 3):
        for K in (12, 18):
            for fb in (0.0, 0.5):
                for psi in (0.0, -2.0):
                    cov = np.zeros(3)
                    bias = np.zeros(3)
                    for _ in range(R):
                        Y, A, L, unit, year, truth = _sim_vector_panel(rng, G, K, p, fb, psi)
                        res = r108.gformula_vector_jackknife(Y, A, L, unit, year, K, level=LEVEL, report=3)
                        est = np.asarray(res["estimate"])
                        lo = np.asarray(res["lower"])
                        hi = np.asarray(res["upper"])
                        cov += (lo <= truth) & (truth <= hi)
                        bias += est - truth
                    cov /= R
                    bias /= R
                    for d in range(3):
                        rows.append(dict(p=p, K=K, feedback=fb, psi=psi, duration=d + 1,
                                         coverage=float(cov[d]), bias=float(bias[d])))
    return rows


def run_e3c(rng):
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
                    res = r108.ecologic_corrected_slope(ax, ay, vx, level=LEVEL)
                    cov.append(res["lower"] <= beta_true <= res["upper"])
                    bias.append(res["estimate"] - beta_true)
                rows.append(dict(icc=icc, J=J, n_j=nj, coverage=float(np.mean(cov)), bias=float(np.mean(bias))))
    return rows


def run_s2b(rng):
    R_sim = 500
    n_rep = 80
    rows = []
    for G in (4, 6):
        p_true = np.array([0.55, 0.25, 0.12, 0.08]) if G == 4 else np.array([0.48, 0.22, 0.12, 0.08, 0.06, 0.04])
        H_true = float(smc.entropy(p_true))
        for n_resp in (150, 200, 400):
            cov, bias = [], []
            for _ in range(R_sim):
                cats = rng.choice(G, size=n_resp, p=p_true)
                Y_ind = np.eye(G)[cats]
                w0 = np.ones(n_resp)
                W_rep = 1.0 + rng.choice([-0.5, 0.5], size=(n_rep, n_resp))
                P = (w0 @ Y_ind)[None, :] / w0.sum()
                Pr_c = W_rep @ Y_ind
                Pr = (Pr_c / Pr_c.sum(axis=1, keepdims=True))[:, None, :]
                res = r108.diversity_sdr_bc(P, Pr, level=LEVEL)
                cov.append(float(res["lower"][0]) <= H_true <= float(res["upper"][0]))
                bias.append(float(res["estimate"][0]) - H_true)
            rows.append(dict(G=G, n_resp=n_resp, coverage=float(np.mean(cov)), bias=float(np.mean(bias))))
    return rows


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    print("Running M5b (vector multi-confounder parametric g-formula)...", flush=True)
    m5b = run_m5b(rng)
    print("Running E3c (Croon/Fuller ecologic slope, n_j >= 80)...", flush=True)
    e3c = run_e3c(rng)
    print("Running S2b (Shannon entropy SDR bias correction, n_resp >= 150)...", flush=True)
    s2b = run_s2b(rng)
    elapsed = time.time() - t0

    m5b_pass = all(r["coverage"] >= 0.86 for r in m5b)
    e3c_pass = all(r["coverage"] >= 0.86 for r in e3c)
    s2b_pass = all(r["coverage"] >= 0.86 for r in s2b)

    summary = {
        "elapsed_seconds": round(elapsed, 2),
        "verdicts": {"M5b": m5b_pass, "E3c": e3c_pass, "S2b": s2b_pass},
        "M5b": m5b,
        "E3c": e3c,
        "S2b": s2b,
    }
    os.makedirs("docs/audits", exist_ok=True)
    with open("docs/audits/repairs108_validation.json", "w") as f:
        json.dump(summary, f, indent=2)

    lines = [
        "# Round 108 Validation Report — Multi-Confounder G-Formula & Realistic-Regime Gated Repairs",
        "",
        f"Runtime: {elapsed:.1f}s (`scripts/repairs108_validation.py`, seed `{SEED}`).",
        "",
        "## Verdicts",
        "",
        f"- **M5b** (Vector parametric g-formula, `p ∈ {{2, 3}}`, 48 cells): **{'PASS' if m5b_pass else 'FAIL'}** "
        f"(min coverage {min(r['coverage'] for r in m5b):.3f}, max {max(r['coverage'] for r in m5b):.3f}, "
        f"max |bias| {max(abs(r['bias']) for r in m5b):.4f})",
        f"- **E3c** (Croon/Fuller ecologic slope, `n_j >= 80, J >= 50`, 12 cells): **{'PASS' if e3c_pass else 'FAIL'}** "
        f"(min coverage {min(r['coverage'] for r in e3c):.3f}, max {max(r['coverage'] for r in e3c):.3f})",
        f"- **S2b** (Shannon entropy SDR bias correction, `n_resp >= 150`, 6 cells): **{'PASS' if s2b_pass else 'FAIL'}** "
        f"(min coverage {min(r['coverage'] for r in s2b):.3f}, max {max(r['coverage'] for r in s2b):.3f})",
        "",
        "## M5b (Summary by p, K, feedback, psi, duration)",
        "| p | K | feedback | psi | d | coverage | bias |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        *[f"| {r['p']} | {r['K']} | {r['feedback']} | {r['psi']} | {r['duration']} | {r['coverage']:.3f} | {r['bias']:+.4f} |"
          for r in m5b],
        "",
        "## E3c",
        "| ICC | J | n_j | coverage | bias |",
        "| ---: | ---: | ---: | ---: | ---: |",
        *[f"| {r['icc']} | {r['J']} | {r['n_j']} | {r['coverage']:.3f} | {r['bias']:+.4f} |" for r in e3c],
        "",
        "## S2b",
        "| G | n_resp | coverage | bias |",
        "| ---: | ---: | ---: | ---: |",
        *[f"| {r['G']} | {r['n_resp']} | {r['coverage']:.3f} | {r['bias']:+.4f} |" for r in s2b],
        "",
    ]
    with open("docs/audits/repairs108_validation.md", "w") as f:
        f.write("\n".join(lines))
    print(json.dumps(summary["verdicts"], indent=2))
    print(f"Done in {elapsed:.1f}s.")


if __name__ == "__main__":
    main()
