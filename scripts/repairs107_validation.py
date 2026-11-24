#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 107 full validation harness for final-wave exploratory-measure repairs (Q2d, E3b, H2d, S2)."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from scipy import stats

from census import designation_core as desc
from census import repairs107_core as r107
from census import sae_extensions_core as sx
from census import spatial_models_core as smc

SEED = 20287107
LEVEL = 0.90


def run_q2d(rng):
    """Q2d-prob80 and Q2d-point: FH parametric bootstrap PPV predictive interval."""
    R = 400
    B = 150
    t = 0.20
    t_arc = float(desc.arcsine(t))
    out = {"Q2d-prob80": [], "Q2d-point": []}
    for N in (200, 1000):
        n_eff = rng.uniform(80, 400, N)
        D = 1.0 / (4.0 * n_eff)
        x = rng.standard_normal(N)
        X = np.column_stack([np.ones(N), x])
        for A in (0.02, 0.08):
            cov_p80, cov_pt = [], []
            for _ in range(R):
                theta = t_arc - 0.10 + 0.08 * x + np.sqrt(A) * rng.standard_normal(N)
                y = np.clip(theta + np.sqrt(D) * rng.standard_normal(N), 0.01, np.pi / 2 - 0.01)
                p = np.sin(y) ** 2
                f0 = sx.fh_interval_analytic(y, X, D)
                P0 = stats.norm.sf((t_arc - f0["estimate"]) / np.sqrt(f0["mse"]))
                # prob80
                S80 = desc.designate("prob80", p, n_eff, t, P=P0, level=LEVEL)
                if S80.sum() >= 1:
                    real = float((theta[S80] >= t_arc).mean())
                    res = r107.ppv_interval_prob80("prob80", S80, p, n_eff, X, t, B=B, level=LEVEL, rng=rng)
                    if np.isfinite(res["ppv_lower"]):
                        cov_p80.append(res["ppv_lower"] <= real <= res["ppv_upper"])
                # point with LL floor
                Spt = desc.designate("point", p, n_eff, t, P=P0, level=LEVEL)
                if Spt.sum() >= 1:
                    real = float((theta[Spt] >= t_arc).mean())
                    res = r107.ppv_interval_point_ll(Spt, p, n_eff, X, t, B=B, level=LEVEL, rng=rng)
                    if np.isfinite(res["ppv_lower"]):
                        cov_pt.append(res["ppv_lower"] <= real <= res["ppv_upper"])
            out["Q2d-prob80"].append(dict(N=N, A=A, n_eval=len(cov_p80), coverage=float(np.mean(cov_p80))))
            out["Q2d-point"].append(dict(N=N, A=A, n_eval=len(cov_pt), coverage=float(np.mean(cov_pt))))
    return out


def run_e3b(rng):
    """E3b: Croon/Fuller reliability-corrected between-area slope gated at n_j >= 40, J >= 50."""
    R = 400
    beta_true = 1.5
    icc = 0.10
    sigma_b = np.sqrt(icc)
    sigma_w = np.sqrt(1.0 - icc)
    rows = []
    for J in (50, 150):
        for nj in (40, 80, 150):
            cov, bias = [], []
            for _ in range(R):
                mu_x = rng.normal(0.0, sigma_b, J)
                mu_y = beta_true * mu_x + rng.normal(0.0, 0.5, J)
                x_ind = mu_x[:, None] + rng.normal(0.0, sigma_w, (J, nj))
                y_ind = mu_y[:, None] + 0.5 * (x_ind - mu_x[:, None]) + rng.normal(0.0, 1.0, (J, nj))
                ax = x_ind.mean(axis=1)
                ay = y_ind.mean(axis=1)
                vx = x_ind.var(axis=1, ddof=1) / nj
                res = r107.ecologic_corrected_slope(ax, ay, vx, level=LEVEL)
                cov.append(res["lower"] <= beta_true <= res["upper"])
                bias.append(res["estimate"] - beta_true)
            rows.append(dict(J=J, n_j=nj, coverage=float(np.mean(cov)), bias=float(np.mean(bias))))
    return rows


