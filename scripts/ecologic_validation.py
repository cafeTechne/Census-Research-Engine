# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 87: ecologic versus individual-level associations on PUMS (frozen with the criterion,
docs/audits/ecologic_validation_criterion.md).

Population: Round 32 sampling (scripts/pums_tests_validation.py: households at g in [0, 1], weight CV 1, household
latent share .25, SDR factors); areas (PUMA-like) are J equal-width bins of g. Persons: area mean of exposure
mu_j = sin(2 pi g_j) (bin midpoint) scaled to SD 1 across areas; x_i = mu_j + e_i (e ~ N(0, 1), household-correlated);
y_i = .5 x_i + c mu_j + k u_j + N(0, 1) with u_j = mu_j (area confounder, "on": k = .3, "off": k = 0) and
contextual c in {0, .25}; binary outcome y_i = 1{-1.2 + the same index + Logistic > 0}.
Cells (32): J in {30, 150} x records in {5,000, 30,000} x c in {0, .25} x confounding {off, on} x outcome
{continuous, binary}. 1,000 draws per cell. Targets: the same estimators on a reference population of 300,000
households with unit weights (per J, c, confounding, outcome).
Judged: C1 (linear; risk-difference scale for binary) within, between, contextual; C2 ecologic slope and the ecologic
gap (C2 - C1 within); C1l (logit, binary cells) within, between, contextual. Pass per family (C1, C2/gap, C1l):
90% coverage >= .86 in every applicable cell. Gate: a family failing only at 5,000 records is validated from 30,000.
Seeds: reference [20282701, J, c, conf, outcome]; draws [20282711 + cell, draw].

Usage: scripts/ecologic_validation.py --criterion-commit SHA [--workers N] [--smoke]
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
from census import ecologic_core as ec  # noqa: E402
from census import pums_tests as pt  # noqa: E402

SEED = 20282701
CELLS = [(J, n, c, conf, out) for J in (30, 150) for n in (5000, 30000) for c in (0.0, .25)
         for conf in ("off", "on") for out in ("continuous", "binary")]
DRAWS, CHUNK = 1000, 20
FROZEN = ["scripts/ecologic_validation.py", "census/ecologic_core.py", "scripts/pums_tests_validation.py",
          "census/pums_tests.py", "docs/audits/ecologic_validation_criterion.md"]
OUT = ROOT/"docs/audits/ecologic_validation"


def persons(rng, g, J, c, conf, out):
    H = len(g); size = 1+rng.poisson(1.5, H); idx = np.repeat(np.arange(H), size); n = len(idx)
    area = np.minimum((g[idx]*J).astype(int), J-1)
    mids = (np.arange(J)+.5)/J
    mu = np.sin(2*np.pi*mids); mu = (mu-mu.mean())/mu.std()
    e = np.sqrt(.25)*rng.standard_normal(H)[idx]+np.sqrt(.75)*rng.standard_normal(n)
    x = mu[area]+e
    k = .3 if conf == "on" else 0.0
    index = .5*x+c*mu[area]+k*mu[area]
    if out == "continuous":
        y = index+rng.standard_normal(n)
    else:
        y = (-1.2+index+rng.logistic(0, 1, n) > 0).astype(float)
    return idx, area, x, y


def reference(J, c, conf, out):
    rng = np.random.default_rng([SEED, J, int(100*c), conf == "on", out == "binary"])
    _, area, x, y = persons(rng, rng.uniform(0, 1, 300000), J, c, conf, out)
    W = np.ones((len(y), 2))
    t = {k: v[0] for k, v in ec.decompose(y, x, area, W)[0].items()}
    if out == "binary":
        t.update({f"logit_{k}": v[0] for k, v in ec.decompose(y, x, area, W, logit=True)[0].items()})
    return t


