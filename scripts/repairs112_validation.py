#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 112 full validation harness for the 5 remaining repairable exploratory candidates:
M3b (3-level variance shares), Q2e (designation lower/prob50 PPV), D2 (count disparity indices),
R2_dens (RDD density test), and W3_rr (stratified RR homogeneity)."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from scipy import stats

from census import designation_core as desc
from census import repairs112_core as r112
from census import sae_extensions_core as sx

SEED = 20292112
LEVEL = 0.90


def run_m3b(rng):
    """M3b: Three-level variance-share delete-one-top-unit logit jackknife (G_top in {30, 49}, 2 splits)."""
    R = 200
    rows = []
    splits = [
        ("70_15_15", (0.70, 0.15, 0.15)),
        ("50_25_25", (0.50, 0.25, 0.25)),
    ]
    for G_top in (30, 49):
        n_mid = 6
        n_bot = 8
        top_id = np.repeat(np.arange(G_top), n_mid * n_bot)
        mid_id = np.repeat(np.arange(G_top * n_mid), n_bot)
        N = len(top_id)
        for sname, (sb, sm, st) in splits:
            cov = {"bottom": [], "mid": [], "top": []}
            truth = {"bottom": sb, "mid": sm, "top": st}
            for _ in range(R):
                u_top = rng.normal(0.0, np.sqrt(st), G_top)[top_id]
                u_mid = rng.normal(0.0, np.sqrt(sm), G_top * n_mid)[mid_id]
                eps = rng.normal(0.0, np.sqrt(sb), N)
                x = rng.normal(0.0, 1.0, N)
                y = 2.0 + 0.5 * x + u_top + u_mid + eps
                df = pd.DataFrame({"y": y, "x": x, "top": top_id.astype(str), "mid": mid_id.astype(str)})
                jk = r112.jackknife_shares(df, "y ~ x", "top", "mid", level=LEVEL)
                for k in ("bottom", "mid", "top"):
                    cov[k].append(jk[k]["lower"] <= truth[k] <= jk[k]["upper"])
            for k in ("bottom", "mid", "top"):
                rows.append(dict(G_top=G_top, split=sname, share=k, coverage=float(np.mean(cov[k]))))
    return rows


def run_q2e(rng):
    """Q2e-lower and Q2e-prob50: FH parametric bootstrap PPV with LL floor."""
    R = 300
    B = 120
    t = 0.20
    t_arc = float(desc.arcsine(t))
    out = {"Q2e-lower": [], "Q2e-prob50": []}
    for N in (200, 1000):
        n_eff = rng.uniform(80, 400, N)
        D = 1.0 / (4.0 * n_eff)
        x = rng.standard_normal(N)
        X = np.column_stack([np.ones(N), x])
        for A in (0.02, 0.08):
            cov_lo, cov_50 = [], []
            for _ in range(R):
                theta = t_arc - 0.08 + 0.08 * x + np.sqrt(A) * rng.standard_normal(N)
                y = np.clip(theta + np.sqrt(D) * rng.standard_normal(N), 0.01, np.pi / 2 - 0.01)
                p = np.sin(y) ** 2
                f0 = sx.fh_interval_analytic(y, X, D)
                P0 = stats.norm.sf((t_arc - f0["estimate"]) / np.sqrt(f0["mse"]))
                for rule, bag in (("lower", cov_lo), ("prob50", cov_50)):
                    S = desc.designate(rule, p, n_eff, t, P=P0, level=LEVEL)
                    if S.sum() >= 1:
                        real = float((theta[S] >= t_arc).mean())
                        res = r112.ppv_interval_ll(rule, S, p, n_eff, X, t, B=B, level=LEVEL, rng=rng)
                        if np.isfinite(res["ppv_lower"]):
                            bag.append(res["ppv_lower"] <= real <= res["ppv_upper"])
            out["Q2e-lower"].append(dict(N=N, A=A, n_eval=len(cov_lo), coverage=float(np.mean(cov_lo))))
            out["Q2e-prob50"].append(dict(N=N, A=A, n_eval=len(cov_50), coverage=float(np.mean(cov_50))))
    return out