def run_h2d(rng):
    """H2d: PUMS Hotelling F(K - 1, R - K + 1) homogeneity under exact per-measure nulls, n >= 500."""
    R_sim = 400
    n_rep = 80
    rows = []
    for measure in ("rr", "or", "rd"):
        for K in (3, 5):
            for n_s in (500, 800):
                p0_vec = np.linspace(0.15, 0.35, K)
                if measure == "rr":
                    p1_vec = np.clip(p0_vec * 1.5, 0.02, 0.98)
                elif measure == "or":
                    odds0 = p0_vec / (1.0 - p0_vec)
                    odds1 = odds0 * 1.8
                    p1_vec = odds1 / (1.0 + odds1)
                else:
                    p1_vec = np.clip(p0_vec + 0.12, 0.02, 0.98)
                rej = 0
                for _ in range(R_sim):
                    # Generate K strata with PUMS-like unequal weights (CV ~ 0.6) and 80 SDR replicates
                    N_tot = K * n_s
                    s = np.repeat(np.arange(K), n_s)
                    e = rng.binomial(1, 0.45, N_tot)
                    probs = np.where(e == 1, p1_vec[s], p0_vec[s])
                    y = rng.binomial(1, probs)
                    w0 = rng.gamma(2.8, 1.0 / 2.8, N_tot)
                    # Build 80 SDR replicate weights via random half-sample perturbation (factor 4/80 -> sd 0.5)
                    # Standard Fay/SDR-like replicate multipliers with Var(w_r/w0) = 1/4 so 4/80 sum (est_r - est)^2 = Var
                    half = rng.choice([-0.5, 0.5], size=(n_rep, N_tot))
                    W = np.vstack([w0[None, :], w0[None, :] * (1.0 + half)]).T
                    res = r107.mh_replicate_homogeneity_f(y, e, s, W, list(range(K)))
                    if res[measure]["p_value"] <= 0.10:
                        rej += 1
                rows.append(dict(measure=measure, K=K, n_per_stratum=n_s, size=float(rej / R_sim)))
    return rows


