# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 99: matching estimators and triple differences (frozen with the criterion,
docs/audits/matching_validation_criterion.md).

Usage: scripts/matching_validation.py --criterion-commit SHA [--workers N] [--smoke]
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
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/"scripts"))
import numpy as np  # noqa: E402

from census import matching_core as mc  # noqa: E402
import positivity_validation as pv  # noqa: E402

M_CELLS = [(n, a, het) for n in (145, 600) for a in (.5, 1.502) for het in (False, True)]
T_CELLS = [(tau, delta) for tau in (0., -2.) for delta in (0., .3)]
DRAWS, CHUNK = 2000, 50
FROZEN = ["scripts/matching_validation.py", "census/matching_core.py", "census/positivity_core.py",
          "scripts/positivity_validation.py", "docs/audits/matching_validation_criterion.md"]
OUT = ROOT/"docs/audits/matching_validation"
KEYS_M = ("M1-ATT", "M1-ATE", "M2", "M3")


def m_job(cell, start, stop):
    n, a, het = M_CELLS[cell]
    acc = {k: 0 for k in KEYS_M}; acc["fail"] = 0; acc["share_matched"] = 0.
    for d in range(start, stop):
        rng = np.random.default_rng([20282991, cell, d])
        y, T, z, _ = pv.draw(rng, n, a, het)
        tau = .5+.5*z[:, 0] if het else np.full(n, .5)
        try:
            r1 = mc.nn_match(y, T, z, 4, "ATT"); r2 = mc.nn_match(y, T, z, 4, "ATE")
            r3 = mc.cem(y, T, z); r4 = mc.ps_match(y, T, z, rng, 200)
        except (ValueError, np.linalg.LinAlgError):
            acc["fail"] += 1; continue
        att = tau[T == 1].mean(); attm = tau[(T == 1) & r3["matched"]].mean()
        for k, r, tgt in (("M1-ATT", r1, att), ("M1-ATE", r2, .5), ("M2", r3, attm), ("M3", r4, att)):
            acc[k] += r["lower"] <= tgt <= r["upper"]
        acc["share_matched"] += r3["share_treated_matched"]
    return acc


def panel(rng, tau, delta, U=51, P=10):
    tr = np.r_[np.ones(26), np.zeros(U-26)]
    rows = []
    gamma = rng.normal(0, .5, (U, P))+delta*(np.arange(P)[None, :]-5)*tr[:, None]
    for g in (1, 0):
        alpha = rng.normal(0, 1, U); lam = rng.normal(0, .5, P)
        e = np.zeros((U, P)); e[:, 0] = rng.normal(0, .5, U)
        for t in range(1, P):
            e[:, t] = .5*e[:, t-1]+rng.normal(0, .5*np.sqrt(.75), U)
        D = (tr[:, None]*g*(np.arange(P)[None, :] >= 5))
        y = alpha[:, None]+lam[None, :]+gamma+tau*D+e
        for u in range(U):
            for t in range(P):
                rows.append((u, g, t, tr[u], int(t >= 5), y[u, t]))
    return np.array(rows, float)


def _did(a):
    from scipy import stats
    y, u, t = a[:, 5], a[:, 0].astype(int), a[:, 2].astype(int)
    D = a[:, 3]*a[:, 4]
    Fu = np.eye(u.max()+1)[u]; Ft = np.eye(t.max()+1)[t][:, 1:]
    F = np.hstack([Fu, Ft]); X = np.column_stack([D, F])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None); r = y-X @ beta
    dres = D-F @ np.linalg.lstsq(F, D, rcond=None)[0]
    G = u.max()+1
    meat = sum(float(np.sum(dres[u == g]*r[u == g]))**2 for g in range(G))
    n, k = len(y), np.linalg.matrix_rank(X)
    se = float(np.sqrt(G/(G-1)*(n-1)/(n-k)*meat/(dres @ dres)**2)); c = stats.t.ppf(.95, G-1)
    return dict(estimate=float(beta[0]), lower=float(beta[0])-c*se, upper=float(beta[0])+c*se)


