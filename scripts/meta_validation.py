# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 102: meta-analysis completeness (frozen with the criterion, docs/audits/meta_validation_criterion.md).

Usage: scripts/meta_validation.py --criterion-commit SHA [--workers N] [--smoke]
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

from census import meta_core as mc  # noqa: E402

P_CELLS = [(k, i2) for k in (4, 5, 10, 20, 40) for i2 in (0., .25, .5, .75)]
R_CELLS = [(k, i2, b) for k in (10, 20, 40) for i2 in (0., .5) for b in (0., .2)]
P_DRAWS, R_DRAWS, CHUNK = 4000, 1000, 100
FROZEN = ["scripts/meta_validation.py", "census/meta_core.py", "census/evidence_core.py", "docs/audits/meta_validation_criterion.md"]
OUT = ROOT/"docs/audits/meta_validation"


def design(cell, k, i2):
    rng = np.random.default_rng([20283021, cell])
    v = (.1*10**rng.uniform(0, 1, k))**2
    w = 1/v; vt = (k-1)*w.sum()/(w.sum()**2-np.sum(w**2))
    return v, (i2/(1-i2)*vt if i2 < 1 else 0.0)


def p_job(cell, start, stop):
    k, i2 = P_CELLS[cell]; v, t2 = design(cell, k, i2)
    acc = {"P1-PM": 0, "P1-REML": 0, "H1": 0, "E1": 0, "mean": 0}
    for d in range(start, stop):
        rng = np.random.default_rng([20283022, cell, d])
        th = .3+rng.normal(0, np.sqrt(t2), k); y = th+rng.normal(0, np.sqrt(v)); new = .3+rng.normal(0, np.sqrt(t2))
        a = mc.meta(y, v, "pm"); b = mc.meta(y, v, "reml"); lo, hi = mc.q_profile(y, v)
        acc["P1-PM"] += a["pi_lower"] <= new <= a["pi_upper"]; acc["P1-REML"] += b["pi_lower"] <= new <= b["pi_upper"]
        acc["H1"] += lo <= t2 <= hi; acc["mean"] += a["lower"] <= .3 <= a["upper"]
        acc["E1"] += mc.egger(y, v)["p"] < .10 if k >= 3 else 0
    return acc


def r_job(cell, start, stop):
    k, i2, beta = R_CELLS[cell]; v, t2 = design(100+cell, k, i2)
    acc = {"R1": 0, "R1_perm": 0}
    for d in range(start, stop):
        rng = np.random.default_rng([20283023, cell, d])
        x = rng.normal(size=k); y = .3+beta*x+rng.normal(0, np.sqrt(t2), k)+rng.normal(0, np.sqrt(v))
        r = mc.meta_regression(y, v, x, perms=199, rng=rng)
        acc["R1"] += r["lower"][1] <= beta <= r["upper"][1]; acc["R1_perm"] += r["p_permutation"][1] < .10
    return acc


def job(args):
    kind, cell, start, stop = args
    return kind, cell, (p_job if kind == "p" else r_job)(cell, start, stop)


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
    pd_, rd_, ch = (20, 4, 10) if a.smoke else (P_DRAWS, R_DRAWS, CHUNK)
    tasks = [("p", c, s, min(s+ch, pd_)) for c in range(len(P_CELLS)) for s in range(0, pd_, ch)]
    tasks += [("r", c, s, min(s+ch, rd_)) for c in range(len(R_CELLS)) for s in range(0, rd_, ch)]
    agg = {}
    with ProcessPoolExecutor(a.workers) as ex:
        for kind, cell, res in ex.map(job, tasks, chunksize=1):
            g = agg.setdefault((kind, cell), {})
            for k_, v_ in res.items():
                g[k_] = g.get(k_, 0)+int(v_)
    prows = [dict(k=k, I2=i2, **{kk: vv/pd_ for kk, vv in agg[("p", i)].items()}) for i, (k, i2) in enumerate(P_CELLS)]
    rrows = [dict(k=k, I2=i2, beta=b, **{kk: vv/rd_ for kk, vv in agg[("r", i)].items()}) for i, (k, i2, b) in enumerate(R_CELLS)]
    outcome = {}
    for key in ("P1-PM", "P1-REML"):
        fails = [r for r in prows if r[key] < .86]
        outcome[key] = dict(passed=not fails, gated=bool(fails) and all(r["k"] < 10 for r in fails),
                            min_k10=float(min(r[key] for r in prows if r["k"] >= 10)))
    outcome["H1"] = dict(passed=bool(min(r["H1"] for r in prows) >= .86), min=float(min(r["H1"] for r in prows)))
    outcome["R1"] = dict(passed=bool(min(r["R1"] for r in rrows) >= .86 and max(r["R1_perm"] for r in rrows if r["beta"] == 0) <= .10),
                         min=float(min(r["R1"] for r in rrows)), perm_size=float(max(r["R1_perm"] for r in rrows if r["beta"] == 0)))
    outcome["E1"] = dict(passed=bool(max(r["E1"] for r in prows if r["k"] >= 10) <= .10),
                         max=float(max(r["E1"] for r in prows if r["k"] >= 10)))
    out = dict(pooling=prows, regression=rrows, outcome=outcome, criterion_commit=a.criterion_commit, seconds=round(time.time()-t0),
               frozen_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FROZEN})
    if a.smoke:
        print(json.dumps(outcome), out["seconds"]); return
    OUT.with_suffix(".json").write_text(json.dumps(out, indent=1)+"\n")
    lab = lambda v: "pass" if v["passed"] else ("pass from k = 10 (gate)" if v.get("gated") else "fail")  # noqa: E731
    L = ["# Round 102: meta-analysis completeness", "", f"Criterion commit: `{a.criterion_commit}`. {P_DRAWS} draws per pooling "
         f"cell, {R_DRAWS} per meta-regression cell; 90% intervals. Author self-review, not independent.", "",
         "| Method | Outcome |", "| :--- | :--- |"] + [f"| {k} | {lab(v)} |" for k, v in outcome.items()]
    L += ["", "| k | I2 | P1-PM | P1-REML | H1 (tau2) | HK mean | E1 rejection |", "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    L += [f"| {r['k']} | {r['I2']} | {r['P1-PM']:.3f} | {r['P1-REML']:.3f} | {r['H1']:.3f} | {r['mean']:.3f} | {r['E1']:.3f} |" for r in prows]
    L += ["", "| k | I2 | beta | R1 coverage | Permutation rejection at .10 |", "| ---: | ---: | ---: | ---: | ---: |"]
    L += [f"| {r['k']} | {r['I2']} | {r['beta']} | {r['R1']:.3f} | {r['R1_perm']:.3f} |" for r in rrows]
    L.append("")
    OUT.with_suffix(".md").write_text("\n".join(L))
    print(json.dumps({k: v["passed"] for k, v in outcome.items()}))


if __name__ == "__main__":
    main()
