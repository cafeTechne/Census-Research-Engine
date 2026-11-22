# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 80: arcsine Fay-Herriot for proportions and Rao-Yu temporal Fay-Herriot (frozen with the criterion,
docs/audits/sae_extensions_validation_criterion.md).

Effective sample sizes: docs/audits/sae_extensions_neff.csv.gz, n_eff = p(1 - p) / se^2 from the 2019-2023 S2701
percent uninsured (S2701_C05_001) and its MOE (/1.645) for MI and NY counties and tracts (areas with a published
0 or 100 percent or a zero MOE omitted).
P1 (8 cells): geometry in {MI county, NY county, MI tract, NY tract} x sigma_u in {.05, .10}. theta_i = .3218 +
.1 x_i + u_i (x_i ~ N(0, 1) fixed per cell, u_i ~ N(0, sigma_u^2) per draw), p_i = sin^2(clip(theta_i, 0, pi/2));
direct p_hat_i = Binomial(m_i, p_i) / m_i with m_i = max(1, round(n_eff_i)). P1 / P1q / P1b with B = 200.
Pass (P1 and P1q separately): mean per-area coverage >= .86, 10th percentile of per-area coverage >= .80, and
|relative bias| <= .10 among area-draws with p < .10 (relative bias = mean(p_hat - p) / mean(p)). P1b reported.
T1 (8 cells): geometry in {MI+NY counties (145), 300 MI tracts sampled once} x releases T in {2, 3} x rho in
{.3, .8}. y_it = .3218 + .1 x_it + v_i + u_it + e_it (arcsine scale), v ~ N(0, .05^2), u stationary AR(1) with
innovation SD .05, e_it ~ N(0, 1/(4 n_eff_i)); x_it ~ N(0, 1) fixed per cell. Rao-Yu with B = 100. Pass: mean
per-area coverage of the last-release theta >= .86 in every cell. MSE gain over single-release FH (last release
only) reported.
500 draws per cell. Seeds: P1 [20282001 + cell, draw]; T1 [20282051 + cell, draw].

