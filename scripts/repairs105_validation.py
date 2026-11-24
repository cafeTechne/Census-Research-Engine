# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 105 validation: second wave of exploratory-measure repairs (Rounds 83, 85, 86, 91, 98).

Usage: .venv/bin/python scripts/repairs105_validation.py [--smoke] [--workers N]
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

from census import bias_analysis_core as bac  # noqa: E402
from census import designation_core as desc  # noqa: E402
from census import repairs105_core as rc  # noqa: E402

FROZEN = [
    "census/repairs105_core.py",
    "scripts/repairs105_validation.py",
    "docs/audits/repairs105_criterion.md",
]
OUT = ROOT / "docs/audits/repairs105_validation"


def _hashes():
    return {rel: hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()[:16] for rel in FROZEN}


# 1. Continuous RDD R1b
def _eval_rdd(args):
    n, c2, c3, draws, seed = args
    rng = np.random.default_rng(seed)
    tau = 0.5
    cov = 0
    for _ in range(draws):
        x = rng.uniform(-1.0, 1.0, n)
        mu = 0.5 * x + c2 * (x ** 2) + c3 * (x ** 3) + tau * (x >= 0.0)
        y = mu + rng.normal(0.0, 0.5, n)
        r = rc.rdd_cer(x, y, 0.0, level=0.90)
        cov += int(r["robust_lower"] <= tau <= r["robust_upper"])
    return dict(n=n, c2=c2, c3=c3, R1b_cov=cov / draws)


# 2. PUMS replicate Wald homogeneity H2b
def _eval_homogeneity(args):
    K, n_s, draws, seed = args
    rng = np.random.default_rng(seed)
    n = K * n_s
    rej = {"rr": 0, "or": 0, "rd": 0}
    for _ in range(draws):
        s = np.repeat(np.arange(K), n_s)
        e = rng.binomial(1, 0.4, n)
        p0 = 0.15 + 0.03 * s
        p = np.where(e == 1, np.clip(p0 * 1.5, 0.01, 0.95), p0)
        y = rng.binomial(1, p)
        # Unequal weights (CV ~ 1) + 80 SDR-like replicate weights
        w0 = rng.gamma(1.0, 10.0, n)
        # Assign 80 random groups for balanced SDR perturbation (4/80 sum (w_r - w_0)^2 = var)
        g80 = rng.integers(0, 80, n)
        W = np.empty((n, 81), float)
        W[:, 0] = w0
        # Hadamard/Rademacher-like SDR weights: each replicate scales a random half by 1 +/- 0.5
        signs = rng.choice([-1.0, 1.0], size=(80, 80))
        W[:, 1:] = w0[:, None] * (1.0 + 0.5 * signs[g80])
        hom = rc.mh_replicate_homogeneity_f(y, e, s, W, np.arange(K))
        for m in ("rr", "or", "rd"):
            rej[m] += int(hom[m]["p_value"] < 0.10)
    return dict(K=K, n_per_stratum=n_s, rr_size=rej["rr"] / draws, or_size=rej["or"] / draws, rd_size=rej["rd"] / draws)


# 3. Designation PPV Q2b
def _eval_ppv(args):
    N, A, rule, draws, seed = args
    rng = np.random.default_rng(seed)
    t = 0.20; t_arc = float(desc.arcsine(t))
    cov = 0; ok = 0
    for _ in range(draws):
        x = rng.standard_normal(N)
        X = np.column_stack([np.ones(N), x])
        n_eff = rng.uniform(40.0, 200.0, N)
        D = 1.0 / (4.0 * n_eff)
        theta = t_arc - 0.05 + 0.12 * x + np.sqrt(A) * rng.standard_normal(N)
        y_obs = np.clip(theta + np.sqrt(D) * rng.standard_normal(N), 0.01, np.pi / 2 - 0.01)
        p_obs = np.sin(y_obs) ** 2
        P_hat, _, _ = desc.q1_fh(p_obs, n_eff, X, t)
        S = desc.designate(rule, p_obs, n_eff, t, P=P_hat)
        if S.sum() < 5:
            continue
        true_ppv = float((theta[S] >= t_arc).mean())
        iv = rc.ppv_interval_bootstrap(S, p_obs, n_eff, X, t, B=80, level=0.90, rng=rng)
        cov += int(iv["ppv_lower"] <= true_ppv <= iv["ppv_upper"])
        ok += 1
    return dict(N=N, A=A, rule=rule, Q2b_cov=cov / max(ok, 1), ok=ok)


