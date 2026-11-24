#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 111 out-of-DGP adversarial stress-test audit across 8 core confirmed methods.

Tests whether confirmed methods maintain nominal 90% coverage (>= .86) or nominal .10 size (<= .13)
under realistic departures from their validation DGPs: heavy-tailed t_3 errors, heteroscedasticity,
skewed lognormal distributions, unbalanced cluster sizes, negative-binomial overdispersion, extreme
survey weight CV, and mild nonlinearity.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from census import repairs104_core as r104
from census import repairs105_core as r105
from census import repairs106_core as r106
from census import repairs108_core as r108
from census import repairs109_core as r109
from census import rdd_core as rddc

SEED = 20291111
LEVEL = 0.90


def stress_meta_t3(rng):
    """Meta-analysis P2 (NNF PI), R2 (KH meta-reg), E2 (Egger) under heavy-tailed t_3 random effects (k = 12)."""
    R = 300
    k = 12
    cov_pi, cov_reg, rej_eg = [], [], []
    for _ in range(R):
        v = rng.uniform(0.01, 0.04, k)
        x = np.linspace(-1.0, 1.0, k)
        tau = 0.25
        # t_3 random effects scaled to variance tau^2 (t_3 has var = 3 -> divide by sqrt(3))
        re = rng.standard_t(3, k) / np.sqrt(3.0) * tau
        y = 0.5 + 0.4 * x + re + rng.normal(0.0, np.sqrt(v))
        # New study for PI (using x=0, null slope case for PI)
        y_null = 0.5 + re + rng.normal(0.0, np.sqrt(v))
        theta_new = 0.5 + rng.standard_t(3) / np.sqrt(3.0) * tau
        pi_lo, pi_hi = r104.prediction_interval_nnf(y_null, v, level=LEVEL, rng=rng)
        cov_pi.append(pi_lo <= theta_new <= pi_hi)

        reg = r104.meta_regression_trunc(y, v, x, level=LEVEL)
        cov_reg.append(float(reg["lower"][1]) <= 0.4 <= float(reg["upper"][1]))

        eg = r104.egger_re(y_null, v)
        rej_eg.append(eg["p"] <= 0.10)
    return [
        dict(method="P2_meta_PI", stress="t3_random_effects_k12", metric="coverage", value=float(np.mean(cov_pi)), holds=bool(np.mean(cov_pi) >= 0.86)),
        dict(method="R2_meta_reg", stress="t3_random_effects_k12", metric="coverage", value=float(np.mean(cov_reg)), holds=bool(np.mean(cov_reg) >= 0.86)),
        dict(method="E2_egger_re", stress="t3_random_effects_k12", metric="size", value=float(np.mean(rej_eg)), holds=bool(np.mean(rej_eg) <= 0.13)),
    ]


def stress_gformula(rng):
    """Parametric g-formula (M5) under (a) heavy-tailed t_3 errors and (b) mild quadratic L^2 misspecification."""
    R = 250
    G, K = 51, 12
    rows = []
    for mode in ("t3_errors", "mild_quadratic_L"):
        cov = np.zeros(3)
        for _ in range(R):
            unit = np.repeat(np.arange(G), K)
            year = np.tile(np.arange(1, K + 1), G)
            L = np.zeros((G, K)); A = np.zeros((G, K)); Y = np.zeros((G, K))
            u_eff = rng.normal(0.0, 0.5, G)
            L[:, 0] = rng.normal(0.0, 1.0, G)
            for t in range(1, K):
                err_l = (rng.standard_t(3, G) / np.sqrt(3.0) * 0.7) if mode == "t3_errors" else rng.normal(0.0, 0.7, G)
                L[:, t] = 0.5 * L[:, t - 1] + 0.5 * A[:, t - 1] + err_l
                if t >= 2:
                    prob = 1.0 / (1.0 + np.exp(-(-2.2 + 0.5 * L[:, t])))
                    start = (A[:, t - 1] == 0) & (rng.random(G) < prob)
                    A[:, t] = np.where((A[:, t - 1] == 1) | start, 1.0, 0.0)
            for t in range(K):
                err_y = (rng.standard_t(3, G) / np.sqrt(3.0) * 0.6) if mode == "t3_errors" else rng.normal(0.0, 0.6, G)
                quad = 0.15 * (L[:, t] ** 2 - 1.0) if mode == "mild_quadratic_L" else 0.0
                Y[:, t] = 10.0 + u_eff + 0.1 * t - 2.0 * A[:, t] + 0.8 * L[:, t] + quad + err_y
            # Analytical truth under linear model (under mild_quadratic_L, E[0.15(L^2-1)|do(A)] shifts slightly for d>=2)
            truth = np.array([-2.0, -2.0 + 0.8 * 0.5, -2.0 + 0.8 * (0.5 + 0.25)])
            if mode == "mild_quadratic_L":
                # True shift in E[L^2] from delta_L = 0, 0.5, 0.75 is delta_L^2
                truth = truth + 0.15 * np.array([0.0, 0.5 ** 2, 0.75 ** 2])
            res = r106.gformula_jackknife(Y.reshape(-1), A.reshape(-1), L.reshape(-1), unit, year, K, level=LEVEL, report=3)
            cov += (np.asarray(res["lower"]) <= truth) & (truth <= np.asarray(res["upper"]))
        cov /= R
        rows.append(dict(method="M5_gformula", stress=mode, metric="min_coverage_d1_3",
                         value=float(cov.min()), holds=bool(cov.min() >= 0.86)))
    return rows


