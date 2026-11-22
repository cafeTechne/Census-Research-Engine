# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 73: three-level models and fixed-loading indices (frozen with the criterion,
docs/audits/methods73_validation_criterion.md).

ML (4 cells): nested random intercepts with G_top in {30, 49} top units, 10-30 middle units each and 5-15 bottom units
each (unbalanced; drawn once per cell), true shares (bottom, mid, top) in {(.70, .11, .19), (.50, .25, .25)}, total
variance 1, a bottom-level covariate x ~ N(0, 1) with slope .5. M1: t(G_top - 1) Wald interval for the slope
(1,000 draws per cell; pass >= .86 in every cell). M3: jackknife share intervals (screening, 100 draws per cell;
reported, exploratory whatever the result).
LI (4 cells): Round 36's design (scripts/index_validation.py setup/true_ind; MI/NY geometry; reliability .9/.7 x
range 0/100 km) with fixed published loadings (.9, .8, .6, .5, .7). Pass: mean per-area coverage >= .86 and every
area >= .80 in every cell (Round 36's S1 rule). 2,000 draws per cell.
Seeds: ML [20281301 + cell, draw]; LI Round 36's generators with seed 20281311.

Usage: scripts/methods73_validation.py --criterion-commit SHA [--workers N] [--smoke]
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
import pandas as pd  # noqa: E402

from census import index_core as ic, loadings_index_core as lc, multilevel3_core as m3  # noqa: E402
from census.simulation import make_replicates  # noqa: E402
import index_validation as r36  # noqa: E402

ML_SEED, LI_SEED = 20281301, 20281311
ML_CELLS = [(G, sh) for G in (30, 49) for sh in ((.70, .11, .19), (.50, .25, .25))]
LI_CELLS = [(rel, dist) for rel in (.9, .7) for dist in (0, 100)]
LOADINGS = np.array([.9, .8, .6, .5, .7])
M1_DRAWS, M3_DRAWS, LI_DRAWS = 1000, 100, 2000
FROZEN = ["scripts/methods73_validation.py", "census/multilevel3_core.py", "census/loadings_index_core.py",
          "census/index_core.py", "census/simulation.py", "scripts/index_validation.py",
          "docs/audits/methods73_validation_criterion.md"]
OUT = ROOT/"docs/audits/methods73_validation"


def ml_design(cell):
    G, _ = ML_CELLS[cell]
    rng = np.random.default_rng([ML_SEED+cell, 999999])
    mids = rng.integers(10, 31, G)
    rows = []
    mid_id = 0
    for g in range(G):
        for _ in range(mids[g]):
            rows += [(g, mid_id)]*int(rng.integers(5, 16)); mid_id += 1
    return pd.DataFrame(rows, columns=["top", "mid"])


def ml_job(args):
    cell, start, stop, jack = args
    G, (sb, sm, st) = ML_CELLS[cell]
    d0 = ml_design(cell)
    top, mid = d0.top.to_numpy(), d0.mid.to_numpy()
    hit = fail = 0; share_hit = {"bottom": 0, "mid": 0, "top": 0}; share_fail = 0
    for d in range(start, stop):
        rng = np.random.default_rng([ML_SEED+cell, d])
        x = rng.standard_normal(len(d0))
        y = 1+.5*x+rng.standard_normal(G)[top]*np.sqrt(st)+rng.standard_normal(mid.max()+1)[mid]*np.sqrt(sm) \
            + rng.standard_normal(len(d0))*np.sqrt(sb)
        data = d0.assign(y=y, x=x)
        try:
            if jack:
                iv = m3.jackknife_shares(data, "y ~ x", "top", "mid")
                for k, true in (("bottom", sb), ("mid", sm), ("top", st)):
                    share_hit[k] += iv[k]["lower"] <= true <= iv[k]["upper"]
            else:
                m, _ = m3.fit3(data, "y ~ x", "top", "mid")
                t = m3.fixed_intervals(m, G).set_index("term").loc["x"]
                hit += t.lower <= .5 <= t.upper
        except Exception:  # noqa: BLE001 - a failed fit counts as non-coverage
            if jack:
                share_fail += 1
            else:
                fail += 1
    return ("ML", cell, jack, hit, fail, share_hit, share_fail)


def li_job(args):
    cell, start, stop = args
    rel, dist = LI_CELLS[cell]
    rng_setup = r36.setup(r36.CELLS.index((rel, dist, "pca")))
    _, L, se = rng_setup
    n = len(L)
    per_area = np.zeros(n); fails = 0
    for d in range(start, stop):
        rng = np.random.default_rng([LI_SEED+cell, d])
        t = r36.true_ind(rng, L, n)
        obs = t+rng.standard_normal((n, 5))@np.linalg.cholesky(r36.CORR).T*se
        reps = make_replicates(obs, se, np.random.default_rng([LI_SEED+cell, d, 7]), corr=r36.CORR)
        try:
            (sc, sd, lo, hi), (m, s) = lc.scores_and_intervals(obs, reps, LOADINGS)
            target = ic.scores(t, m, s, LOADINGS)
            per_area += (lo <= target) & (target <= hi)
        except (ValueError, np.linalg.LinAlgError):
            fails += 1
    return ("LI", cell, per_area, fails)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--criterion-commit"); ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    if not a.smoke:
        subprocess.run(["git", "merge-base", "--is-ancestor", a.criterion_commit, "HEAD"], cwd=ROOT, check=True)
        for rel in FROZEN:
            if subprocess.check_output(["git", "show", a.criterion_commit+":"+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
                raise SystemExit("differs from criterion commit: "+rel)
    d1, d3, dl = (2, 1, 3) if a.smoke else (M1_DRAWS, M3_DRAWS, LI_DRAWS)
    tasks = [("ML", c, s, min(s+25, d1), False) for c in range(len(ML_CELLS)) for s in range(0, d1, 25)]
    tasks += [("ML", c, s, min(s+2, d3), True) for c in range(len(ML_CELLS)) for s in range(0, d3, 2)]
    tasks += [("LI", c, s, min(s+100, dl)) for c in range(len(LI_CELLS)) for s in range(0, dl, 100)]
    ml = {c: [0, 0] for c in range(len(ML_CELLS))}; jk = {c: [{"bottom": 0, "mid": 0, "top": 0}, 0] for c in range(len(ML_CELLS))}
    li = {c: [None, 0] for c in range(len(LI_CELLS))}
    t0 = time.time()
    with ProcessPoolExecutor(a.workers) as ex:
        futs = [ex.submit(ml_job if t[0] == "ML" else li_job, t[1:]) for t in tasks]
        for f in futs:
            r = f.result()
            if r[0] == "ML":
                _, c, jack, hit, fail, sh, sf = r
                if jack:
                    for k in sh:
                        jk[c][0][k] += sh[k]
                    jk[c][1] += sf
                else:
                    ml[c][0] += hit; ml[c][1] += fail
            else:
                _, c, pa, fails = r
                li[c][0] = pa if li[c][0] is None else li[c][0]+pa; li[c][1] += fails
            print({"done": r[0], "cell": r[1], "s": round(time.time()-t0)}, flush=True)
    ml_rows = [dict(G=ML_CELLS[c][0], shares=ML_CELLS[c][1], m1_coverage=ml[c][0]/d1, m1_failed=ml[c][1],
                    m3_coverage={k: v/d3 for k, v in jk[c][0].items()}, m3_failed=jk[c][1]) for c in ml]
    li_rows = [dict(reliability=LI_CELLS[c][0], range_km=LI_CELLS[c][1], mean=float(li[c][0].mean()/dl),
                    min=float(li[c][0].min()/dl), failed=li[c][1]) for c in li]
    passed = dict(M1=bool(all(r["m1_coverage"] >= .86 for r in ml_rows)),
                  M3_screen=bool(all(min(r["m3_coverage"].values()) >= .86 for r in ml_rows)),
                  LI=bool(all(r["mean"] >= .86 and r["min"] >= .80 for r in li_rows)))
    res = dict(ml=ml_rows, li=li_rows, passed=passed, draws=dict(M1=d1, M3=d3, LI=dl), criterion_commit=a.criterion_commit,
               frozen_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FROZEN})
    if a.smoke:
        print(json.dumps(passed), round(time.time()-t0)); return
    OUT.with_suffix(".json").write_text(json.dumps(res, indent=1, default=float)+"\n")
    L = ["# Round 73: three-level models and fixed-loading indices", "", f"Criterion commit: `{a.criterion_commit}`.", "",
         "| G_top | Shares (bottom, mid, top) | M1 slope coverage | M3 share coverage (screening, 100 draws) |",
         "| ---: | :--- | ---: | :--- |"]
    for r in ml_rows:
        L.append(f"| {r['G']} | {r['shares']} | {r['m1_coverage']:.4f} | " +
                 ", ".join(f"{k} {v:.2f}" for k, v in r["m3_coverage"].items())+" |")
    L += ["", "| Reliability | Range km | Mean per-area coverage | Lowest area |", "| ---: | ---: | ---: | ---: |"]
    L += [f"| {r['reliability']} | {r['range_km']} | {r['mean']:.4f} | {r['min']:.4f} |" for r in li_rows]
    L += ["", f"Outcomes: `{json.dumps(passed)}` (M3 is a screening result; it stays exploratory).", ""]
    OUT.with_suffix(".md").write_text("\n".join(L))
    print(json.dumps(passed))


if __name__ == "__main__":
    main()