def t_job(cell, start, stop):
    tau, delta = T_CELLS[cell]
    acc = {"T3": 0, "D2": 0, "T3_bias": 0., "D2_bias": 0.}
    for d in range(start, stop):
        R = panel(np.random.default_rng([20282992, cell, d]), tau, delta)
        r3 = mc.triple_difference(R[:, 5], R[:, 0], R[:, 1], R[:, 2], R[:, 3], R[:, 4])
        r2 = _did(R[R[:, 1] == 1])
        acc["T3"] += r3["lower"] <= tau <= r3["upper"]; acc["D2"] += r2["lower"] <= tau <= r2["upper"]
        acc["T3_bias"] += r3["estimate"]-tau; acc["D2_bias"] += r2["estimate"]-tau
    return acc


def job(args):
    kind, cell, start, stop = args
    return kind, cell, (m_job if kind == "m" else t_job)(cell, start, stop)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--criterion-commit"); ap.add_argument("--workers", type=int, default=14)
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    if not a.smoke:
        subprocess.run(["git", "merge-base", "--is-ancestor", a.criterion_commit, "HEAD"], cwd=ROOT, check=True)
        for rel in FROZEN:
            if subprocess.check_output(["git", "show", a.criterion_commit+":"+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
                raise SystemExit("differs from criterion commit: "+rel)
    t0 = time.time()
    draws, ch = (4, 2) if a.smoke else (DRAWS, CHUNK)
    tasks = [(k, c, s, min(s+ch, draws)) for k, cells in (("m", M_CELLS), ("t", T_CELLS)) for c in range(len(cells))
             for s in range(0, draws, ch)]
    agg = {}
    with ProcessPoolExecutor(a.workers) as ex:
        for kind, cell, res in ex.map(job, tasks, chunksize=1):
            g = agg.setdefault((kind, cell), {})
            for k, v in res.items():
                g[k] = g.get(k, 0)+float(v)
    mrows = [dict(N=n, a=aa, heterogeneous=h, **{k: v/draws for k, v in agg[("m", i)].items()}) for i, (n, aa, h) in enumerate(M_CELLS)]
    trows = [dict(tau=t, delta=dl, **{k: v/draws for k, v in agg[("t", i)].items()}) for i, (t, dl) in enumerate(T_CELLS)]
    outcome = {k: dict(passed=bool(min(r[k] for r in mrows) >= .86), min=float(min(r[k] for r in mrows))) for k in KEYS_M}
    outcome["T3"] = dict(passed=bool(min(r["T3"] for r in trows) >= .86), min=float(min(r["T3"] for r in trows)))
    out = dict(matching=mrows, triple=trows, outcome=outcome, draws=draws, criterion_commit=a.criterion_commit,
               seconds=round(time.time()-t0), frozen_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FROZEN})
    if a.smoke:
        print(json.dumps(outcome), out["seconds"]); return
    OUT.with_suffix(".json").write_text(json.dumps(out, indent=1)+"\n")
    L = ["# Round 99: matching estimators and triple differences", "", f"Criterion commit: `{a.criterion_commit}`. {draws} "
         "draws per cell; 90% intervals. Author self-review, not independent.", "", "| Estimator | Outcome | Lowest coverage |",
         "| :--- | :--- | ---: |"] + [f"| {k} | {'pass' if v['passed'] else 'fail'} | {v['min']:.3f} |" for k, v in outcome.items()]
    L += ["", "| N | Propensity strength | Heterogeneous | M1-ATT | M1-ATE | M2 (CEM) | M3 (PS) | CEM share matched | Failures |",
          "| ---: | ---: | :--- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    L += [f"| {r['N']} | {r['a']} | {r['heterogeneous']} | {r['M1-ATT']:.3f} | {r['M1-ATE']:.3f} | {r['M2']:.3f} | {r['M3']:.3f} | "
          f"{r['share_matched']:.2f} | {r['fail']:.3f} |" for r in mrows]
    L += ["", "| tau | delta (treated-unit trend) | T3 coverage | T3 bias | D2 (group A DiD) coverage | D2 bias |",
          "| ---: | ---: | ---: | ---: | ---: | ---: |"]
    L += [f"| {r['tau']} | {r['delta']} | {r['T3']:.3f} | {r['T3_bias']:.3f} | {r['D2']:.3f} | {r['D2_bias']:.3f} |" for r in trows]
    L.append("")
    OUT.with_suffix(".md").write_text("\n".join(L))
    print(json.dumps({k: v["passed"] for k, v in outcome.items()}))


if __name__ == "__main__":
    main()
