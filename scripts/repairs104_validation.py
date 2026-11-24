# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 104 validation: candidate repairs for exploratory measures (Rounds 91, 94, 96, 99, 102).

Usage: .venv/bin/python scripts/repairs104_validation.py [--smoke] [--workers N]
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

from census import disease_mapping_core as dmc  # noqa: E402
from census import inequality_monitoring_core as imc  # noqa: E402
from census import repairs104_core as rc  # noqa: E402

FROZEN = [
    "census/repairs104_core.py",
    "scripts/repairs104_validation.py",
    "docs/audits/repairs104_criterion.md",
]
OUT = ROOT / "docs/audits/repairs104_validation"


def _hashes():
    return {rel: hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()[:16] for rel in FROZEN}


# 1. Meta-analysis (P2, R2, E2)
def _eval_meta_pool(args):
    k, i2, draws, seed = args
    rng = np.random.default_rng(seed)
    v_base = np.geomspace(0.01, 0.10, k)
    s2_typ = (k - 1) * np.sum(1.0 / v_base) / (np.sum(1.0 / v_base) ** 2 - np.sum(1.0 / v_base ** 2))
    tau2 = 0.0 if i2 == 0.0 else s2_typ * i2 / (1.0 - i2)
    cov_p2 = 0; rej_e2 = 0
    for d in range(draws):
        theta = rng.normal(0.0, np.sqrt(tau2), size=k)
        y = theta + rng.normal(0.0, np.sqrt(v_base))
        theta_new = rng.normal(0.0, np.sqrt(tau2))
        lo, hi = rc.prediction_interval_nnf(y, v_base, level=0.90, draws=1000, rng=rng)
        cov_p2 += int(lo <= theta_new <= hi)
        e2 = rc.egger_re(y, v_base)
        rej_e2 += int(e2["p"] < 0.10)
    return dict(k=k, I2=i2, P2=cov_p2 / draws, E2_rej=rej_e2 / draws)


def _eval_meta_reg(args):
    k, i2, beta, draws, seed = args
    rng = np.random.default_rng(seed)
    v_base = np.geomspace(0.01, 0.10, k)
    s2_typ = (k - 1) * np.sum(1.0 / v_base) / (np.sum(1.0 / v_base) ** 2 - np.sum(1.0 / v_base ** 2))
    tau2 = 0.0 if i2 == 0.0 else s2_typ * i2 / (1.0 - i2)
    cov_r2 = 0
    for _ in range(draws):
        x = rng.standard_normal(k)
        y = beta * x + rng.normal(0.0, np.sqrt(tau2 + v_base))
        r = rc.meta_regression_trunc(y, v_base, x, level=0.90)
        cov_r2 += int(r["lower"][1] <= beta <= r["upper"][1])
    return dict(k=k, I2=i2, beta=beta, R2=cov_r2 / draws)


# 2. Matching M1b-ATT
def _eval_matching(args):
    n, strength, het, draws, seed = args
    rng = np.random.default_rng(seed)
    cov = 0
    for _ in range(draws):
        X = rng.standard_normal((n, 2))
        p = expit(strength * (0.7 * X[:, 0] + 0.7 * X[:, 1]))
        T = (rng.random(n) < p).astype(int)
        if T.sum() < 10 or (1 - T).sum() < 10:
            continue
        tau_i = 1.0 + (0.6 * X[:, 0] if het else np.zeros(n))
        y = 1.0 + 0.8 * X[:, 0] - 0.5 * X[:, 1] + tau_i * T + rng.standard_normal(n)
        true_att = float(tau_i[T == 1].mean())
        r = rc.nn_match_att_t(y, T, X, M=4, level=0.90)
        cov += int(r["lower"] <= true_att <= r["upper"])
    return dict(N=n, strength=strength, het=het, M1b_ATT=cov / draws)


# 3. BYM2 B3 (on an 83-county connected grid matching Michigan's county count)
def _grid_edges(rows, cols):
    edges = []
    for r in range(rows):
        for c in range(cols):
            i = r * cols + c
            if c + 1 < cols:
                edges.append((i, i + 1))
            if r + 1 < rows:
                edges.append((i, i + cols))
    return edges


