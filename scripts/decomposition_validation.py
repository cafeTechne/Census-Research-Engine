# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 79: Oaxaca-Blinder and Fairlie decompositions with SDR replicate weights (frozen with the criterion,
docs/audits/decomposition_validation_criterion.md).

Design (Round 32 sampling, scripts/pums_tests_validation.py): households at g in [0, 1] sampled with probability
proportional to exp(sigma field(g)), weight CV 1.0; 1 + Poisson(1.5) persons per household; household latent share
rho = .25; 80 SDR replicate factors in geographic order. Persons: group A with P = logistic(log 2 + .8 sin 2 pi g)
(about two thirds), group B otherwise. Covariates: k in {3, 8} blocks = k - 1 continuous x_j = -.5 [B] +
.3 cos(2 pi g) + latent, and one 5-level categorical (latent + .4 [A] cut at -1, -.3, .3, 1).
Linear outcome: y = alpha [A] + sum .5/sqrt(k-1) x_j + .1 [A] x_1 + (0, .2, .4, .6, .8)[cat] + N(0, 1).
Binary outcome: 1{-1 + alpha_b [A] + the same index without the error + Logistic(0, 1) > 0}.
alpha (alpha_b) is set by bisection on a reference population of 300,000 households so that the population
explained share (O1; F1) equals s in {.2, .6}. Targets: the same estimators on the reference population with unit
weights (Fairlie detailed: 20 orderings). Sample households m = 1.2 x size so that group B has about `size`
persons, size in {300, 1000, 5000}. 12 cells (size x k x s), 1,000 draws each; F1 uses 10 orderings per draw.
Judged quantities: O1 explained, unexplained, explained and unexplained (Yun-normalised) per block, unexplained
intercept; F1 explained, unexplained, explained per block. Pass per quantity family (O1 totals, O1 detailed, F1
totals, F1 detailed): 90% coverage >= .86 in every cell. Size gate: failing only at size 300 -> validated from
1,000; failing only at sizes 300 and 1,000 -> validated from 5,000.
Seeds: reference [20281901, k, s]; draws [20281911 + cell, draw].

Usage: scripts/decomposition_validation.py --criterion-commit SHA [--workers N] [--smoke]
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

import pums_tests_validation as r32  # noqa: E402
from census import decomposition_core as dc  # noqa: E402
from census import pums_tests as pt  # noqa: E402

SEED = 20281901
SIZES, KS, SHARES = (300, 1000, 5000), (3, 8), (.2, .6)
CELLS = [(size, k, s) for size in SIZES for k in KS for s in SHARES]
DRAWS, CHUNK, R_DRAW, R_TARGET, H_REF = 1000, 20, 10, 20, 300000
RHO, CV = .25, 1.0
CUTS = (-1, -.3, .3, 1)
FROZEN = ["scripts/decomposition_validation.py", "census/decomposition_core.py", "scripts/pums_tests_validation.py",
          "census/pums_tests.py", "docs/audits/decomposition_validation_criterion.md"]
OUT = ROOT/"docs/audits/decomposition_validation"


def persons(rng, g, k):
    H = len(g); size = 1+rng.poisson(1.5, H); idx = np.repeat(np.arange(H), size); n = len(idx)
    he = rng.standard_normal((k+3, H)); pe = rng.standard_normal((k+3, n))
    lat = np.sqrt(RHO)*he[:, idx]+np.sqrt(1-RHO)*pe
    gp = g[idx]
    A = (rng.random(n) < 1/(1+np.exp(-(np.log(2)+.8*np.sin(2*np.pi*gp))))).astype(int)
    xs = np.column_stack([-.5*(1-A)+.3*np.cos(2*np.pi*gp)+lat[j] for j in range(k-1)])
    cat = np.digitize(lat[k-1]+.4*A, CUTS)
    D = np.eye(5)[cat][:, 1:]
    X = np.column_stack([np.ones(n), xs, D])
    index = xs@np.full(k-1, .5/np.sqrt(k-1))+.1*A*xs[:, 0]+D@np.array([.2, .4, .6, .8])
    return dict(idx=idx, A=A, X=X, index=index, e=rng.standard_normal(n), u=rng.logistic(0, 1, n))


