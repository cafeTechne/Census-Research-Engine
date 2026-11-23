# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 98: regression discontinuity (frozen with the criterion, docs/audits/rdd_validation_criterion.md).

Usage: scripts/rdd_validation.py --criterion-commit SHA [--workers N] [--smoke]
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

from census import rdd_core as rc  # noqa: E402
from census.pums_tests import sdr_factors  # noqa: E402

C_CELLS = [(shape, tau, n) for shape in ("linear", "quadratic", "lee") for tau in (0., .2) for n in (2000, 10000, 50000)]
D_CELLS = [("linear", 0.), ("linear", .05), ("quadratic", 0.), ("quadratic", .05), ("fuzzy", .15)]
DRAWS, CHUNK = 2000, 50
FROZEN = ["scripts/rdd_validation.py", "census/rdd_core.py", "census/pums_tests.py", "docs/audits/rdd_validation_criterion.md"]
OUT = ROOT/"docs/audits/rdd_validation"
LEE_L = np.array([.48, 1.27, 7.18, 20.21, 21.54, 7.33]); LEE_R = np.array([.52, .84, -3.00, 7.99, -9.01, 3.56])


def c_data(rng, shape, tau, n):
    if shape == "lee":
        x = 2*rng.beta(2, 4, n)-1
        right = LEE_R.copy()
        if tau == 0:
            right[0] = LEE_L[0]
        P = np.vander(x, 6, increasing=True)
        y = np.where(x >= 0, P @ right, P @ LEE_L)+rng.normal(0, .1295, n)
        return x, y, (right[0]-LEE_L[0])
    x = rng.uniform(-1, 1, n)
    m = .5*x if shape == "linear" else x+2*x**2
    return x, m+tau*(x >= 0)+rng.normal(0, .3, n), tau


def c_job(cell, start, stop):
    shape, tau, n = C_CELLS[cell]
    acc = dict(R1=0, R0=0, D1=0, fail=0)
    for d in range(start, stop):
        rng = np.random.default_rng([20282981, cell, d])
        x, y, t = c_data(rng, shape, tau, n)
        try:
            o = rc.rdd(x, y, 0.)
        except (ValueError, np.linalg.LinAlgError):
            acc["fail"] += 1; continue
        acc["R1"] += o["robust_lower"] <= t <= o["robust_upper"]; acc["R0"] += o["lower"] <= t <= o["upper"]
        acc["D1"] += rc.density_test(x, 0.)["p"] < .10
    return acc


def d_job(cell, start, stop):
    shape, tau = D_CELLS[cell]
    acc = {"R1-rep": 0, "R1-cluster": 0, "R1-hc": 0, "fail": 0}
    n = 30000
    for dd in range(start, stop):
        rng = np.random.default_rng([20282982, cell, dd])
        age = rng.integers(45, 85, n).astype(float)
        w = rng.lognormal(-.5*np.log(2), np.sqrt(np.log(2)), n)
        R = w[:, None]*sdr_factors(n)[rng.permutation(n)]
        a = age-65
        if shape == "fuzzy":
            d = (rng.random(n) < .05+.85*(age >= 65)).astype(float)
            y = (rng.random(n) < .80+.003*a+.15*d).astype(float)
        else:
            d = None
            p = .80+.003*a+(.0002*a**2 if shape == "quadratic" else 0)+tau*(age >= 65)
            y = (rng.random(n) < p).astype(float)
        try:
            h = rc.ik_bandwidth(age, y, 65.)
            h = max(h, 3.0)
            res = {"R1-rep": rc.rdd(age, y, 65., h=h, d=d, weights=w, replicate_weights=R),
                   "R1-cluster": rc.rdd(age, y, 65., h=h, d=d, weights=w, vce="cluster"),
                   "R1-hc": rc.rdd(age, y, 65., h=h, d=d, weights=w)}
        except (ValueError, np.linalg.LinAlgError):
            acc["fail"] += 1; continue
        for k, o in res.items():
            acc[k] += o["robust_lower"] <= tau <= o["robust_upper"]
    return acc


