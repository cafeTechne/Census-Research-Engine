# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 106 validation: third wave of exploratory-measure repairs (Rounds 37, 83, 85, 87, 91).

Usage: .venv/bin/python scripts/repairs106_validation.py [--smoke] [--workers N]
"""
import argparse
import hashlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
from scipy.special import expit  # noqa: E402

from census import designation_core as desc  # noqa: E402
from census import repairs106_core as rc  # noqa: E402

FROZEN = [
    "census/repairs106_core.py",
    "scripts/repairs106_validation.py",
    "docs/audits/repairs106_criterion.md",
]
OUT = ROOT / "docs/audits/repairs106_validation"


def _hashes():
    return {rel: hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()[:16] for rel in FROZEN}


# 1. H2c: proper per-measure nulls
def _eval_hom_measure(args):
    measure, K, n_s, draws, seed = args
    rng = np.random.default_rng(seed)
    n = K * n_s
    rej = 0
    for _ in range(draws):
        s = np.repeat(np.arange(K), n_s)
        e = rng.binomial(1, 0.4, n)
        p0 = 0.15 + 0.03 * s
        if measure == "rr":
            p1 = np.clip(p0 * 1.5, 0.01, 0.95)
        elif measure == "or":
            odds0 = p0 / (1.0 - p0)
            p1 = (1.8 * odds0) / (1.0 + 1.8 * odds0)
        else:
            p1 = np.clip(p0 + 0.10, 0.01, 0.95)
        y = rng.binomial(1, np.where(e == 1, p1, p0))
        w0 = rng.gamma(1.0, 10.0, n)
        g80 = rng.integers(0, 80, n)
        W = np.empty((n, 81), float); W[:, 0] = w0
        signs = rng.choice([-1.0, 1.0], size=(80, 80))
        W[:, 1:] = w0[:, None] * (1.0 + 0.5 * signs[g80])
        hom = rc.mh_replicate_homogeneity_f(y, e, s, W, np.arange(K))
        rej += int(hom[measure]["p_value"] < 0.10)
    return dict(measure=measure, K=K, n_per_stratum=n_s, size=rej / draws)


# 2. Q2c: PPV with rule re-selection
def _eval_ppv(args):
    N, A, rule, draws, seed = args
    rng = np.random.default_rng(seed)
    t = 0.20; t_arc = float(desc.arcsine(t))
    cov = 0; ok = 0
    for _ in range(draws):
        x = rng.standard_normal(N); X = np.column_stack([np.ones(N), x])
        n_eff = rng.uniform(40.0, 200.0, N); D = 1.0 / (4.0 * n_eff)
        theta = t_arc - 0.05 + 0.12 * x + np.sqrt(A) * rng.standard_normal(N)
        y_obs = np.clip(theta + np.sqrt(D) * rng.standard_normal(N), 0.01, np.pi / 2 - 0.01)
        p_obs = np.sin(y_obs) ** 2
        P_hat, _, _ = desc.q1_fh(p_obs, n_eff, X, t)
        S = desc.designate(rule, p_obs, n_eff, t, P=P_hat)
        if S.sum() < 5:
            continue
        true_ppv = float((theta[S] >= t_arc).mean())
        iv = rc.ppv_interval_reselect(rule, S, p_obs, n_eff, X, t, B=80, level=0.90, rng=rng)
        if np.isfinite(iv["ppv_lower"]):
            cov += int(iv["ppv_lower"] <= true_ppv <= iv["ppv_upper"])
            ok += 1
    return dict(N=N, A=A, rule=rule, Q2c_cov=cov / max(ok, 1))


# 3. E3: Ecologic / between-area reliability-corrected slope
def _eval_ecologic(args):
    J, n_j, beta_b, draws, seed = args
    rng = np.random.default_rng(seed)
    cov = 0; cov_naive = 0
    for _ in range(draws):
        mu_x = rng.normal(0.0, 0.5, J)
        mu_y = 1.0 + beta_b * mu_x + rng.normal(0.0, 0.4, J)
        # Individual draws within each of J small areas
        x_ind = mu_x[:, None] + rng.normal(0.0, 1.0, (J, n_j))
        y_ind = mu_y[:, None] + 0.3 * (x_ind - mu_x[:, None]) + rng.normal(0.0, 1.0, (J, n_j))
        xbar = x_ind.mean(1); ybar = y_ind.mean(1)
        vx = x_ind.var(1, ddof=1) / n_j
        r = rc.ecologic_corrected_slope(xbar, ybar, vx, level=0.90)
        cov += int(r["lower"] <= beta_b <= r["upper"])
        # Naive OLS for reference
        b_n = float(np.cov(xbar, ybar, ddof=1)[0, 1] / np.var(xbar, ddof=1))
        resid = ybar - (ybar.mean() + b_n * (xbar - xbar.mean()))
        se_n = float(np.sqrt(np.sum(resid ** 2) / ((J - 2) * np.sum((xbar - xbar.mean()) ** 2))))
        cov_naive += int(b_n - 1.645 * se_n <= beta_b <= b_n + 1.645 * se_n)
    return dict(J=J, n_j=n_j, beta_b=beta_b, E3_cov=cov / draws, naive_cov=cov_naive / draws)


# 4. C2: Lin's CCC jackknife
def _eval_ccc(args):
    n, rho, shift, scale, draws, seed = args
    rng = np.random.default_rng(seed)
    # True CCC for X ~ N(0, 1), Y = shift + scale * (rho * X + sqrt(1 - rho^2) * E)
    mu_x, mu_y = 0.0, shift
    var_x, var_y = 1.0, scale ** 2
    cov_xy = scale * rho
    true_ccc = float(2.0 * cov_xy / (var_x + var_y + (mu_x - mu_y) ** 2))
    cov = 0
    for _ in range(draws):
        x = rng.standard_normal(n)
        y = shift + scale * (rho * x + np.sqrt(1.0 - rho ** 2) * rng.standard_normal(n))
        r = rc.ccc_jackknife(x, y, level=0.90)
        cov += int(r["lower"] <= true_ccc <= r["upper"])
    return dict(n=n, true_ccc=round(true_ccc, 3), shift=shift, scale=scale, C2_cov=cov / draws)


# 5. M5: Parametric g-formula
def _eval_gformula(args):
    K, g, psi, draws, seed = args
    rng = np.random.default_rng(seed)
    n = 51
    tg = np.array([psi, psi + g, psi + g * 1.6])
    cov = np.zeros(3); bias = np.zeros(3)
    for _ in range(draws):
        L = np.zeros((n, K)); A = np.zeros((n, K)); Y = np.zeros((n, K))
        u = rng.standard_normal(n); e = rng.standard_normal(n) / np.sqrt(1 - 0.25)
        for t in range(K):
            if t == 0:
                L[:, 0] = rng.standard_normal(n)
            else:
                L[:, t] = 0.6 * L[:, t - 1] + g * A[:, t - 1] + rng.standard_normal(n)
                start = rng.random(n) < expit(-2.75 + 0.8 * L[:, t])
                A[:, t] = np.where(A[:, t - 1] == 1, 1, start.astype(float))
                e = 0.5 * e + rng.standard_normal(n)
            Y[:, t] = 10 + 0.2 * (t + 1) + psi * A[:, t] + L[:, t] + u + e + 0.5 * rng.standard_normal(n)
        unit = np.repeat(np.arange(n), K); year = np.tile(np.arange(1, K + 1), n)
        r = rc.gformula_jackknife(Y.ravel(), A.ravel(), L.ravel(), unit, year, K, level=0.90)
        lo, hi, est = map(np.asarray, (r["lower"], r["upper"], r["estimate"]))
        cov += (lo <= tg) & (tg <= hi); bias += (est - tg)
    return dict(K=K, feedback=g, psi=psi, cov=(cov / draws).tolist(), bias=(bias / draws).tolist())


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    t0 = time.time()

    d_hom = 60 if args.smoke else 1000
    d_ppv = 30 if args.smoke else 400
    d_eco = 80 if args.smoke else 1000
    d_ccc = 100 if args.smoke else 2000
    d_gf = 50 if args.smoke else 1000

    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        hom_res = list(ex.map(_eval_hom_measure, [
            (m, K, ns, d_hom, 106100 + i)
            for i, (m, K, ns) in enumerate([(m, K, ns) for m in ("rr", "or", "rd") for K in (3, 5) for ns in (300, 1000)])
        ]))
        ppv_res = list(ex.map(_eval_ppv, [
            (N, A, rl, d_ppv, 106200 + i)
            for i, (N, A, rl) in enumerate([(N, A, rl) for N in (200, 1000) for A in (0.005, 0.02) for rl in ("point", "prob80")])
        ]))
        eco_res = list(ex.map(_eval_ecologic, [
            (150, nj, bb, d_eco, 106300 + i)
            for i, (nj, bb) in enumerate([(nj, bb) for nj in (20, 40) for bb in (0.0, 1.0)])
        ]))
        ccc_res = list(ex.map(_eval_ccc, [
            (n, rh, sh, sc, d_ccc, 106400 + i)
            for i, (n, rh, sh, sc) in enumerate([
                (50, 0.6, 0.3, 1.2), (50, 0.9, 0.2, 1.1), (50, 0.98, 0.1, 1.05),
                (145, 0.6, 0.3, 1.2), (145, 0.9, 0.2, 1.1), (145, 0.98, 0.1, 1.05),
            ])
        ]))
        gf_res = list(ex.map(_eval_gformula, [
            (K, g, psi, d_gf, 106500 + i)
            for i, (K, g, psi) in enumerate([(K, g, psi) for K in (12, 18) for g in (0.0, 0.5, 1.0) for psi in (0.0, -2.0)])
        ]))

    outcomes = {
        "H2c_all": max(r["size"] for r in hom_res) <= 0.13,
        "Q2c_all": min(r["Q2c_cov"] for r in ppv_res) >= 0.86,
        "E3_all": min(r["E3_cov"] for r in eco_res) >= 0.86,
        "C2_all": min(r["C2_cov"] for r in ccc_res) >= 0.86,
        "M5_all": min(min(r["cov"]) for r in gf_res) >= 0.86,
    }
    report = dict(
        smoke=args.smoke,
        elapsed_s=round(time.time() - t0, 1),
        frozen_sha256=_hashes(),
        outcomes=outcomes,
        homogeneity=hom_res,
        ppv=ppv_res,
        ecologic=eco_res,
        ccc=ccc_res,
        gformula=gf_res,
    )
    if not args.smoke:
        OUT.with_suffix(".json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        lines = [
            "# Round 106: third-wave exploratory-measure repairs validation",
            "",
            f"Elapsed: {report['elapsed_s']}s. Frozen SHA-256: `{report['frozen_sha256']}`. 90% intervals (pass ≥ .86; H2c size ≤ .13). Author self-review, not independent.",
            "",
            "## Outcomes",
            "",
            "| Candidate | Outcome |",
            "| :--- | :--- |",
            *[f"| `{k}` | {'**pass**' if v else 'fail'} |" for k, v in outcomes.items()],
            "", "## PUMS replicate Wald homogeneity (H2c: Hotelling F, exact per-measure nulls)", "",
            "| Measure | K | n/stratum | Size (.10) |",
            "| :--- | ---: | ---: | ---: |",
            *[f"| {r['measure']} | {r['K']} | {r['n_per_stratum']} | {r['size']:.3f} |" for r in hom_res],
            "", "## Designation PPV predictive interval (Q2c: FH bootstrap with rule re-selection)", "",
            "| N | A | Rule | Q2c coverage |",
            "| ---: | ---: | :--- | ---: |",
            *[f"| {r['N']} | {r['A']} | {r['rule']} | {r['Q2c_cov']:.3f} |" for r in ppv_res],
            "", "## Ecologic / between-area slope (E3: Croon/Fuller reliability correction)", "",
            "| J | n_j | beta_b | E3 coverage | Naive OLS coverage |",
            "| ---: | ---: | ---: | ---: | ---: |",
            *[f"| {r['J']} | {r['n_j']} | {r['beta_b']} | {r['E3_cov']:.3f} | {r['naive_cov']:.3f} |" for r in eco_res],
            "", "## Lin's CCC (C2: Fisher-z jackknife)", "",
            "| n | True CCC | Shift | Scale | C2 coverage |",
            "| ---: | ---: | ---: | ---: | ---: |",
            *[f"| {r['n']} | {r['true_ccc']} | {r['shift']} | {r['scale']} | {r['C2_cov']:.3f} |" for r in ccc_res],
            "", "## Parametric g-formula (M5: Hernán & Robins ch. 21 + cluster jackknife)", "",
            "| K | Feedback | psi | M5 cov (d1/d2/d3) | M5 bias (d1/d2/d3) |",
            "| ---: | ---: | ---: | :--- | :--- |",
            *[f"| {r['K']} | {r['feedback']} | {r['psi']} | "
              f"{r['cov'][0]:.3f}/{r['cov'][1]:.3f}/{r['cov'][2]:.3f} | "
              f"{r['bias'][0]:+.3f}/{r['bias'][1]:+.3f}/{r['bias'][2]:+.3f} |" for r in gf_res],
        ]
        OUT.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(dict(elapsed_s=report["elapsed_s"], outcomes=outcomes), indent=2))


if __name__ == "__main__":
    main()