def run_s2(rng):
    """S2: Shannon entropy diversity with exact SDR replicate bias correction E_bc = E - 4*(mean(Er) - E)."""
    R_sim = 500
    n_rep = 80
    rows = []
    for G in (4, 6):
        # Realistic skewed tract group shares (e.g. race/ethnicity)
        p_true = np.array([0.55, 0.25, 0.12, 0.08]) if G == 4 else np.array([0.48, 0.22, 0.12, 0.08, 0.06, 0.04])
        H_true = float(smc.entropy(p_true))
        for n_resp in (50, 100, 200):
            cov, bias = [], []
            for _ in range(R_sim):
                # Draw n_resp individuals from multinomial(p_true), compute 80 SDR replicate shares
                cats = rng.choice(G, size=n_resp, p=p_true)
                Y_ind = np.eye(G)[cats]  # (n_resp, G)
                w0 = np.ones(n_resp)
                half = rng.choice([-0.5, 0.5], size=(n_rep, n_resp))
                W_rep = 1.0 + half  # (n_rep, n_resp)
                P = (w0 @ Y_ind)[None, :] / w0.sum()
                Pr_counts = W_rep @ Y_ind  # (n_rep, G)
                Pr = (Pr_counts / Pr_counts.sum(axis=1, keepdims=True))[:, None, :]
                res = r107.diversity_sdr_bc(P, Pr, level=LEVEL)
                est = float(res["estimate"][0])
                lo = float(res["lower"][0])
                hi = float(res["upper"][0])
                cov.append(lo <= H_true <= hi)
                bias.append(est - H_true)
            rows.append(dict(G=G, n_resp=n_resp, coverage=float(np.mean(cov)), bias=float(np.mean(bias))))
    return rows


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    print("Running Q2d (FH PPV prob80 & point-LL)...", flush=True)
    q2d = run_q2d(rng)
    print("Running E3b (Croon/Fuller ecologic slope, n_j >= 40)...", flush=True)
    e3b = run_e3b(rng)
    print("Running H2d (PUMS Hotelling F homogeneity, n >= 500)...", flush=True)
    h2d = run_h2d(rng)
    print("Running S2 (Shannon entropy SDR bias correction)...", flush=True)
    s2 = run_s2(rng)
    elapsed = time.time() - t0

    q2d_p80_pass = all(r["coverage"] >= 0.86 for r in q2d["Q2d-prob80"])
    q2d_pt_pass = all(r["coverage"] >= 0.86 for r in q2d["Q2d-point"])
    e3b_pass = all(r["coverage"] >= 0.86 for r in e3b)
    h2d_pass = all(r["size"] <= 0.13 for r in h2d)
    s2_all_pass = all(r["coverage"] >= 0.86 for r in s2)
    s2_100_pass = all(r["coverage"] >= 0.86 for r in s2 if r["n_resp"] >= 100)

    summary = {
        "elapsed_seconds": round(elapsed, 2),
        "verdicts": {
            "Q2d-prob80": q2d_p80_pass,
            "Q2d-point": q2d_pt_pass,
            "E3b": e3b_pass,
            "H2d": h2d_pass,
            "S2_all": s2_all_pass,
            "S2_n100": s2_100_pass,
        },
        "Q2d-prob80": q2d["Q2d-prob80"],
        "Q2d-point": q2d["Q2d-point"],
        "E3b": e3b,
        "H2d": h2d,
        "S2": s2,
    }
    os.makedirs("docs/audits", exist_ok=True)
    with open("docs/audits/repairs107_validation.json", "w") as f:
        json.dump(summary, f, indent=2)

    lines = [
        "# Round 107 Validation Report — Final-Wave Exploratory-Measure Repairs",
        "",
        f"Runtime: {elapsed:.1f}s (`scripts/repairs107_validation.py`, seed `{SEED}`).",
        "",
        "## Verdicts",
        "",
        f"- **Q2d-prob80** (FH parametric bootstrap PPV, `rule='prob80'`): **{'PASS' if q2d_p80_pass else 'FAIL'}** "
        f"(min coverage {min(r['coverage'] for r in q2d['Q2d-prob80']):.3f}, max {max(r['coverage'] for r in q2d['Q2d-prob80']):.3f})",
        f"- **Q2d-point** (FH parametric bootstrap PPV, `rule='point'` with LL floor): **{'PASS' if q2d_pt_pass else 'FAIL'}** "
        f"(min coverage {min(r['coverage'] for r in q2d['Q2d-point']):.3f}, max {max(r['coverage'] for r in q2d['Q2d-point']):.3f})",
        f"- **E3b** (Croon/Fuller ecologic slope, `n_j >= 40, J >= 50`): **{'PASS' if e3b_pass else 'FAIL'}** "
        f"(min coverage {min(r['coverage'] for r in e3b):.3f}, max {max(r['coverage'] for r in e3b):.3f})",
        f"- **H2d** (PUMS Hotelling F homogeneity, `min_stratum_n >= 500`): **{'PASS' if h2d_pass else 'FAIL'}** "
        f"(min size {min(r['size'] for r in h2d):.3f}, max {max(r['size'] for r in h2d):.3f})",
        f"- **S2** (Shannon entropy SDR bias correction): **all n {'PASS' if s2_all_pass else 'FAIL'}** / "
        f"**n >= 100 {'PASS' if s2_100_pass else 'FAIL'}** "
        f"(all min {min(r['coverage'] for r in s2):.3f}; n>=100 min {min(r['coverage'] for r in s2 if r['n_resp'] >= 100):.3f})",
        "",
        "## Q2d-prob80",
        "| N | A | n_eval | coverage |",
        "| ---: | ---: | ---: | ---: |",
        *[f"| {r['N']} | {r['A']} | {r['n_eval']} | {r['coverage']:.3f} |" for r in q2d["Q2d-prob80"]],
        "",
        "## Q2d-point",
        "| N | A | n_eval | coverage |",
        "| ---: | ---: | ---: | ---: |",
        *[f"| {r['N']} | {r['A']} | {r['n_eval']} | {r['coverage']:.3f} |" for r in q2d["Q2d-point"]],
        "",
        "## E3b",
        "| J | n_j | coverage | bias |",
        "| ---: | ---: | ---: | ---: |",
        *[f"| {r['J']} | {r['n_j']} | {r['coverage']:.3f} | {r['bias']:+.4f} |" for r in e3b],
        "",
        "## H2d",
        "| measure | K | n_per_stratum | size |",
        "| :--- | ---: | ---: | ---: |",
        *[f"| {r['measure']} | {r['K']} | {r['n_per_stratum']} | {r['size']:.3f} |" for r in h2d],
        "",
        "## S2",
        "| G | n_resp | coverage | bias |",
        "| ---: | ---: | ---: | ---: |",
        *[f"| {r['G']} | {r['n_resp']} | {r['coverage']:.3f} | {r['bias']:+.4f} |" for r in s2],
        "",
    ]
    with open("docs/audits/repairs107_validation.md", "w") as f:
        f.write("\n".join(lines))
    print(json.dumps(summary["verdicts"], indent=2))
    print(f"Done in {elapsed:.1f}s.")


if __name__ == "__main__":
    main()