def job(args):
    kind, cell, start, stop = args
    return kind, cell, (c_job if kind == "c" else d_job)(cell, start, stop)


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
    tasks = [(k, c, s, min(s+ch, draws)) for k, cells in (("c", C_CELLS), ("d", D_CELLS)) for c in range(len(cells))
             for s in range(0, draws, ch)]
    agg = {}
    with ProcessPoolExecutor(a.workers) as ex:
        for i, (kind, cell, res) in enumerate(ex.map(job, tasks, chunksize=1)):
            g = agg.setdefault((kind, cell), {})
            for k, v in res.items():
                g[k] = g.get(k, 0)+int(v)
            if i % 200 == 0:
                print({"done": i, "of": len(tasks), "s": round(time.time()-t0)}, flush=True)
    crows = [dict(shape=s, tau=t, n=n, **{k: v/draws for k, v in agg[("c", i)].items()}) for i, (s, t, n) in enumerate(C_CELLS)]
    drows = [dict(shape=s, tau=t, **{k: v/draws for k, v in agg[("d", i)].items()}) for i, (s, t) in enumerate(D_CELLS)]
    outcome = {"R1": dict(passed=min(r["R1"] for r in crows) >= .86, min=min(r["R1"] for r in crows)),
               "R1-rep": dict(passed=min(r["R1-rep"] for r in drows) >= .86, min=min(r["R1-rep"] for r in drows)),
               "D1": dict(passed=max(r["D1"] for r in crows) <= .10, max=max(r["D1"] for r in crows))}
    out = dict(continuous=crows, discrete=drows, outcome=outcome, draws=draws, criterion_commit=a.criterion_commit,
               seconds=round(time.time()-t0), frozen_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FROZEN})
    if a.smoke:
        print(json.dumps(outcome), out["seconds"]); return
    OUT.with_suffix(".json").write_text(json.dumps(out, indent=1)+"\n")
    L = ["# Round 98: regression discontinuity", "", f"Criterion commit: `{a.criterion_commit}`. {draws} draws per cell; "
         "90% intervals. Author self-review, not independent.", "", "| Estimator | Outcome | Key value |", "| :--- | :--- | ---: |",
         f"| R1 robust bias-corrected (continuous) | {'pass' if outcome['R1']['passed'] else 'fail'} | lowest coverage {outcome['R1']['min']:.3f} |",
         f"| R1-rep replicate SEs (discrete ages) | {'pass' if outcome['R1-rep']['passed'] else 'fail'} | lowest coverage {outcome['R1-rep']['min']:.3f} |",
         f"| D1 density test | {'pass' if outcome['D1']['passed'] else 'fail'} | largest null rejection rate {outcome['D1']['max']:.3f} |", "",
         "## Continuous", "", "| Shape | Jump | n | R1 robust | R0 conventional | D1 rejection | Failures |", "| :--- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    L += [f"| {r['shape']} | {r['tau']} | {r['n']:,} | {r['R1']:.3f} | {r['R0']:.3f} | {r['D1']:.3f} | {r['fail']:.3f} |" for r in crows]
    L += ["", "## Discrete (ages 45-84, cutoff 65, survey weights)", "", "| Design | Jump | R1-rep | R1-cluster | R1-hc | Failures |",
          "| :--- | ---: | ---: | ---: | ---: | ---: |"]
    L += [f"| {r['shape']} | {r['tau']} | {r['R1-rep']:.3f} | {r['R1-cluster']:.3f} | {r['R1-hc']:.3f} | {r['fail']:.3f} |" for r in drows]
    L.append("")
    OUT.with_suffix(".md").write_text("\n".join(L))
    print(json.dumps({k: v["passed"] for k, v in outcome.items()}))


if __name__ == "__main__":
    main()