def _eval_bym2(args):
    phi, sigma, med_e, draws, seed = args
    rng = np.random.default_rng(seed)
    edges = _grid_edges(9, 9)  # 81 connected counties (~MI 83)
    n = 81
    eigen = dmc.scaled_icar_eigen(n, edges)
    E = med_e * np.exp(rng.normal(0.0, 0.5, size=n))
    area_cov = np.zeros(n)
    for _ in range(draws):
        b = dmc.simulate_field(rng, eigen, sigma, phi)
        eta = b
        y = rng.poisson(E * np.exp(eta))
        fit = rc.bym2_pc(y, E, eigen=eigen, level=0.90)
        rr = np.exp(eta)
        area_cov += (fit["lower"] <= rr) & (rr <= fit["upper"])
    area_cov /= draws
    return dict(phi=phi, sigma=sigma, median_E=med_e,
                mean_cov=float(area_cov.mean()), share_ge_80=float((area_cov >= 0.80).mean()))


# 4. MSM M3
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
            r = rc.msm_jackknife(Y.ravel(), A.ravel(), L.ravel(), unit, year, K, truncate=False, level=0.90)
        except (ValueError, np.linalg.LinAlgError):
            continue
        lo, hi, est = map(np.asarray, (r["lower"], r["upper"], r["estimate"]))
        cov += (lo <= tg) & (tg <= hi); bias += (est - tg); ok += 1
    return dict(K=K, feedback=g, psi=psi, cov=(cov / max(ok, 1)).tolist(),
                bias=(bias / max(ok, 1)).tolist(), ok=ok, draws=draws)