def blocks_for(k):
    b = {f"x{j+1}": [1+j] for j in range(k-1)}
    b["cat"] = list(range(k, k+4))
    return b


def outcomes(p, alpha, alpha_b):
    y = alpha*p["A"]+p["index"]+p["e"]
    yb = (-1+alpha_b*p["A"]+p["index"]+p["u"] > 0).astype(float)
    return y, yb


def reference(k, s):
    rng = np.random.default_rng([SEED, k, int(100*s)])
    p = persons(rng, rng.uniform(0, 1, H_REF), k)
    w = np.ones(len(p["A"])); bl = blocks_for(k)

    def share(kind, a):
        y, yb = outcomes(p, a, a)
        if kind == "o":
            o = dc.oaxaca(y, p["X"], p["A"], w, bl, ("cat",))
        else:
            o = dc.fairlie(yb, p["X"], p["A"], w, bl, R=2, rng=np.random.default_rng(1))[0]
        return o["explained"]/o["gap"]

    def solve(kind):  # explained share falls as alpha grows (alpha > 0 widens the unexplained part)
        lo, hi = 0.0, 5.0
        for _ in range(40):
            mid = (lo+hi)/2
            lo, hi = (mid, hi) if share(kind, mid) > s else (lo, mid)
        return (lo+hi)/2
    alpha, alpha_b = solve("o"), solve("f")
    y, yb = outcomes(p, alpha, alpha_b)
    o = dc.oaxaca(y, p["X"], p["A"], w, bl, ("cat",))
    f = dc.fairlie(yb, p["X"], p["A"], w, bl, R=R_TARGET, rng=np.random.default_rng([SEED, k, 7]))[0]
    return dict(alpha=alpha, alpha_b=alpha_b, oaxaca=o, fairlie=f, persons=int(len(w)),
                share_o=o["explained"]/o["gap"], share_f=f["explained"]/f["gap"])


def judged(kind, k):
    names = ["explained", "unexplained"]
    det = [f"explained:{b}" for b in blocks_for(k)]
    if kind == "oaxaca":
        det += [f"unexplained:{b}" for b in blocks_for(k)]+["unexplained:intercept"]
    return names, det


def job(args):
    cell, start, stop, targets = args
    size, k, s = CELLS[cell]
    sigma = r32.sigma_for(CV)
    m = int(1.2*size)
    bl = blocks_for(k)
    hits = {}
    for d in range(start, stop):
        rng = np.random.default_rng([SEED+10+cell, d])
        u = rng.uniform(0, 1, m)
        pi = np.exp(sigma*r32.field(r32.GRID)); cdf = np.cumsum(pi); cdf /= cdf[-1]
        g = np.sort(np.interp(u, cdf, r32.GRID))
        w = 1/np.exp(sigma*r32.field(g))
        p = persons(rng, g, k)
        W = (w[:, None]*np.column_stack((np.ones(m), pt.sdr_factors(m))))[p["idx"]]
        y, yb = outcomes(p, targets["alpha"], targets["alpha_b"])
        res = {"oaxaca": dc.with_replicates("oaxaca", y, p["X"], p["A"], W, bl, ("cat",)),
               "fairlie": dc.with_replicates("fairlie", yb, p["X"], p["A"], W, bl, R=R_DRAW, rng=rng)}
        for kind, r in res.items():
            for q in sum(judged(kind, k), []):
                est, se, lo, hi = r[q]
                key = f"{kind}|{q}"
                hits[key] = hits.get(key, 0)+int(lo <= targets[kind][q] <= hi)
    return cell, hits