def stress_rdd(rng):
    """Continuous RDD (R1b CCT CER) under t_3 errors and heteroscedastic variance jump (3x SD right of cutoff)."""
    R = 300
    n = 3000
    cov = []
    for _ in range(R):
        x = rng.uniform(-1.0, 1.0, n)
        sd = np.where(x >= 0, 0.9, 0.3)
        err = rng.standard_t(3, n) / np.sqrt(3.0) * sd
        y = 1.0 + 0.8 * (x >= 0) + 0.6 * x - 0.5 * x ** 2 + err
        h = float(rddc.ik_bandwidth(x, y, 0.0) * (n ** (-1.0 / 20.0)))
        res = rddc.rdd(x, y, 0.0, h=h, level=LEVEL)
        cov.append(res["robust_lower"] <= 0.8 <= res["robust_upper"])
    return [dict(method="R1b_rdd_continuous", stress="t3_and_3x_heteroscedastic_jump", metric="coverage",
                 value=float(np.mean(cov)), holds=bool(np.mean(cov) >= 0.86))]


def stress_ccc(rng):
    """Lin's CCC Fisher-z jackknife (C2) under skewed lognormal data (n = 80)."""
    R = 300
    n = 80
    # Compute true CCC by large-sample Monte Carlo
    big_x = rng.lognormal(0.0, 0.6, 200000)
    big_y = big_x + rng.normal(0.1, 0.4, 200000)
    ccc_true = r106._lin_ccc(big_x, big_y)
    cov = []
    for _ in range(R):
        x = rng.lognormal(0.0, 0.6, n)
        y = x + rng.normal(0.1, 0.4, n)
        res = r106.ccc_jackknife(x, y, level=LEVEL)
        cov.append(res["lower"] <= ccc_true <= res["upper"])
    return [dict(method="C2_lin_ccc", stress="skewed_lognormal_n80", metric="coverage",
                 value=float(np.mean(cov)), holds=bool(np.mean(cov) >= 0.86))]


def stress_ecologic_fuller(rng):
    """Fuller alpha=4 ecologic slope (E3d) under unbalanced area sizes (50..200) and t_3 errors."""
    R = 300
    J = 80
    beta_true = 1.5
    cov = []
    for _ in range(R):
        ns = rng.integers(50, 201, J)
        mu_x = rng.normal(0.0, np.sqrt(0.10), J)
        mu_y = beta_true * mu_x + rng.standard_t(3, J) / np.sqrt(3.0) * 0.5
        ax, ay, vx = np.empty(J), np.empty(J), np.empty(J)
        for j in range(J):
            xj = mu_x[j] + rng.normal(0.0, np.sqrt(0.90), ns[j])
            yj = mu_y[j] + 0.5 * (xj - mu_x[j]) + rng.standard_t(3, ns[j]) / np.sqrt(3.0)
            ax[j] = xj.mean(); ay[j] = yj.mean(); vx[j] = xj.var(ddof=1) / ns[j]
        res = r109.ecologic_fuller_slope(ax, ay, vx, alpha=4.0, level=LEVEL)
        cov.append(res["lower"] <= beta_true <= res["upper"])
    return [dict(method="E3d_ecologic_fuller", stress="unbalanced_nj_50_200_and_t3", metric="coverage",
                 value=float(np.mean(cov)), holds=bool(np.mean(cov) >= 0.86))]