def run_d2(rng):
    """D2: Count-scale disparity indices (idisp, bgv, theil, mld) gated at min_events >= 100."""
    R = 300
    B = 200
    out = {k: [] for k in ("idisp", "bgv", "theil", "mld")}
    for G in (3, 5):
        pops = np.linspace(50000.0, 150000.0, G)
        w = pops / pops.sum()
        for min_ev in (100, 500):
            for spread_name, mult in (("moderate", 1.8), ("wide", 3.0)):
                r_base = min_ev / pops[0]
                r_true = np.linspace(r_base, r_base * mult, G)
                mu_true = float(np.sum(w * r_true))
                ratio_t = r_true / mu_true
                truth = {
                    "idisp": float(np.mean(np.abs(r_true - r_true[0])) / r_true[0]),
                    "bgv": float(np.sum(w * (r_true - mu_true) ** 2)),
                    "theil": float(np.sum(w * ratio_t * np.log(ratio_t))),
                    "mld": float(-np.sum(w * np.log(ratio_t))),
                }
                mu_counts = r_true * pops
                cov = {k: [] for k in out}
                for _ in range(R):
                    c = np.maximum(rng.poisson(mu_counts), 1)
                    res = r112.count_disparity_indices_boot(c, pops, ref_idx=0, B=B, level=LEVEL, rng=rng)
                    for k in out:
                        cov[k].append(res[k]["lower"] <= truth[k] <= res[k]["upper"])
                for k in out:
                    out[k].append(dict(G=G, min_events=min_ev, spread=spread_name, coverage=float(np.mean(cov[k]))))
    return out


def run_r2_dens(rng):
    """R2_dens: RDD density/manipulation test null size across smooth densities."""
    R = 400
    rows = []
    for dist in ("uniform", "normal", "beta22"):
        for n in (1000, 5000):
            rej = 0
            for _ in range(R):
                if dist == "uniform":
                    x = rng.uniform(-1.0, 1.0, n)
                    c = 0.0
                elif dist == "normal":
                    x = rng.normal(0.0, 1.0, n)
                    c = 0.0
                else:
                    x = rng.beta(2.0, 2.0, n) - 0.5
                    c = 0.0
                res = r112.rdd_density_test(x, c)
                if res["p"] <= 0.10:
                    rej += 1
            rows.append(dict(dist=dist, n=n, size=float(rej / R)))
    return rows