Usage: scripts/sae_extensions_validation.py --criterion-commit SHA [--workers N] [--smoke]
"""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from census import sae_extensions_core as sc  # noqa: E402

PSEED, TSEED = 20282001, 20282051
NEFF = ROOT/"docs/audits/sae_extensions_neff.csv.gz"
P_CELLS = [(g, s) for g in ("MI county", "NY county", "MI tract", "NY tract") for s in (.05, .10)]
T_CELLS = [(g, T, rho) for g in ("counties", "tracts300") for T in (2, 3) for rho in (.3, .8)]
DRAWS, CHUNK, BP, BT = 500, 10, 200, 100
B0, B1 = .3218, .1
FROZEN = ["scripts/sae_extensions_validation.py", "census/sae_extensions_core.py",
          "docs/audits/sae_extensions_neff.csv.gz", "docs/audits/sae_extensions_validation_criterion.md"]
OUT = ROOT/"docs/audits/sae_extensions_validation"


def neff(geom):
    f = pd.read_csv(NEFF, dtype={"GEOID": str, "state": str})
    if geom == "counties":
        return f[f.level == "county"].n_eff.to_numpy()
    if geom == "tracts300":
        t = f[(f.level == "tract") & (f.state == "26")].n_eff.to_numpy()
        return np.random.default_rng([TSEED, 999]).choice(t, 300, replace=False)
    st, lvl = geom.split()
    return f[(f.level == lvl) & (f.state == {"MI": "26", "NY": "36"}[st])].n_eff.to_numpy()


def p_job(args):
    cell, start, stop = args
    geom, su = P_CELLS[cell]
    n = neff(geom); m = len(n)
    x = np.random.default_rng([PSEED+cell, 999999]).standard_normal(m)
    X = np.column_stack([np.ones(m), x])
    mm = np.maximum(1, np.round(n)).astype(int)
    acc = dict(p1=np.zeros(m), p1q=np.zeros(m), p1b=np.zeros(m), bias_num=0.0, bias_den=0.0, nb_num=0.0, n_small=0)
    for d in range(start, stop):
        rng = np.random.default_rng([PSEED+cell, d])
        p = np.sin(np.clip(B0+B1*x+rng.normal(0, su, m), 0, np.pi/2))**2
        ph = rng.binomial(mm, p)/mm
        r = sc.arcsine_fh(ph, n, X, B=BP, rng=rng)
        acc["p1"] += (r["lower"] <= p) & (p <= r["upper"])
        acc["p1q"] += (r["q_lower"] <= p) & (p <= r["q_upper"])
        acc["p1b"] += (r["naive_lower"] <= p) & (p <= r["naive_upper"])
        small = p < .10
        acc["bias_num"] += float((r["estimate"][small]-p[small]).sum()); acc["bias_den"] += float(p[small].sum())
        acc["nb_num"] += float((r["naive"][small]-p[small]).sum()); acc["n_small"] += int(small.sum())
    return "p", cell, acc


def t_job(args):
    cell, start, stop = args
    geom, T, rho = T_CELLS[cell]
    n = neff(geom); m = len(n)
    xr = np.random.default_rng([TSEED+cell, 999999])
    X = np.stack([np.ones((m, T)), xr.standard_normal((m, T))], axis=2)
    D = np.repeat((1/(4*n))[:, None], T, axis=1)
    acc = dict(t1=np.zeros(m), se_t1=0.0, se_fh=0.0, fh=np.zeros(m))
    for d in range(start, stop):
        rng = np.random.default_rng([TSEED+cell, d])
        v = rng.normal(0, .05, m)
        u = np.zeros((m, T)); u[:, 0] = rng.normal(0, .05/np.sqrt(1-rho**2), m)
        for t in range(1, T):
            u[:, t] = rho*u[:, t-1]+rng.normal(0, .05, m)
        truth = X@np.array([B0, B1])+v[:, None]+u
        y = truth+rng.normal(0, np.sqrt(D))
        r = sc.rao_yu(y, X, D, B=BT, rng=rng)
        last = truth[:, -1]
        acc["t1"] += (r["lower"] <= last) & (last <= r["upper"])
        acc["se_t1"] += float(((r["estimate"]-last)**2).mean())
        f = sc.fh_interval_analytic(y[:, -1], X[:, -1, :], D[:, -1])
        acc["se_fh"] += float(((f["estimate"]-last)**2).mean())
        acc["fh"] += (f["lower"] <= last) & (last <= f["upper"])
    return "t", cell, acc


def job(a):
    return p_job(a[1:]) if a[0] == "p" else t_job(a[1:])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--criterion-commit"); ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    if not a.smoke:
        subprocess.run(["git", "merge-base", "--is-ancestor", a.criterion_commit, "HEAD"], cwd=ROOT, check=True)
        for rel in FROZEN:
            if subprocess.check_output(["git", "show", a.criterion_commit+":"+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
                raise SystemExit("differs from criterion commit: "+rel)
    draws, chunk = (2, 1) if a.smoke else (DRAWS, CHUNK)
    tasks = [("p", c, s, min(s+chunk, draws)) for c in range(len(P_CELLS)) for s in range(0, draws, chunk)]
    tasks += [("t", c, s, min(s+chunk, draws)) for c in range(len(T_CELLS)) for s in range(0, draws, chunk)]
    P, Tt = {}, {}
    t0 = time.time()
    with ProcessPoolExecutor(a.workers) as ex:
        for i, (kind, cell, acc) in enumerate(ex.map(job, tasks, chunksize=1)):
            tgt = (P if kind == "p" else Tt)
            if cell not in tgt:
                tgt[cell] = acc
            else:
                for k, v in acc.items():
                    tgt[cell][k] = tgt[cell][k]+v
            if i % 50 == 0:
                print({"done": i, "of": len(tasks), "s": round(time.time()-t0)}, flush=True)
    prow = []
    for c, r in sorted(P.items()):
        cov = {k: r[k]/draws for k in ("p1", "p1q", "p1b")}
        prow.append(dict(geometry=P_CELLS[c][0], sigma_u=P_CELLS[c][1], areas=int(len(r["p1"])),
                         **{f"{k}_mean": float(v.mean()) for k, v in cov.items()},
                         **{f"{k}_p10": float(np.quantile(v, .10)) for k, v in cov.items()},
                         rel_bias=r["bias_num"]/r["bias_den"] if r["bias_den"] else None,
                         naive_rel_bias=r["nb_num"]/r["bias_den"] if r["bias_den"] else None, small_area_draws=r["n_small"]))
    trow = []
    for c, r in sorted(Tt.items()):
        trow.append(dict(geometry=T_CELLS[c][0], T=T_CELLS[c][1], rho=T_CELLS[c][2], t1_mean=float((r["t1"]/draws).mean()),
                         t1_p10=float(np.quantile(r["t1"]/draws, .10)), fh_mean=float((r["fh"]/draws).mean()),
                         mse_t1=r["se_t1"]/draws, mse_fh=r["se_fh"]/draws, mse_gain=1-r["se_t1"]/r["se_fh"]))
    def p_ok(k):
        return all(r[f"{k}_mean"] >= .86 and r[f"{k}_p10"] >= .80 and r["rel_bias"] is not None and abs(r["rel_bias"]) <= .10
                   for r in prow)
    passed = dict(P1=p_ok("p1"), P1q=p_ok("p1q"), T1=all(r["t1_mean"] >= .86 for r in trow))
    out = dict(p1=prow, t1=trow, passed=passed, draws=draws, bootstrap=dict(P1=BP, T1=BT),
               criterion_commit=a.criterion_commit, seconds=round(time.time()-t0),
               frozen_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FROZEN})
    if a.smoke:
        print(json.dumps(passed), out["seconds"]); return
    OUT.with_suffix(".json").write_text(json.dumps(out, indent=1)+"\n")
    L = ["# Round 80: arcsine Fay-Herriot for proportions and Rao-Yu temporal Fay-Herriot", "",
         f"Criterion commit: `{a.criterion_commit}`. {draws} draws per cell; 90% intervals. Author self-review, not "
         "independent.", "", "## P1: arcsine FH (per-area coverage: mean / 10th percentile)", "",
         "| Geometry | sigma_u | Areas | P1 MSE-normal | P1q quantile | P1b naive | Rel. bias p<.10 (P1 / naive) |",
         "| :--- | ---: | ---: | :--- | :--- | :--- | :--- |"]
    L += [f"| {r['geometry']} | {r['sigma_u']} | {r['areas']} | {r['p1_mean']:.3f} / {r['p1_p10']:.3f} | "
          f"{r['p1q_mean']:.3f} / {r['p1q_p10']:.3f} | {r['p1b_mean']:.3f} / {r['p1b_p10']:.3f} | "
          f"{r['rel_bias']:.3f} / {r['naive_rel_bias']:.3f} |" for r in prow]
    L += ["", "## T1: Rao-Yu temporal FH (last release)", "",
          "| Geometry | Releases | rho | T1 mean coverage | 10th pct | FH (g1+g2) coverage | MSE gain vs FH |",
          "| :--- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    L += [f"| {r['geometry']} | {r['T']} | {r['rho']} | {r['t1_mean']:.3f} | {r['t1_p10']:.3f} | {r['fh_mean']:.3f} | "
          f"{r['mse_gain']:.3f} |" for r in trow]
    L += ["", f"Outcomes: `{json.dumps(passed)}`.", ""]
    OUT.with_suffix(".md").write_text("\n".join(L))
    print(json.dumps(passed))


if __name__ == "__main__":
    main()