def judge(cov, family):
    """cov: {cell: {key: rate}}; family: list of keys. Returns pass/gate info."""
    fail_sizes = sorted({CELLS[c][0] for c, r in cov.items() for key in family(c) if r[key] < .86})
    gate = None
    if not fail_sizes:
        gate = SIZES[0]
    elif fail_sizes == [300]:
        gate = 1000
    elif fail_sizes == [300, 1000]:
        gate = 5000
    return dict(passed=not fail_sizes, failing_sizes=fail_sizes, validated_from=gate)


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
    with ProcessPoolExecutor(min(a.workers, 4)) as ex:
        refs = dict(zip([(k, s) for k in KS for s in SHARES], ex.map(reference, *zip(*[(k, s) for k in KS for s in SHARES]))))
    print({"targets_s": round(time.time()-t0), **{f"{k}/{s}": (round(r['share_o'], 3), round(r['share_f'], 3)) for (k, s), r in refs.items()}}, flush=True)
    draws, chunk = (4, 2) if a.smoke else (DRAWS, CHUNK)
    tasks = [(c, st, min(st+chunk, draws), refs[CELLS[c][1:]]) for c in range(len(CELLS)) for st in range(0, draws, chunk)]
    cov = {}
    with ProcessPoolExecutor(a.workers) as ex:
        for i, (cell, hits) in enumerate(ex.map(job, tasks, chunksize=1)):
            acc = cov.setdefault(cell, {})
            for key, v in hits.items():
                acc[key] = acc.get(key, 0)+v
            if i % 100 == 0:
                print({"done": i, "of": len(tasks), "s": round(time.time()-t0)}, flush=True)
    rates = {c: {k: v/draws for k, v in r.items()} for c, r in cov.items()}
    fams = {
        "O1_totals": lambda c: ["oaxaca|explained", "oaxaca|unexplained"],
        "O1_detailed": lambda c: ["oaxaca|"+q for q in judged("oaxaca", CELLS[c][1])[1]],
        "F1_totals": lambda c: ["fairlie|explained", "fairlie|unexplained"],
        "F1_detailed": lambda c: ["fairlie|"+q for q in judged("fairlie", CELLS[c][1])[1]]}
    outcome = {name: judge(rates, f) for name, f in fams.items()}
    rows = [dict(size=CELLS[c][0], k=CELLS[c][1], share=CELLS[c][2],
                 **{name: min(rates[c][q] for q in f(c)) for name, f in fams.items()}) for c in sorted(rates)]
    out = dict(cells=rows, outcome=outcome, coverage={str(CELLS[c]): r for c, r in rates.items()},
               targets={f"{k}/{s}": {kk: v for kk, v in r.items()} for (k, s), r in refs.items()},
               draws=draws, orderings=dict(draw=R_DRAW, target=R_TARGET), criterion_commit=a.criterion_commit,
               seconds=round(time.time()-t0), frozen_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FROZEN})
    if a.smoke:
        print(json.dumps(outcome), out["seconds"]); return
    OUT.with_suffix(".json").write_text(json.dumps(out, indent=1, default=float)+"\n")
    L = ["# Round 79: Oaxaca-Blinder and Fairlie decompositions with SDR replicate weights", "",
         f"Criterion commit: `{a.criterion_commit}`. {draws} draws per cell; 90% SDR intervals; Fairlie {R_DRAW} "
         "orderings per draw. Lowest coverage over the quantities in each family. Author self-review, not independent.",
         "", "| Group B size | Blocks | Explained share | O1 totals | O1 detailed | F1 totals | F1 detailed |",
         "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    L += [f"| {r['size']} | {r['k']} | {r['share']} | {r['O1_totals']:.3f} | {r['O1_detailed']:.3f} | {r['F1_totals']:.3f} | "
          f"{r['F1_detailed']:.3f} |" for r in rows]
    L += ["", "Achieved population explained shares (O1, F1): "+", ".join(
        f"k={k}, s={s}: {r['share_o']:.3f}, {r['share_f']:.3f}" for (k, s), r in refs.items())+".", "",
        f"Outcomes: `{json.dumps(outcome)}`.", ""]
    OUT.with_suffix(".md").write_text("\n".join(L))
    print(json.dumps(outcome))


if __name__ == "__main__":
    main()
