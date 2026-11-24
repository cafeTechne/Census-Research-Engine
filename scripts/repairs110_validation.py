#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 110 full validation harness: S3 (synthetic-control conformal at T_pre >= 15) and W2 (WHO mdm_w/mdb_w at SNR >= 4)."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from census import inequality_monitoring_core as imc
from census import repairs110_core as r110

SEED = 20290110
LEVEL = 0.90


def run_s3(rng):
    R = 250
    N = 51  # 1 treated + 50 donors
    rows = []
    for T0 in (15, 20):
        T = T0 + 1
        for rho in (0.0, 0.3, 0.7):
            for eff in (0.0, -2.0):
                cov, bias = [], []
                for _ in range(R):
                    # Factor model + AR(1) idiosyncratic errors (standard Abadie/CWZ DGP)
                    lam = rng.normal(0.0, 1.0, (N, 2))
                    fac = rng.normal(0.0, 1.0, (T, 2))
                    eps = np.zeros((N, T))
                    sd_e = np.sqrt(1.0 - rho ** 2)
                    eps[:, 0] = rng.normal(0.0, 1.0, N)
                    for t in range(1, T):
                        eps[:, t] = rho * eps[:, t - 1] + rng.normal(0.0, sd_e, N)
                    M = 10.0 + lam @ fac.T + eps
                    M[0, T0] += eff
                    est, lo, hi = r110.synthetic_conformal_interval(M, 0, T0, T0, level=LEVEL)
                    cov.append(lo <= eff <= hi)
                    bias.append(est - eff)
                rows.append(dict(T_pre=T0, rho=rho, effect=eff,
                                 coverage=float(np.mean(cov)), bias=float(np.mean(bias))))
    return rows


def run_w2(rng):
    R = 400
    n_rep = 80
    rows_mdm, rows_mdb = [], []
    for G in (4, 6):
        pops = np.linspace(1000.0, 4000.0, G)
        for cv in (0.05, 0.15):
            for snr in (4.0, 8.0):
                # True group rates spaced so (max - min) / median_se == snr
                base = 0.15
                se_mid = base * cv
                spread = snr * se_mid
                r_true = np.linspace(base - spread / 2.0, base + spread / 2.0, G)
                r_true = np.clip(r_true, 0.02, 0.90)
                se_vec = r_true * cv
                # True mdm_w and mdb_w
                w = pops / pops.sum()
                mu_true = float(np.sum(w * r_true))
                true_mdm = float(np.sum(w * np.abs(r_true - mu_true)))
                true_mdb = float(np.sum(w * np.abs(r_true - np.min(r_true))))

                cov_m, cov_b = [], []
                for _ in range(R):
                    r_obs = np.clip(r_true + rng.normal(0.0, se_vec), 0.005, 0.99)
                    # 80 SDR replicates with Var = 4/80 sum (r_k - r_obs)^2 == se_vec^2 -> sd = se_vec / 2
                    r_reps = np.clip(r_obs[:, None] + rng.normal(0.0, se_vec[:, None] * 0.5, (G, n_rep)), 0.005, 0.99)
                    iv = r110.who_md_replicate_intervals(
                        r_obs[None, :], pops[None, :], r_reps[None, :, :], None, reference="best", level=LEVEL
                    )
                    m = iv["mdm_w"]
                    b = iv["mdb_w"]
                    cov_m.append(float(m["lower"][0]) <= true_mdm <= float(m["upper"][0]))
                    cov_b.append(float(b["lower"][0]) <= true_mdb <= float(b["upper"][0]))
                rows_mdm.append(dict(G=G, cv=cv, snr=snr, coverage=float(np.mean(cov_m))))
                rows_mdb.append(dict(G=G, cv=cv, snr=snr, coverage=float(np.mean(cov_b))))
    return rows_mdm, rows_mdb


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    print("Running S3 (synthetic-control conformal at T_pre >= 15)...", flush=True)
    s3 = run_s3(rng)
    print("Running W2 (WHO mdm_w / mdb_w at SNR >= 4)...", flush=True)
    w2_mdm, w2_mdb = run_w2(rng)
    elapsed = time.time() - t0

    s3_pass = all(r["coverage"] >= 0.86 for r in s3)
    w2_mdm_pass = all(r["coverage"] >= 0.86 for r in w2_mdm)
    w2_mdb_pass = all(r["coverage"] >= 0.86 for r in w2_mdb)

    summary = {
        "elapsed_seconds": round(elapsed, 2),
        "verdicts": {"S3": s3_pass, "W2-mdm": w2_mdm_pass, "W2-mdb": w2_mdb_pass},
        "S3": s3,
        "W2-mdm": w2_mdm,
        "W2-mdb": w2_mdb,
    }
    os.makedirs("docs/audits", exist_ok=True)
    with open("docs/audits/repairs110_validation.json", "w") as f:
        json.dump(summary, f, indent=2)

    lines = [
        "# Round 110 Validation Report — Synthetic-Control Conformal & WHO Mean-Difference SNR Gate",
        "",
        f"Runtime: {elapsed:.1f}s (`scripts/repairs110_validation.py`, seed `{SEED}`).",
        "",
        "## Verdicts",
        "",
        f"- **S3** (Synthetic-control conformal interval, `T_pre >= 15, N_donors >= 25`, 12 cells): **{'PASS' if s3_pass else 'FAIL'}** "
        f"(min coverage {min(r['coverage'] for r in s3):.3f}, max {max(r['coverage'] for r in s3):.3f})",
        f"- **W2-mdm** (WHO `mdm_w`, `SNR >= 4.0, max_cv <= 0.15`, 8 cells): **{'PASS' if w2_mdm_pass else 'FAIL'}** "
        f"(min coverage {min(r['coverage'] for r in w2_mdm):.3f}, max {max(r['coverage'] for r in w2_mdm):.3f})",
        f"- **W2-mdb** (WHO `mdb_w`, `SNR >= 4.0, max_cv <= 0.15`, 8 cells): **{'PASS' if w2_mdb_pass else 'FAIL'}** "
        f"(min coverage {min(r['coverage'] for r in w2_mdb):.3f}, max {max(r['coverage'] for r in w2_mdb):.3f})",
        "",
        "## S3",
        "| T_pre | rho | effect | coverage | bias |",
        "| ---: | ---: | ---: | ---: | ---: |",
        *[f"| {r['T_pre']} | {r['rho']} | {r['effect']} | {r['coverage']:.3f} | {r['bias']:+.4f} |" for r in s3],
        "",
        "## W2-mdm",
        "| G | cv | snr | coverage |",
        "| ---: | ---: | ---: | ---: |",
        *[f"| {r['G']} | {r['cv']} | {r['snr']} | {r['coverage']:.3f} |" for r in w2_mdm],
        "",
        "## W2-mdb",
        "| G | cv | snr | coverage |",
        "| ---: | ---: | ---: | ---: |",
        *[f"| {r['G']} | {r['cv']} | {r['snr']} | {r['coverage']:.3f} |" for r in w2_mdb],
        "",
    ]
    with open("docs/audits/repairs110_validation.md", "w") as f:
        f.write("\n".join(lines))
    print(json.dumps(summary["verdicts"], indent=2))
    print(f"Done in {elapsed:.1f}s.")


if __name__ == "__main__":
    main()
