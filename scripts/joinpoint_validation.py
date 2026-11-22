# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 77: joinpoint regression and age-adjusted rate ratios (frozen with the criterion,
docs/audits/joinpoint_validation_criterion.md).

Joinpoint (45 cells): n in {15, 20, 25} annual points x expected events in the first year E in {50, 500, 5000} x
scenario: J0 (no joinpoint, APC 1%), J1d2 / J1d5 (one joinpoint at index n // 2, log slope .01 then .01 + d/100),
J2d2 / J2d5 (two joinpoints at round(n/3), round(2n/3), slopes .01, .01 + d/100, .01). Counts d_t ~ Poisson(mean),
known population 1e6, y = log(d / 1e6), WLS weights d_t. 1,000 draws per cell.
- J1: select_k with K = 3, alpha .05 (each test at .05/3), B = 999 permutations. Pass: false-joinpoint rate (k > 0
  selected) <= .10 in every J0 cell. Power (k = true k; k >= 1) reported.
- J2 / J3: fit with the true k; t intervals for every segment APC and the whole-window AAPC. Pass: coverage >= .86 for
  every segment and the AAPC in every cell.
- J2b / J3b: k from J1, empirical-quantile bootstrap (B = 999) for the last segment's APC and the AAPC. Judged
  separately with the same rule.
Rate ratio (4 cells): 10 age strata, standard weights STD, two areas with different age structures; expected
counts per stratum drawn once per cell uniformly in [5, 50] (small) or [500, 5000] (large); true ratio of
age-specific rates theta in {1, 1.5}. 2,000 draws per cell. R1 (Tiwari) and R1b (log delta) judged separately:
coverage >= .86 in every cell.
Seeds: joinpoint [20281701 + cell, draw]; ratio [20281751 + cell, chunk].

Usage: scripts/joinpoint_validation.py --criterion-commit SHA [--workers N] [--smoke]
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

from census import joinpoint_core as jc  # noqa: E402

JSEED, RSEED = 20281701, 20281751
NS, ES = (15, 20, 25), (50, 500, 5000)
SCEN = ("J0", "J1d2", "J1d5", "J2d2", "J2d5")
CELLS = [(n, E, s) for n in NS for E in ES for s in SCEN]
K, ALPHA, BPERM, BBOOT = 3, .05, 999, 999
DRAWS, RDRAWS, CHUNK = 1000, 2000, 25
STD = np.array([.0139, .0553, .1454, .1352, .1625, .1349, .0874, .0661, .0447, .0155]); STD = STD/STD.sum()
RCELLS = [(lvl, th) for lvl in ("small", "large") for th in (1.0, 1.5)]
FROZEN = ["scripts/joinpoint_validation.py", "census/joinpoint_core.py", "docs/audits/joinpoint_validation_criterion.md"]
OUT = ROOT/"docs/audits/joinpoint_validation"


def truth(n, s):
    if s == "J0":
        return [], [.01]
    d = (2 if s.endswith("d2") else 5)/100
    if s.startswith("J1"):
        return [n//2], [.01, .01+d]
    return [round(n/3), round(2*n/3)], [.01, .01+d, .01]


def mean_log(n, jps, sl):
    x = np.arange(n, dtype=float)
    mu = sl[0]*x
    for j, (a, b) in zip(jps, zip(sl, sl[1:])):
        mu += (b-a)*np.maximum(x-j, 0)
    return x, mu


def true_aapc(n, jps, sl):
    cuts = [0, *jps, n-1]
    L = np.diff(cuts)/(n-1)
    return 100*(np.exp(float(np.dot(L, sl)))-1)


def jp_job(args):
    cell, start, stop = args
    n, E, s = CELLS[cell]
    jps, sl = truth(n, s)
    x, mu = mean_log(n, jps, sl)
    k_true = len(jps)
    apc_true = 100*(np.exp(np.array(sl))-1); aapc_true = true_aapc(n, jps, sl)
    res = dict(sel=[0]*(K+1), j2=[0]*(k_true+1), j3=0, j2b=0, j3b=0, failed=0)
    for d in range(start, stop):
        rng = np.random.default_rng([JSEED+cell, d])
        cnt = rng.poisson(E*np.exp(mu)).astype(float)
        if (cnt == 0).any():
            res["failed"] += 1; continue
        y = np.log(cnt/1e6)
        k, _ = jc.select_k(x, y, cnt, K, alpha=ALPHA, B=BPERM, rng=rng)
        res["sel"][k] += 1
        f = jc.fit_with_residuals(x, y, cnt, k_true)
        a = jc.apc_intervals(f)
        for i in range(k_true+1):
            res["j2"][i] += int(a["lower"][i] <= apc_true[i] <= a["upper"][i])
        g = jc.aapc_interval(f)
        res["j3"] += int(g["lower"] <= aapc_true <= g["upper"])
        fs = jc.fit_with_residuals(x, y, cnt, k)
        b = jc.bootstrap_intervals(fs, cnt, B=BBOOT, rng=rng)
        res["j2b"] += int(b["last_apc_lower"] <= apc_true[-1] <= b["last_apc_upper"])
        res["j3b"] += int(b["aapc_lower"] <= aapc_true <= b["aapc_upper"])
    return "jp", cell, res


def ratio_job(args):
    cell, chunk, m = args
    lvl, th = RCELLS[cell]
    setup = np.random.default_rng([RSEED+cell, 999999])
    lo, hi = (5, 50) if lvl == "small" else (500, 5000)
    e2 = setup.uniform(lo, hi, 10); e1 = setup.uniform(lo, hi, 10)
    rate2 = np.linspace(.0002, .02, 10)
    n2 = e2/rate2; n1 = e1/(th*rate2)
    target = th
    rng = np.random.default_rng([RSEED+cell, chunk])
    d1 = rng.poisson(e1, (m, 10)); d2 = rng.poisson(e2, (m, 10))
    r = jc.tiwari_ratio(d1, n1, d2, n2, STD)
    ok = np.isfinite(r["ratio"])
    t = ok & (r["tiwari_lower"] <= target) & (target <= r["tiwari_upper"])
    dl = ok & (r["delta_lower"] <= target) & (target <= r["delta_upper"])
    return "ratio", cell, dict(r1=int(t.sum()), r1b=int(dl.sum()))


def job(a):
    return jp_job(a[1:]) if a[0] == "jp" else ratio_job(a[1:])


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
    draws, rdraws, chunk = (4, 100, 2) if a.smoke else (DRAWS, RDRAWS, CHUNK)
    tasks = [("jp", c, s, min(s+chunk, draws)) for c in range(len(CELLS)) for s in range(0, draws, chunk)]
    tasks += [("ratio", c, k, 100) for c in range(len(RCELLS)) for k in range(rdraws//100)]
    jp = {}; rr = {}
    t0 = time.time()
    with ProcessPoolExecutor(a.workers) as ex:
        for i, (kind, cell, res) in enumerate(ex.map(job, tasks, chunksize=1)):
            acc = (jp if kind == "jp" else rr).setdefault(cell, None)
            if acc is None:
                (jp if kind == "jp" else rr)[cell] = res
            else:
                for key, v in res.items():
                    acc[key] = [x+y for x, y in zip(acc[key], v)] if isinstance(v, list) else acc[key]+v
            if i % 200 == 0:
                print({"done": i, "of": len(tasks), "s": round(time.time()-t0)}, flush=True)
    rows = []
    for c, r in sorted(jp.items()):
        n, E, s = CELLS[c]
        used = draws-r["failed"]
        k_true = len(truth(n, s)[0])
        rows.append(dict(n=n, E=E, scenario=s, k_true=k_true, failed=r["failed"],
                         selected=[v/used for v in r["sel"]], false_jp=(1-r["sel"][0]/used) if k_true == 0 else None,
                         power_exact=r["sel"][k_true]/used, power_any=(1-r["sel"][0]/used),
                         j2=[v/used for v in r["j2"]], j3=r["j3"]/used, j2b=r["j2b"]/used, j3b=r["j3b"]/used))
    rrows = [dict(level=RCELLS[c][0], theta=RCELLS[c][1], r1=r["r1"]/rdraws, r1b=r["r1b"]/rdraws) for c, r in sorted(rr.items())]
    passed = dict(
        J1=all(r["false_jp"] <= .10 for r in rows if r["k_true"] == 0),
        J2=all(min(r["j2"]) >= .86 for r in rows), J3=all(r["j3"] >= .86 for r in rows),
        J2b=all(r["j2b"] >= .86 for r in rows), J3b=all(r["j3b"] >= .86 for r in rows),
        R1=all(r["r1"] >= .86 for r in rrows), R1b=all(r["r1b"] >= .86 for r in rrows))
    out = dict(joinpoint=rows, ratio=rrows, passed=passed, draws=dict(joinpoint=draws, ratio=rdraws),
               permutations=BPERM, bootstrap=BBOOT, criterion_commit=a.criterion_commit, seconds=round(time.time()-t0),
               frozen_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FROZEN})
    if a.smoke:
        print(json.dumps(passed), out["seconds"]); return
    OUT.with_suffix(".json").write_text(json.dumps(out, indent=1)+"\n")
    L = ["# Round 77: joinpoint regression and age-adjusted rate ratios", "",
         f"Criterion commit: `{a.criterion_commit}`. {draws} draws per joinpoint cell ({BPERM} permutations, {BBOOT} "
         f"bootstrap fits), {rdraws} per ratio cell; 90% intervals; pass = coverage >= .86 in every cell (J1: "
         "false-joinpoint rate <= .10). Author self-review, not independent.", "",
         "| n | E | Scenario | False/any jp | Exact k | J2 min segment | J3 AAPC | J2b last APC | J3b AAPC |",
         "| ---: | ---: | :--- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for r in rows:
        L.append(f"| {r['n']} | {r['E']} | {r['scenario']} | {r['power_any']:.3f} | {r['power_exact']:.3f} | "
                 f"{min(r['j2']):.3f} | {r['j3']:.3f} | {r['j2b']:.3f} | {r['j3b']:.3f} |")
    L += ["", "| Counts per stratum | True ratio | R1 Tiwari | R1b log delta |", "| :--- | ---: | ---: | ---: |"]
    L += [f"| {r['level']} | {r['theta']} | {r['r1']:.4f} | {r['r1b']:.4f} |" for r in rrows]
    L += ["", f"Outcomes: `{json.dumps(passed)}`.", ""]
    OUT.with_suffix(".md").write_text("\n".join(L))
    print(json.dumps(passed))


if __name__ == "__main__":
    main()