def run_w3_rr(rng):
    """W3_rr: Stratified count RR homogeneity test (woolf_rr) gated at min_cases >= 15."""
    R = 400
    rows = []
    for K in (3, 5):
        p0 = np.linspace(0.08, 0.20, K)
        p1 = p0 * 1.5
        for min_cases in (15, 40):
            n_arm = np.ceil(min_cases / p0).astype(int)
            rej = 0
            for _ in range(R):
                a = rng.binomial(n_arm, p1).astype(float)
                c = rng.binomial(n_arm, p0).astype(float)
                b = n_arm - a
                d = n_arm - c
                rr_mh = float(np.sum(a * n_arm / (2 * n_arm)) / max(np.sum(c * n_arm / (2 * n_arm)), 1e-12))
                _, p_val, _ = r112.woolf_rr(a, b, c, d, rr_mh)
                if np.isfinite(p_val) and p_val <= 0.10:
                    rej += 1
            rows.append(dict(K=K, min_cases=min_cases, size=float(rej / R)))
    return rows


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    print("Running M3b (3-level variance-share jackknife)...", flush=True)
    m3b = run_m3b(rng)
    print("Running Q2e (designation lower & prob50 PPV)...", flush=True)
    q2e = run_q2e(rng)
    print("Running D2 (count-scale disparity indices)...", flush=True)
    d2 = run_d2(rng)
    print("Running R2_dens (RDD density test)...", flush=True)
    r2d = run_r2_dens(rng)
    print("Running W3_rr (stratified RR homogeneity)...", flush=True)
    w3 = run_w3_rr(rng)
    elapsed = time.time() - t0

    verdicts = {
        "M3b": all(r["coverage"] >= 0.86 for r in m3b),
        "Q2e-lower": all(r["coverage"] >= 0.86 for r in q2e["Q2e-lower"]),
        "Q2e-prob50": all(r["coverage"] >= 0.86 for r in q2e["Q2e-prob50"]),
        **{f"D2-{k}": all(r["coverage"] >= 0.86 for r in d2[k]) for k in d2},
        "R2_dens": all(0.07 <= r["size"] <= 0.13 for r in r2d),
        "W3_rr": all(0.07 <= r["size"] <= 0.13 for r in w3),
    }

    summary = {
        "elapsed_seconds": round(elapsed, 2),
        "verdicts": verdicts,
        "M3b": m3b,
        "Q2e-lower": q2e["Q2e-lower"],
        "Q2e-prob50": q2e["Q2e-prob50"],
        "D2": d2,
        "R2_dens": r2d,
        "W3_rr": w3,
    }
    os.makedirs("docs/audits", exist_ok=True)
    with open("docs/audits/repairs112_validation.json", "w") as f:
        json.dump(summary, f, indent=2)

    lines = [
        "# Round 112 Validation Report — Final Repairable Exploratory Wave",
        "",
        f"Runtime: {elapsed:.1f}s (`scripts/repairs112_validation.py`, seed `{SEED}`).",
        "",
        "## Verdicts",
        "",
        *[f"- **{k}**: **{'PASS' if v else 'FAIL'}**" for k, v in verdicts.items()],
        "",
        "## M3b (Three-level variance shares)",
        "| G_top | split | share | coverage |",
        "| ---: | :--- | :--- | ---: |",
        *[f"| {r['G_top']} | {r['split']} | {r['share']} | {r['coverage']:.3f} |" for r in m3b],
        "",
        "## Q2e-lower",
        "| N | A | n_eval | coverage |",
        "| ---: | ---: | ---: | ---: |",
        *[f"| {r['N']} | {r['A']} | {r['n_eval']} | {r['coverage']:.3f} |" for r in q2e["Q2e-lower"]],
        "",
        "## Q2e-prob50",
        "| N | A | n_eval | coverage |",
        "| ---: | ---: | ---: | ---: |",
        *[f"| {r['N']} | {r['A']} | {r['n_eval']} | {r['coverage']:.3f} |" for r in q2e["Q2e-prob50"]],
        "",
        "## D2 (Count disparity indices, min_events >= 100)",
        "| index | min_cov | max_cov |",
        "| :--- | ---: | ---: |",
        *[f"| {k} | {min(r['coverage'] for r in d2[k]):.3f} | {max(r['coverage'] for r in d2[k]):.3f} |" for k in d2],
        "",
        "## R2_dens (RDD density test)",
        "| dist | n | size |",
        "| :--- | ---: | ---: |",
        *[f"| {r['dist']} | {r['n']} | {r['size']:.3f} |" for r in r2d],
        "",
        "## W3_rr (Stratified RR homogeneity, min_cases >= 15)",
        "| K | min_cases | size |",
        "| ---: | ---: | ---: |",
        *[f"| {r['K']} | {r['min_cases']} | {r['size']:.3f} |" for r in w3],
        "",
    ]
    with open("docs/audits/repairs112_validation.md", "w") as f:
        f.write("\n".join(lines))
    print(json.dumps(verdicts, indent=2))
    print(f"Done in {elapsed:.1f}s.")


if __name__ == "__main__":
    main()
