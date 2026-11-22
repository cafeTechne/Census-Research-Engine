# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 90: positivity diagnostics, stabilized/truncated/overlap weights and the g-formula (frozen with the criterion,
docs/audits/positivity_validation_criterion.md).

Usage: scripts/positivity_validation.py --criterion-commit SHA [--workers N] [--smoke]
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

from census import causal_core as cc  # noqa: E402
from census import positivity_core as pc  # noqa: E402

SEED = 20282991
CELLS = [(n, a, het) for n in (145, 600) for a in (.5, 1.502, 2.045) for het in (False, True)]
DRAWS, CHUNK = 2000, 100
FROZEN = ["scripts/positivity_validation.py", "census/positivity_core.py", "census/causal_core.py",
          "docs/audits/positivity_validation_criterion.md"]
OUT = ROOT/"docs/audits/positivity_validation"
KEYS = ("W1", "W2", "W3", "G1", "P0")


def draw(rng, n, a, het):
    z = rng.standard_normal((n, 2)); z[:, 1] = .3*z[:, 0]+np.sqrt(.91)*z[:, 1]
    e = expit(a*(z[:, 0]-z[:, 1])/np.sqrt(1.4))
    T = rng.binomial(1, e)
    tau = .5+.5*z[:, 0] if het else np.full(n, .5)
    y = 1+tau*T+.5*z[:, 0]+.5*z[:, 1]+rng.standard_normal(n)
    return y, T, z, e


def overlap_target(a, het):
    rng = np.random.default_rng([20282990, int(1000*a), het])
    z = rng.standard_normal((2_000_000, 2)); z[:, 1] = .3*z[:, 0]+np.sqrt(.91)*z[:, 1]
    e = expit(a*(z[:, 0]-z[:, 1])/np.sqrt(1.4)); h = e*(1-e)
    tau = .5+.5*z[:, 0] if het else np.full(len(e), .5)
    return float(np.sum(h*tau)/np.sum(h)), float(np.mean((e < .05) | (e > .95)))


def job(args):
    cell, start, stop, ato = args
    n, a, het = CELLS[cell]
    cov = {k: 0 for k in KEYS}; fail = {k: 0 for k in KEYS}; flag = 0; est = {k: [] for k in KEYS}; outside = []
    for d in range(start, stop):
        rng = np.random.default_rng([SEED, cell, d])
        y, T, z, e = draw(rng, n, a, het)
        outside.append(float(np.mean((e < .05) | (e > .95))))
        res = {}
        for k, fn in (("W1", lambda: pc.weighted_effect(y, T, z, "stabilized")[0]),
                      ("W2", lambda: pc.weighted_effect(y, T, z, "truncated")[0]),
                      ("W3", lambda: pc.weighted_effect(y, T, z, "overlap")[0]),
                      ("G1", lambda: pc.g_formula(y, T, z)), ("P0", lambda: cc.treatment_effect(y, T, z, "ipw"))):
            try:
                if min(T.sum(), n-T.sum()) < 10:
                    raise ValueError("fewer than 10 areas in a group")
                res[k] = fn()
            except (ValueError, np.linalg.LinAlgError, FloatingPointError):
                fail[k] += 1
                continue
            target = ato if k == "W3" else .5
            cov[k] += int(res[k]["lower"] <= target <= res[k]["upper"])
            est[k].append(res[k]["estimate"]-target)
        flag += int(not ("W1" in res and "G1" in res) or pc.agreement(res["W1"], res["G1"])["flagged"])
    return cell, cov, fail, flag, {k: (float(np.sum(v)), float(np.sum(np.square(v))), len(v)) for k, v in est.items()}, outside


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
    keys = sorted({(ac, het) for _, ac, het in CELLS})
    with ProcessPoolExecutor(min(a.workers, 6)) as ex:
        targets = dict(zip(keys, ex.map(overlap_target, *zip(*keys))))
    draws, ch = (20, 10) if a.smoke else (DRAWS, CHUNK)
    tasks = [(c, s, min(s+ch, draws), targets[(CELLS[c][1], CELLS[c][2])][0])
             for c in range(len(CELLS)) for s in range(0, draws, ch)]
    agg = {}
    with ProcessPoolExecutor(a.workers) as ex:
        for cell, cov, fail, flag, est, outside in ex.map(job, tasks, chunksize=1):
            g = agg.setdefault(cell, dict(cov={k: 0 for k in KEYS}, fail={k: 0 for k in KEYS}, flag=0,
                                          est={k: [0., 0., 0] for k in KEYS}, outside=[]))
            for k in KEYS:
                g["cov"][k] += cov[k]; g["fail"][k] += fail[k]
                for i in range(3):
                    g["est"][k][i] += est[k][i]
            g["flag"] += flag; g["outside"] += outside
    rows = []
    for c, g in sorted(agg.items()):
        n, ac, het = CELLS[c]
        r = dict(N=n, a=ac, heterogeneous=het, share_outside=float(np.mean(g["outside"])),
                 overlap_target=targets[(ac, het)][0], flag_rate=g["flag"]/draws)
        for k in KEYS:
            s, ss, m = g["est"][k]
            r[k] = g["cov"][k]/draws; r[f"{k}_fail"] = g["fail"][k]/draws
            r[f"{k}_bias"] = s/m if m else None; r[f"{k}_rmse"] = float(np.sqrt(ss/m)) if m else None
        rows.append(r)
    outcome = {k: dict(passed=min(r[k] for r in rows) >= .86, min=min(r[k] for r in rows)) for k in ("W1", "W2", "W3", "G1")}
    outcome["flag"] = dict(passed=max(r["flag_rate"] for r in rows) <= .10, max=max(r["flag_rate"] for r in rows))
    out = dict(rows=rows, outcome=outcome, draws=draws, criterion_commit=a.criterion_commit, seconds=round(time.time()-t0),
               targets={str(k): v for k, v in targets.items()},
               frozen_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FROZEN})
    if a.smoke:
        print(json.dumps(outcome), out["seconds"]); print(json.dumps(rows[-1])); return
    OUT.with_suffix(".json").write_text(json.dumps(out, indent=1)+"\n")
    L = ["# Round 90: positivity, stabilized/truncated/overlap weights and the g-formula", "",
         f"Criterion commit: `{a.criterion_commit}`. {draws} draws per cell; 90% sandwich intervals. Author "
         "self-review, not independent.", "", "| Family | Outcome | Worst cell |", "| :--- | :--- | ---: |"]
    for k, v in outcome.items():
        L.append(f"| {k} | {'pass' if v['passed'] else 'fail'} | {v.get('min', v.get('max')):.3f} |")
    L += ["", "| N | a | Heterogeneous | Outside [.05,.95] | W1 | W2 | W3 | G1 | P0 (plain IPW) | Flag rate | W1 bias | W2 bias |",
          "| ---: | ---: | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    L += [f"| {r['N']} | {r['a']} | {r['heterogeneous']} | {r['share_outside']:.3f} | {r['W1']:.3f} | {r['W2']:.3f} | "
          f"{r['W3']:.3f} | {r['G1']:.3f} | {r['P0']:.3f} | {r['flag_rate']:.3f} | {r['W1_bias']:.3f} | {r['W2_bias']:.3f} |"
          for r in rows]
    L += ["", "Failures (non-convergence, propensity 0 or 1) count as non-coverage; failure rates are in the JSON.", ""]
    OUT.with_suffix(".md").write_text("\n".join(L))
    print(json.dumps({k: v["passed"] for k, v in outcome.items()}))


if __name__ == "__main__":
    main()