def stress_joinpoint_overdispersed(rng):
    """Joinpoint AAPC bootstrap-t (J3c) under negative-binomial overdispersion (Var = 2.5 * mu)."""
    R = 250
    T = 18
    x = np.arange(T, dtype=float)
    log_mu = -0.03 * x + 0.06 * np.maximum(x - 9, 0.0)
    mu = 400.0 * np.exp(log_mu)
    true_aapc = float(100.0 * (np.exp((log_mu[-1] - log_mu[0]) / (T - 1)) - 1.0))
    cov = []
    for _ in range(R):
        # Gamma-Poisson mixture with Var = mu + mu^2 / r; Var = 2.5 * mu => r = mu / 1.5
        lam = rng.gamma(shape=mu / 1.5, scale=1.5)
        d = np.maximum(rng.poisson(lam), 1)
        y = np.log(d / 100000.0)
        res = r109.joinpoint_aapc_bootstrap_t(x, y, d.astype(float), k=1, B=120, level=LEVEL, rng=rng)
        cov.append(res["lower"] <= true_aapc <= res["upper"])
    return [dict(method="J3c_joinpoint_aapc", stress="negbin_overdispersed_2.5x", metric="coverage",
                 value=float(np.mean(cov)), holds=bool(np.mean(cov) >= 0.86))]


def stress_pums_hotelling_heavy_weights(rng):
    """PUMS Hotelling F homogeneity (H2d) under extreme survey weight CV = 1.2 (K=4, n=600)."""
    R = 300
    K, n_s = 4, 600
    N = K * n_s
    p0 = np.linspace(0.15, 0.35, K)
    p1 = np.clip(p0 * 1.5, 0.02, 0.98)
    rej = 0
    for _ in range(R):
        s = np.repeat(np.arange(K), n_s)
        e = rng.binomial(1, 0.45, N)
        y = rng.binomial(1, np.where(e == 1, p1[s], p0[s]))
        # Gamma(shape=0.7) has CV = 1 / sqrt(0.7) ~= 1.20
        w0 = rng.gamma(0.7, 1.0 / 0.7, N)
        half = rng.choice([-0.5, 0.5], size=(80, N))
        W = np.vstack([w0[None, :], w0[None, :] * (1.0 + half)]).T
        res = r105.mh_replicate_homogeneity_f(y, e, s, W, list(range(K)))
        if res["rr"]["p_value"] <= 0.10:
            rej += 1
    return [dict(method="H2d_pums_hotelling_f", stress="extreme_weight_cv_1.2", metric="size",
                 value=float(rej / R), holds=bool(rej / R <= 0.13))]


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    results = []
    for fn in (
        stress_meta_t3,
        stress_gformula,
        stress_rdd,
        stress_ccc,
        stress_ecologic_fuller,
        stress_joinpoint_overdispersed,
        stress_pums_hotelling_heavy_weights,
    ):
        print(f"Running {fn.__name__}...", flush=True)
        results.extend(fn(rng))
    elapsed = time.time() - t0

    os.makedirs("docs/audits", exist_ok=True)
    payload = {"elapsed_seconds": round(elapsed, 2), "seed": SEED, "results": results}
    with open("docs/audits/confirmed_stress_audit.json", "w") as f:
        json.dump(payload, f, indent=2)

    lines = [
        "# Round 111 Adversarial Out-of-DGP Stress-Test Audit of Confirmed Methods",
        "",
        f"Runtime: {elapsed:.1f}s (`scripts/confirmed_stress_audit.py`, seed `{SEED}`).",
        "",
        "Checks whether confirmed methods hold nominal 90% coverage (≥ .86) or nominal .10 size (≤ .13) "
        "under deliberate departures from their validation DGPs.",
        "",
        "| Method | Stress Departure | Metric | Observed | Holds? |",
        "| :--- | :--- | :--- | ---: | :--- |",
        *[f"| `{r['method']}` | `{r['stress']}` | {r['metric']} | {r['value']:.3f} | {'**YES**' if r['holds'] else '**NO**'} |"
          for r in results],
        "",
    ]
    with open("docs/audits/confirmed_stress_audit.md", "w") as f:
        f.write("\n".join(lines))
    for r in results:
        print(f"  {r['method']:24s} {r['stress']:32s} {r['metric']:18s} = {r['value']:.3f}  holds={r['holds']}")
    print(f"Done in {elapsed:.1f}s.")


if __name__ == "__main__":
    main()
