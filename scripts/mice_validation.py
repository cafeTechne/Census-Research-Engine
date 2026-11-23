# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 100: multiple imputation by FCS (frozen with the criterion, docs/audits/mice_validation_criterion.md).

Usage: scripts/mice_validation.py --criterion-commit SHA [--workers N] [--smoke]
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
from scipy import stats  # noqa: E402

from census import mice_core as mc  # noqa: E402

CELLS = [(n, c) for n in (145, 600) for c in (-2.6, -.5)]
TRUE = np.array([.5, .02, -.3])
DRAWS, CHUNK = 1000, 10
FROZEN = ["scripts/mice_validation.py", "census/mice_core.py", "docs/audits/mice_validation_criterion.md"]
OUT = ROOT/"docs/audits/mice_validation"


def data(rng, n, c):
    x3 = rng.normal(size=n); x1 = .5*x3+rng.normal(size=n); x2 = 100*rng.beta(2, 5, n)+5*x3
    y = 1+.5*x1+.02*x2-.3*x3+rng.normal(size=n)
    D = np.column_stack([y, x1, x2, x3])
    for j in (0, 1, 2):
        D[rng.random(n) < 1/(1+np.exp(-(c+x3))), j] = np.nan
    return D


def job(args):
    cell, start, stop = args
    n, c = CELLS[cell]
    acc = {k: np.zeros(3) for k in ("pmm", "norm", "cc")}; bias = {k: np.zeros(3) for k in acc}; fmi = 0.; miss = 0.; fails = 0
    for d in range(start, stop):
        rng = np.random.default_rng([20283001, cell, d])
        D = data(rng, n, c); miss += np.isnan(D[:, :3]).mean()
        try:
            for meth in ("pmm", "norm"):
                imps = mc.mice(D, {0: meth, 1: meth, 2: meth}, m=20, cycles=10, rng=rng)
                fits = [mc.ols(Z, 0, [1, 2, 3]) for Z in imps]
                p = mc.pool([f[0] for f in fits], [f[1] for f in fits], fits[0][2])
                acc[meth] += (p["lower"][1:] <= TRUE) & (TRUE <= p["upper"][1:]); bias[meth] += p["estimate"][1:]-TRUE
                if meth == "pmm":
                    fmi += float(np.mean(p["fmi"][1:]))
            cc = D[~np.isnan(D).any(1)]
            b, v, df = mc.ols(cc, 0, [1, 2, 3]); t = stats.t.ppf(.95, df)
            acc["cc"] += (b[1:]-t*np.sqrt(v[1:]) <= TRUE) & (TRUE <= b[1:]+t*np.sqrt(v[1:])); bias["cc"] += b[1:]-TRUE
        except (ValueError, np.linalg.LinAlgError):
            fails += 1
    return cell, {k: v.tolist() for k, v in acc.items()}, {k: v.tolist() for k, v in bias.items()}, fmi, miss, fails


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
    tasks = [(c, s, min(s+ch, draws)) for c in range(len(CELLS)) for s in range(0, draws, ch)]
    agg = {}
    with ProcessPoolExecutor(a.workers) as ex:
        for cell, acc, bias, fmi, miss, fails in ex.map(job, tasks, chunksize=1):
            g = agg.setdefault(cell, dict(acc={k: np.zeros(3) for k in acc}, bias={k: np.zeros(3) for k in acc}, fmi=0., miss=0., fails=0))
            for k in acc:
                g["acc"][k] += acc[k]; g["bias"][k] += bias[k]
            g["fmi"] += fmi; g["miss"] += miss; g["fails"] += fails
    rows = []
    for c, g in sorted(agg.items()):
        n, cc = CELLS[c]
        rows.append(dict(N=n, intercept=cc, missing_share=g["miss"]/draws, fmi=g["fmi"]/draws, fails=g["fails"],
                         **{k: (g["acc"][k]/draws).tolist() for k in g["acc"]},
                         **{f"{k}_bias": (g["bias"][k]/draws).tolist() for k in g["bias"]}))
    outcome = {k: dict(passed=bool(min(min(r[k]) for r in rows) >= .86), min=float(min(min(r[k]) for r in rows)))
               for k in ("pmm", "norm")}
    out = dict(rows=rows, outcome=outcome, draws=draws, criterion_commit=a.criterion_commit, seconds=round(time.time()-t0),
               frozen_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FROZEN})
    if a.smoke:
        print(json.dumps(outcome), out["seconds"]); return
    OUT.with_suffix(".json").write_text(json.dumps(out, indent=1)+"\n")
    f3 = lambda v: "/".join(f"{x:.3f}" for x in v)  # noqa: E731
    L = ["# Round 100: multiple imputation by fully conditional specification", "", f"Criterion commit: `{a.criterion_commit}`. "
         f"{draws} draws per cell; m = 20; 90% intervals; coverage and bias for the x1/x2/x3 slopes. Author self-review, "
         "not independent.", "", "| Method | Outcome | Lowest coverage |", "| :--- | :--- | ---: |"]
    L += [f"| I1-{k} | {'pass' if v['passed'] else 'fail'} | {v['min']:.3f} |" for k, v in outcome.items()]
    L += ["", "| N | Share missing | Mean FMI | PMM | Norm | Complete cases | CC bias |", "| ---: | ---: | ---: | :--- | :--- | :--- | :--- |"]
    L += [f"| {r['N']} | {r['missing_share']:.2f} | {r['fmi']:.2f} | {f3(r['pmm'])} | {f3(r['norm'])} | {f3(r['cc'])} | "
          f"{f3(r['cc_bias'])} |" for r in rows]
    L.append("")
    OUT.with_suffix(".md").write_text("\n".join(L))
    print(json.dumps({k: v["passed"] for k, v in outcome.items()}))


if __name__ == "__main__":
    main()