def job(args):
    cell, start, stop, ref = args
    J, size, c, conf, out = CELLS[cell]
    sigma = r32.sigma_for(1.0); m = int(size/2.5)+1
    acc = {}
    for d in range(start, stop):
        rng = np.random.default_rng([SEED+10+cell, d])
        u = rng.uniform(0, 1, m)
        pi = np.exp(sigma*r32.field(r32.GRID)); cdf = np.cumsum(pi); cdf /= cdf[-1]
        g = np.sort(np.interp(u, cdf, r32.GRID)); w = 1/np.exp(sigma*r32.field(g))
        idx, area, x, y = persons(rng, g, J, c, conf, out)
        W = (w[:, None]*np.column_stack((np.ones(m), pt.sdr_factors(m))))[idx]
        res = {k: v for k, v in ec.decompose(y, x, area, W)[0].items()}
        if out == "binary":
            res.update({f"logit_{k}": v for k, v in ec.decompose(y, x, area, W, logit=True)[0].items()})
        for k, (est, se, lo, hi) in res.items():
            acc[k] = acc.get(k, 0)+int(lo <= ref[k] <= hi)
    return cell, acc


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--criterion-commit"); ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    if not a.smoke:
        subprocess.run(["git", "merge-base", "--is-ancestor", a.criterion_commit, "HEAD"], cwd=ROOT, check=True)
        for rel in FROZEN:
            if subprocess.check_output(["git", "show", a.criterion_commit+":"+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
                raise SystemExit("differs from criterion commit: "+rel)
    t0 = time.time()
    keys = sorted({(J, c, conf, out) for J, _, c, conf, out in CELLS})
    with ProcessPoolExecutor(min(a.workers, 8)) as ex:
        refs = dict(zip(keys, ex.map(reference, *zip(*keys))))
    print({"references_s": round(time.time()-t0)}, flush=True)
    draws, ch = (2, 1) if a.smoke else (DRAWS, CHUNK)
    tasks = [(cl, s, min(s+ch, draws), refs[(CELLS[cl][0], CELLS[cl][2], CELLS[cl][3], CELLS[cl][4])])
             for cl in range(len(CELLS)) for s in range(0, draws, ch)]
    acc = {}
    with ProcessPoolExecutor(a.workers) as ex:
        for i, (cell, r) in enumerate(ex.map(job, tasks, chunksize=1)):
            dd = acc.setdefault(cell, {})
            for k, v in r.items():
                dd[k] = dd.get(k, 0)+v
            if i % 200 == 0:
                print({"done": i, "of": len(tasks), "s": round(time.time()-t0)}, flush=True)
    rows = [dict(J=CELLS[c][0], records=CELLS[c][1], context_effect=CELLS[c][2], confounding=CELLS[c][3], outcome=CELLS[c][4],
                 **{k: v/draws for k, v in r.items()}) for c, r in sorted(acc.items())]
    fams = {"C1": ("within", "between", "contextual"), "C2": ("ecologic", "ecologic_gap"),
            "C1l": ("logit_within", "logit_between", "logit_contextual")}
    outcome = {}
    for f, ks in fams.items():
        sub = [r for r in rows if all(k in r for k in ks)]
        fails = [r for r in sub if min(r[k] for k in ks) < .86]
        outcome[f] = dict(passed=not fails, gated=bool(fails) and all(r["records"] == 5000 for r in fails),
                          min=min(min(r[k] for k in ks) for r in sub), cells=len(sub))
    out = dict(rows=rows, outcome=outcome, references={str(k): v for k, v in refs.items()}, draws=draws,
               criterion_commit=a.criterion_commit, seconds=round(time.time()-t0),
               frozen_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FROZEN})
    if a.smoke:
        print(json.dumps({k: v["passed"] for k, v in outcome.items()}), out["seconds"]); return
    OUT.with_suffix(".json").write_text(json.dumps(out, indent=1, default=float)+"\n")
    L = ["# Round 87: ecologic versus individual-level associations on PUMS", "",
         f"Criterion commit: `{a.criterion_commit}`. {draws} draws per cell; 90% SDR intervals. Author self-review, "
         "not independent.", "", "| Family | Outcome | Lowest coverage | Cells |", "| :--- | :--- | ---: | ---: |"]
    for k, v in outcome.items():
        L.append(f"| {k} | {'pass' if v['passed'] else ('pass with gate (30,000 records)' if v['gated'] else 'fail')} | "
                 f"{v['min']:.3f} | {v['cells']} |")
    L += ["", "| J | Records | Contextual | Confounding | Outcome | Coverage |", "| ---: | ---: | ---: | :--- | :--- | :--- |"]
    L += [f"| {r['J']} | {r['records']} | {r['context_effect']} | {r['confounding']} | {r['outcome']} | "
          + ", ".join(f"{k} {r[k]:.3f}" for k in r if k not in ("J", "records", "context_effect", "confounding", "outcome"))+" |"
          for r in rows]
    L.append("")
    OUT.with_suffix(".md").write_text("\n".join(L))
    print(json.dumps({k: (v["passed"], v["gated"]) for k, v in outcome.items()}))


if __name__ == "__main__":
    main()