# 4. Probabilistic misclassification M1b
def _eval_misclass(args):
    kind, true_rr, diff, draws, seed = args
    rng = np.random.default_rng(seed)
    N = 2000; p_e = 0.4; p0 = 0.15; p1 = p0 * true_rr
    se_p = ((0.85, 0.04), (0.80, 0.04)) if diff else (0.85, 0.04)
    sp_p = ((0.92, 0.03), (0.90, 0.03)) if diff else (0.92, 0.03)
    true_or = (p1 / (1.0 - p1)) / (p0 / (1.0 - p0))
    cov_rr = 0; cov_or = 0; ok = 0
    for _ in range(draws):
        # Draw true Se, Sp from the prior
        if diff:
            se_t = np.array([rng.beta(*bac.beta_params(*pr)) for pr in se_p])
            sp_t = np.array([rng.beta(*bac.beta_params(*pr)) for pr in sp_p])
        else:
            s_ = rng.beta(*bac.beta_params(*se_p)); q_ = rng.beta(*bac.beta_params(*sp_p))
            se_t = np.array([s_, s_]); sp_t = np.array([q_, q_])
        n1 = int(N * p_e); n0 = N - n1
        A = rng.binomial(n1, p1); B = n1 - A
        C = rng.binomial(n0, p0); D = n0 - C
        if kind == "outcome":
            a_obs = rng.binomial(A, se_t[0]) + rng.binomial(B, 1.0 - sp_t[0])
            b_obs = n1 - a_obs
            c_obs = rng.binomial(C, se_t[1]) + rng.binomial(D, 1.0 - sp_t[1])
            d_obs = n0 - c_obs
        else:
            a_obs = rng.binomial(A, se_t[0]) + rng.binomial(C, 1.0 - sp_t[0])
            c_obs = (A + C) - a_obs
            b_obs = rng.binomial(B, se_t[1]) + rng.binomial(D, 1.0 - sp_t[1])
            d_obs = (B + D) - b_obs
        res = rc.probabilistic_propagated(a_obs, b_obs, c_obs, d_obs, se_p, sp_p, kind=kind,
                                          draws=1500, level=0.90, rng=rng, differential=diff)
        if np.isfinite(res["rr"]["lower"]):
            cov_rr += int(res["rr"]["lower"] <= true_rr <= res["rr"]["upper"])
            cov_or += int(res["or"]["lower"] <= true_or <= res["or"]["upper"])
            ok += 1
    return dict(kind=kind, true_rr=true_rr, differential=diff, RR_cov=cov_rr / max(ok, 1), OR_cov=cov_or / max(ok, 1))