# 5. WHO MD2
def _eval_who(args):
    G, cv, spread, draws, seed = args
    rng = np.random.default_rng(seed)
    base = 0.15
    delta = 0.02 if spread == "small" else 0.08
    r_true = np.linspace(base, base + delta, G)
    p = np.linspace(1.0, 2.0, G); p /= p.sum()
    se = r_true * cv
    true_decl = imc.measures(r_true, p, ref=0)
    true_best = imc.measures(r_true, p, ref="best")
    cov_bc_decl = {m: 0 for m in ("mdm_w", "mdb_w")}
    cov_bc_best = {m: 0 for m in ("mdm_w", "mdb_w")}
    cov_raw_decl = {m: 0 for m in ("mdm_w", "mdb_w")}
    cov_raw_best = {m: 0 for m in ("mdm_w", "mdb_w")}
    # Vectorized in chunks of 250 for speed
    chunk = min(draws, 250)
    done = 0
    while done < draws:
        m = min(chunk, draws - done)
        r_obs = np.clip(r_true[None, :] + rng.normal(0.0, se[None, :], (m, G)), 1e-4, 0.999)
        # 80 SDR-like replicates: variance = (4/80)*sum((rep - obs)^2) = se^2 -> per-rep sd = se / sqrt(4) = se / 2
        r_reps = np.clip(r_obs[:, :, None] + rng.normal(0.0, se[None, :, None] / 2.0, (m, G, 80)), 1e-4, 0.999)
        p_b = np.broadcast_to(p[None, :], (m, G))
        bc_d = rc.md_bias_corrected(r_obs, p_b, r_reps, None, ref=0, level=0.90)
        bc_b = rc.md_bias_corrected(r_obs, p_b, r_reps, None, ref="best", level=0.90)
        raw_d = imc.replicate_intervals(r_obs, p_b, r_reps, None, ref=0, level=0.90)
        raw_b = imc.replicate_intervals(r_obs, p_b, r_reps, None, ref="best", level=0.90)
        for nm in ("mdm_w", "mdb_w"):
            cov_bc_decl[nm] += int(((bc_d[nm]["lower"] <= true_decl[nm]) & (true_decl[nm] <= bc_d[nm]["upper"])).sum())
            cov_bc_best[nm] += int(((bc_b[nm]["lower"] <= true_best[nm]) & (true_best[nm] <= bc_b[nm]["upper"])).sum())
            cov_raw_decl[nm] += int(((raw_d[nm]["lower"] <= true_decl[nm]) & (true_decl[nm] <= raw_d[nm]["upper"])).sum())
            cov_raw_best[nm] += int(((raw_b[nm]["lower"] <= true_best[nm]) & (true_best[nm] <= raw_b[nm]["upper"])).sum())
        done += m
    return dict(G=G, cv=cv, spread=spread,
                bc_mdm_w=cov_bc_decl["mdm_w"] / draws, bc_mdb_w_decl=cov_bc_decl["mdb_w"] / draws,
                bc_mdb_w_best=cov_bc_best["mdb_w"] / draws,
                raw_mdm_w=cov_raw_decl["mdm_w"] / draws, raw_mdb_w_decl=cov_raw_decl["mdb_w"] / draws,
                raw_mdb_w_best=cov_raw_best["mdb_w"] / draws)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    t0 = time.time()

    d_meta = 100 if args.smoke else 2000
    d_mreg = 100 if args.smoke else 1000
    d_match = 100 if args.smoke else 1500
    d_bym2 = 20 if args.smoke else 300
    d_msm = 30 if args.smoke else 500
    d_who = 100 if args.smoke else 1500

    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        meta_pool = list(ex.map(_eval_meta_pool, [
            (k, i2, d_meta, 104100 + i)
            for i, (k, i2) in enumerate([(k, i2) for k in (10, 20, 40) for i2 in (0.0, 0.25, 0.5, 0.75)])
        ]))
        meta_reg = list(ex.map(_eval_meta_reg, [
            (k, i2, b, d_mreg, 104200 + i)
            for i, (k, i2, b) in enumerate([(k, i2, b) for k in (10, 20, 40) for i2 in (0.0, 0.5) for b in (0.0, 0.2)])
        ]))
        matching = list(ex.map(_eval_matching, [
            (n, s, h, d_match, 104300 + i)
            for i, (n, s, h) in enumerate([(n, s, h) for n in (145, 600) for s in (0.5, 1.502) for h in (False, True)])
        ]))
        bym2 = list(ex.map(_eval_bym2, [
            (ph, sg, me, d_bym2, 104400 + i)
            for i, (ph, sg, me) in enumerate([(ph, sg, me) for ph in (0.2, 0.8) for sg in (0.2, 0.5) for me in (5, 30)])
        ]))
        msm = list(ex.map(_eval_msm, [
            (K, g, psi, d_msm, 104500 + i)
            for i, (K, g, psi) in enumerate([(K, g, psi) for K in (12, 18) for g in (0.0, 0.5, 1.0) for psi in (0.0, -2.0)])
        ]))
        who = list(ex.map(_eval_who, [
            (G, cv, sp, d_who, 104600 + i)
            for i, (G, cv, sp) in enumerate([(G, cv, sp) for G in (4, 6, 8) for cv in (0.1, 0.3, 0.5) for sp in ("small", "large")])
        ]))

    outcomes = {
        "P2_all": min(r["P2"] for r in meta_pool) >= 0.86,
        "P2_k20": min(r["P2"] for r in meta_pool if r["k"] >= 20) >= 0.86,
        "R2_all": min(r["R2"] for r in meta_reg) >= 0.86,
        "R2_k20": min(r["R2"] for r in meta_reg if r["k"] >= 20) >= 0.86,
        "E2_all": max(r["E2_rej"] for r in meta_pool) <= 0.13,
        "E2_k20": max(r["E2_rej"] for r in meta_pool if r["k"] >= 20) <= 0.13,
        "M1b_ATT": min(r["M1b_ATT"] for r in matching) >= 0.86,
        "B3_all": min(r["mean_cov"] for r in bym2) >= 0.86 and min(r["share_ge_80"] for r in bym2) >= 0.80,
        "B3_E30": min(r["mean_cov"] for r in bym2 if r["median_E"] >= 30) >= 0.86,
        "M3_all": min(min(r["cov"]) for r in msm) >= 0.86,
        "MD2_bc_all": min(min(r["bc_mdm_w"], r["bc_mdb_w_decl"], r["bc_mdb_w_best"]) for r in who) >= 0.86,
        "MD2_raw_cv10": min(min(r["raw_mdm_w"], r["raw_mdb_w_decl"], r["raw_mdb_w_best"]) for r in who if r["cv"] <= 0.10) >= 0.86,
    }

    report = dict(
        smoke=args.smoke,
        elapsed_s=round(time.time() - t0, 1),
        frozen_sha256=_hashes(),
        outcomes=outcomes,
        meta_pool=meta_pool,
        meta_reg=meta_reg,
        matching=matching,
        bym2=bym2,
        msm=msm,
        who=who,
    )
    if not args.smoke:
        OUT.with_suffix(".json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        lines = [
            "# Round 104: exploratory-measure repairs validation",
            "",
            f"Elapsed: {report['elapsed_s']}s. Frozen SHA-256: `{report['frozen_sha256']}`. 90% intervals (pass ≥ .86; E2 size ≤ .13). Author self-review, not independent.",
            "",
            "## Outcomes",
            "",
            "| Candidate | Outcome | Detail |",
            "| :--- | :--- | :--- |",
        ]
        for k, v in outcomes.items():
            lines.append(f"| `{k}` | {'**pass**' if v else 'fail'} | — |")
        lines += [
            "", "## Meta-analysis (P2, E2)", "",
            "| k | I2 | P2 coverage | E2 size (.10) |",
            "| ---: | ---: | ---: | ---: |",
            *[f"| {r['k']} | {r['I2']} | {r['P2']:.3f} | {r['E2_rej']:.3f} |" for r in meta_pool],
            "", "## Meta-regression (R2)", "",
            "| k | I2 | beta | R2 coverage |",
            "| ---: | ---: | ---: | ---: |",
            *[f"| {r['k']} | {r['I2']} | {r['beta']} | {r['R2']:.3f} |" for r in meta_reg],
            "", "## Matching ATT (M1b-ATT)", "",
            "| N | Propensity | Het | M1b-ATT coverage |",
            "| ---: | ---: | :--- | ---: |",
            *[f"| {r['N']} | {r['strength']} | {r['het']} | {r['M1b_ATT']:.3f} |" for r in matching],
            "", "## BYM2 PC-prior (B3)", "",
            "| phi | sigma | median E | Mean cov | Share >= .80 |",
            "| ---: | ---: | ---: | ---: | ---: |",
            *[f"| {r['phi']} | {r['sigma']} | {r['median_E']} | {r['mean_cov']:.3f} | {r['share_ge_80']:.2f} |" for r in bym2],
            "", "## IP-weighted MSM (M3: L0-stabilized + cluster jackknife)", "",
            "| K | Feedback | psi | M3 cov (d1/d2/d3) | M3 bias (d1/d2/d3) |",
            "| ---: | ---: | ---: | :--- | :--- |",
            *[f"| {r['K']} | {r['feedback']} | {r['psi']} | "
              f"{r['cov'][0]:.3f}/{r['cov'][1]:.3f}/{r['cov'][2]:.3f} | "
              f"{r['bias'][0]:+.3f}/{r['bias'][1]:+.3f}/{r['bias'][2]:+.3f} |" for r in msm],
            "", "## WHO mean differences (MD2)", "",
            "| G | cv | Spread | bc mdm_w | bc mdb_w (decl) | bc mdb_w (best) | raw mdm_w | raw mdb_w (decl) | raw mdb_w (best) |",
            "| ---: | ---: | :--- | ---: | ---: | ---: | ---: | ---: | ---: |",
            *[f"| {r['G']} | {r['cv']} | {r['spread']} | {r['bc_mdm_w']:.3f} | {r['bc_mdb_w_decl']:.3f} | "
              f"{r['bc_mdb_w_best']:.3f} | {r['raw_mdm_w']:.3f} | {r['raw_mdb_w_decl']:.3f} | {r['raw_mdb_w_best']:.3f} |" for r in who],
        ]
        OUT.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(dict(elapsed_s=report["elapsed_s"], outcomes=outcomes), indent=2))


if __name__ == "__main__":
    main()
