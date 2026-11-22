# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 91: IP-weighted marginal structural models with treatment-confounder feedback (frozen with the criterion,
docs/audits/msm_validation_criterion.md).

Usage: scripts/msm_validation.py --criterion-commit SHA [--workers N] [--smoke]
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
from scipy.special import expit  # noqa: E402

from census import msm_core as mc  # noqa: E402

CELLS = [(K, g, psi) for K in (12, 18) for g in (0., .5, 1.) for psi in (0., -2.)]
DRAWS, CHUNK, B, UNITS = 1000, 20, 200, 51
FROZEN = ["scripts/msm_validation.py", "census/msm_core.py", "docs/audits/msm_validation_criterion.md"]
OUT = ROOT/"docs/audits/msm_validation"
EST = {"M1": dict(), "M2": dict(truncate=True), "N1": dict(adjust_L=True), "N0": dict(unweighted=True)}


def panel(rng, K, g, psi, n=UNITS):
    L = np.zeros((n, K)); A = np.zeros((n, K)); Y = np.zeros((n, K))
    u = rng.standard_normal(n); e = rng.standard_normal(n)/np.sqrt(1-.25)
    for t in range(K):
        if t == 0:
            L[:, 0] = rng.standard_normal(n)
        else:
            L[:, t] = .6*L[:, t-1]+g*A[:, t-1]+rng.standard_normal(n)
            start = rng.random(n) < expit(-2.75+.8*L[:, t])
            A[:, t] = np.where(A[:, t-1] == 1, 1, start.astype(float))
            e = .5*e+rng.standard_normal(n)
        Y[:, t] = 10+.2*(t+1)+psi*A[:, t]+L[:, t]+u+e+.5*rng.standard_normal(n)
    unit = np.repeat(np.arange(n), K); year = np.tile(np.arange(1, K+1), n)
    return Y.ravel(), A.ravel(), L.ravel(), unit, year


def targets(g, psi):
    return np.array([psi, psi+g, psi+g*1.6])


def job(args):
    cell, start, stop = args
    K, g, psi = CELLS[cell]
    tg = targets(g, psi)
    cov = {k: np.zeros(3) for k in EST}; fail = {k: 0 for k in EST}; bias = {k: np.zeros(3) for k in EST}
    nb = {k: 0 for k in EST}; wmax = []
    for d in range(start, stop):
        Y, A, L, unit, year = panel(np.random.default_rng([20282911, cell, d]), K, g, psi)
        for k, kw in EST.items():
            try:
                r = mc.msm(Y, A, L, unit, year, K, B=B, rng=np.random.default_rng([20282912, cell, d]), **kw)
            except (ValueError, np.linalg.LinAlgError):
                fail[k] += 1
                continue
            lo, hi, est = map(np.asarray, (r["lower"], r["upper"], r["estimate"]))
            cov[k] += (lo <= tg) & (tg <= hi); bias[k] += est-tg; nb[k] += 1
            if k == "M1":
                wmax.append(r["max_weight"])
    return cell, {k: v.tolist() for k, v in cov.items()}, fail, {k: v.tolist() for k, v in bias.items()}, nb, wmax


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
        for i, (cell, cov, fail, bias, nb, wmax) in enumerate(ex.map(job, tasks, chunksize=1)):
            gg = agg.setdefault(cell, dict(cov={k: np.zeros(3) for k in EST}, fail={k: 0 for k in EST},
                                           bias={k: np.zeros(3) for k in EST}, nb={k: 0 for k in EST}, wmax=[]))
            for k in EST:
                gg["cov"][k] += cov[k]; gg["fail"][k] += fail[k]; gg["bias"][k] += bias[k]; gg["nb"][k] += nb[k]
            gg["wmax"] += wmax
            if i % 50 == 0:
                print({"done": i, "of": len(tasks), "s": round(time.time()-t0)}, flush=True)
    rows = []
    for c, gg in sorted(agg.items()):
        K, g, psi = CELLS[c]
        r = dict(K=K, feedback=g, psi=psi, targets=targets(g, psi).tolist(),
                 median_max_weight=float(np.median(gg["wmax"])) if gg["wmax"] else None)
        for k in EST:
            r[k] = (gg["cov"][k]/draws).tolist(); r[f"{k}_fail"] = gg["fail"][k]/draws
            r[f"{k}_bias"] = (gg["bias"][k]/max(1, gg["nb"][k])).tolist()
        rows.append(r)
    outcome = {k: dict(passed=min(min(r[k]) for r in rows) >= .86, min=min(min(r[k]) for r in rows)) for k in ("M1", "M2")}
    out = dict(rows=rows, outcome=outcome, draws=draws, criterion_commit=a.criterion_commit, seconds=round(time.time()-t0),
               frozen_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FROZEN})
    if a.smoke:
        print(json.dumps(outcome), out["seconds"]); print(json.dumps(rows[-1])); return
    OUT.with_suffix(".json").write_text(json.dumps(out, indent=1)+"\n")
    f3 = lambda v: "/".join(f"{x:.3f}" for x in v)  # noqa: E731
    L = ["# Round 91: IP-weighted marginal structural models with treatment-confounder feedback", "",
         f"Criterion commit: `{a.criterion_commit}`. {draws} draws per cell; 90% cluster-bootstrap intervals (B = {B}). "
         "Coverage and bias are given for durations 1/2/3. Author self-review, not independent.", "",
         "| Family | Outcome | Lowest coverage |", "| :--- | :--- | ---: |"]
    L += [f"| {k} | {'pass' if v['passed'] else 'fail'} | {v['min']:.3f} |" for k, v in outcome.items()]
    L += ["", "| K | Feedback | psi | M1 | M2 | N1 (adjust L) | N0 (none) | M1 bias | N1 bias | N0 bias |",
          "| ---: | ---: | ---: | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"]
    L += [f"| {r['K']} | {r['feedback']} | {r['psi']} | {f3(r['M1'])} | {f3(r['M2'])} | {f3(r['N1'])} | {f3(r['N0'])} | "
          f"{f3(r['M1_bias'])} | {f3(r['N1_bias'])} | {f3(r['N0_bias'])} |" for r in rows]
    L.append("")
    OUT.with_suffix(".md").write_text("\n".join(L))
    print(json.dumps({k: v["passed"] for k, v in outcome.items()}))


if __name__ == "__main__":
    main()