# 5. MSM M4 (Firth logit + L0 + jackknife)
def _eval_msm(args):
    K, g, psi, draws, seed = args
    rng = np.random.default_rng(seed)
    n = 51
    tg = np.array([psi, psi + g, psi + g * 1.6])
    cov = np.zeros(3); bias = np.zeros(3); ok = 0
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
        try:
            r = rc.msm_firth_jackknife(Y.ravel(), A.ravel(), L.ravel(), unit, year, K, truncate=False, level=0.90)
        except (ValueError, np.linalg.LinAlgError):
            continue
        lo, hi, est = map(np.asarray, (r["lower"], r["upper"], r["estimate"]))
        cov += (lo <= tg) & (tg <= hi); bias += (est - tg); ok += 1
    return dict(K=K, feedback=g, psi=psi, cov=(cov / max(ok, 1)).tolist(),
                bias=(bias / max(ok, 1)).tolist(), ok=ok)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    t0 = time.time()

    d_rdd = 60 if args.smoke else 1000
    d_hom = 60 if args.smoke else 1000
    d_ppv = 30 if args.smoke else 400
    d_mis = 60 if args.smoke else 1000
    d_msm = 30 if args.smoke else 500

    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        rdd_res = list(ex.map(_eval_rdd, [
            (n, c2, c3, d_rdd, 105100 + i)
            for i, (n, c2, c3) in enumerate([(n, c2, c3) for n in (2000, 10000) for c2 in (0.0, 2.0) for c3 in (0.0, 3.0)])
        ]))
        hom_res = list(ex.map(_eval_homogeneity, [
            (K, ns, d_hom, 105200 + i)
            for i, (K, ns) in enumerate([(K, ns) for K in (3, 5) for ns in (300, 1000)])
        ]))
        ppv_res = list(ex.map(_eval_ppv, [
            (N, A, rl, d_ppv, 105300 + i)
            for i, (N, A, rl) in enumerate([(N, A, rl) for N in (200, 1000) for A in (0.005, 0.02) for rl in ("point", "prob80")])
        ]))
        mis_res = list(ex.map(_eval_misclass, [
            (kd, rr, df, d_mis, 105400 + i)
            for i, (kd, rr, df) in enumerate([
                ("outcome", 1.0, False), ("outcome", 1.5, False),
                ("outcome", 1.5, True), ("exposure", 1.0, False), ("exposure", 1.5, False),
            ])
        ]))
        msm_res = list(ex.map(_eval_msm, [
            (K, g, psi, d_msm, 105500 + i)
            for i, (K, g, psi) in enumerate([(K, g, psi) for K in (12, 18) for g in (0.0, 0.5, 1.0) for psi in (0.0, -2.0)])
        ]))

    outcomes = {
        "R1b_all": min(r["R1b_cov"] for r in rdd_res) >= 0.86,
        "H2b_all": max(max(r["rr_size"], r["or_size"], r["rd_size"]) for r in hom_res) <= 0.13,
        "Q2b_all": min(r["Q2b_cov"] for r in ppv_res) >= 0.86,
        "M1b_all": min(min(r["RR_cov"], r["OR_cov"]) for r in mis_res) >= 0.86,
        "M4_all": min(min(r["cov"]) for r in msm_res) >= 0.86,
    }
    report = dict(
        smoke=args.smoke,
        elapsed_s=round(time.time() - t0, 1),
        frozen_sha256=_hashes(),
        outcomes=outcomes,
        rdd=rdd_res,
        homogeneity=hom_res,
        ppv=ppv_res,
        misclass=mis_res,
        msm=msm_res,
    )
    if not args.smoke:
        OUT.with_suffix(".json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        lines = [
            "# Round 105: second-wave exploratory-measure repairs validation",
            "",
            f"Elapsed: {report['elapsed_s']}s. Frozen SHA-256: `{report['frozen_sha256']}`. 90% intervals (pass ≥ .86; H2b size ≤ .13). Author self-review, not independent.",
            "",
            "## Outcomes",
            "",
            "| Candidate | Outcome |",
            "| :--- | :--- |",
            *[f"| `{k}` | {'**pass**' if v else 'fail'} |" for k, v in outcomes.items()],
            "", "## Continuous RDD (R1b: CER bandwidth)", "",
            "| n | c2 | c3 | R1b coverage |",
            "| ---: | ---: | ---: | ---: |",
            *[f"| {r['n']} | {r['c2']} | {r['c3']} | {r['R1b_cov']:.3f} |" for r in rdd_res],
            "", "## PUMS replicate Wald homogeneity (H2b: Hotelling F)", "",
            "| K | n/stratum | RR size | OR size | RD size |",
            "| ---: | ---: | ---: | ---: | ---: |",
            *[f"| {r['K']} | {r['n_per_stratum']} | {r['rr_size']:.3f} | {r['or_size']:.3f} | {r['rd_size']:.3f} |" for r in hom_res],
            "", "## Designation PPV predictive interval (Q2b: FH parametric bootstrap)", "",
            "| N | A | Rule | Q2b coverage |",
            "| ---: | ---: | :--- | ---: |",
            *[f"| {r['N']} | {r['A']} | {r['rule']} | {r['Q2b_cov']:.3f} |" for r in ppv_res],
            "", "## Probabilistic misclassification (M1b: propagated sampling)", "",
            "| Kind | True RR | Diff | RR cov | OR cov |",
            "| :--- | ---: | :--- | ---: | ---: |",
            *[f"| {r['kind']} | {r['true_rr']} | {r['differential']} | {r['RR_cov']:.3f} | {r['OR_cov']:.3f} |" for r in mis_res],
            "", "## IP-weighted MSM (M4: Firth logit + L0 + cluster jackknife)", "",
            "| K | Feedback | psi | M4 cov (d1/d2/d3) | M4 bias (d1/d2/d3) |",
            "| ---: | ---: | ---: | :--- | :--- |",
            *[f"| {r['K']} | {r['feedback']} | {r['psi']} | "
              f"{r['cov'][0]:.3f}/{r['cov'][1]:.3f}/{r['cov'][2]:.3f} | "
              f"{r['bias'][0]:+.3f}/{r['bias'][1]:+.3f}/{r['bias'][2]:+.3f} |" for r in msm_res],
        ]
        OUT.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(dict(elapsed_s=report["elapsed_s"], outcomes=outcomes), indent=2))


if __name__ == "__main__":
    main()
