# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 94: WHO inequality monitoring measures (frozen with the criterion,
docs/audits/inequality_monitoring_validation_criterion.md).

Usage: scripts/inequality_monitoring_validation.py --criterion-commit SHA [--workers N] [--smoke]
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

from census import inequality_monitoring_core as im  # noqa: E402
from census.simulation import make_replicates  # noqa: E402
from disparity_validation import gamma_copula, sigma  # noqa: E402

SEED = 20282941
R = np.array([.10, .22, .30, .16, .35, .26, .12, .20]); P = np.array([.55, .15, .10, .07, .05, .04, .02, .02])
X_CELLS = [(G, c, sp) for G in (4, 6, 8) for c in (.10, .30, .50) for sp in ("large", "small")]
T_CELLS = [(G, c, ch) for G in (4, 8) for c in (.10, .30) for ch in (0., .3)]
DRAWS, CHUNK = 2000, 100
FAMILIES = {"MDM": [("mdm_u", "decl"), ("mdm_w", "decl")], "MDB-declared": [("mdb_u", "decl"), ("mdb_w", "decl")],
            "PAR-declared": [("par", "decl"), ("par_pct", "decl")], "MDB-best": [("mdb_u", "best"), ("mdb_w", "best")],
            "PAR-best": [("par", "best"), ("par_pct", "best")], "SII": [("sii", "decl")]}
T_MEASURES = ("mdm_w", "mdb_w", "par", "sii")
FROZEN = ["scripts/inequality_monitoring_validation.py", "census/inequality_monitoring_core.py",
          "scripts/disparity_validation.py", "census/simulation.py",
          "docs/audits/inequality_monitoring_validation_criterion.md"]
OUT = ROOT/"docs/audits/inequality_monitoring_validation"


def truth(G, sp):
    r = R[:G] if sp == "large" else .2+(R[:G]-.2)/4
    p = P[:G]/P[:G].sum()
    return r, p


def cvs(G, c):
    p = P[:G]/P[:G].sum()
    cv = np.maximum(.05, c*np.sqrt(p.min()/p)); cv[0] = .05
    return cv


def draw(rng, r, p, cv, n):
    G = len(r); C = sigma(G); L = np.linalg.cholesky(C)
    z = rng.standard_normal((n, 2*G))@L.T
    pop = p*100000
    er = gamma_copula(r, cv, z[:, :G]); en = gamma_copula(pop, cv/2, z[:, G:])
    reps = make_replicates(np.hstack([er, en]), np.tile(np.hstack([r*cv, pop*cv/2]), (n, 1)), rng, corr=C)
    return er, en, reps[:, :G, :], reps[:, G:, :]


def ivs(er, en, rr, nr):
    return {"decl": im.replicate_intervals(er, en, rr, nr, 0), "best": im.replicate_intervals(er, en, rr, nr, "best")}


def x_chunk(cell, chunk, n):
    G, c, sp = X_CELLS[cell]
    r, p = truth(G, sp); cv = cvs(G, c)
    rng = np.random.default_rng([SEED, cell, chunk])
    iv = ivs(*draw(rng, r, p, cv, n))
    tgt = im.measures(r, p, 0)
    return {f"{m}|{ref}": int(((iv[ref][m]["lower"] <= tgt[m]) & (tgt[m] <= iv[ref][m]["upper"])).sum())
            for fam in FAMILIES.values() for m, ref in fam}


def t_chunk(cell, chunk, n):
    G, c, ch = T_CELLS[cell]
    r1, p = truth(G, "large"); rbar = (p*r1).sum(); r2 = rbar+(1-ch)*(r1-rbar); cv = cvs(G, c)
    rng = np.random.default_rng([SEED+1000, cell, chunk])
    a = im.replicate_intervals(*draw(rng, r1, p, cv, n), 0); b = im.replicate_intervals(*draw(rng, r2, p, cv, n), 0)
    d = im.change(a, b, measures_=T_MEASURES)
    t = {m: im.measures(r2, p, 0)[m]-im.measures(r1, p, 0)[m] for m in T_MEASURES}
    return {m: int(((d[m]["lower"] <= t[m]) & (t[m] <= d[m]["upper"])).sum()) for m in T_MEASURES}


def job(args):
    kind, cell, chunk, n = args
    return kind, cell, (x_chunk if kind == "x" else t_chunk)(cell, chunk, n)


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
    draws, ch = (40, 20) if a.smoke else (DRAWS, CHUNK)
    tasks = [(k, c, s//ch, min(ch, draws-s)) for k, cells in (("x", X_CELLS), ("t", T_CELLS))
             for c in range(len(cells)) for s in range(0, draws, ch)]
    agg = {}
    with ProcessPoolExecutor(a.workers) as ex:
        for kind, cell, res in ex.map(job, tasks, chunksize=1):
            d = agg.setdefault((kind, cell), {})
            for k, v in res.items():
                d[k] = d.get(k, 0)+v
    xrows = [dict(G=G, c=c, spread=sp, **{k: v/draws for k, v in agg[("x", i)].items()}) for i, (G, c, sp) in enumerate(X_CELLS)]
    trows = [dict(G=G, c=c, change=chg, **{k: v/draws for k, v in agg[("t", i)].items()}) for i, (G, c, chg) in enumerate(T_CELLS)]
    outcome = {}
    for fam, mem in FAMILIES.items():
        keys = [f"{m}|{ref}" for m, ref in mem]
        fails = [r for r in xrows if min(r[k] for k in keys) < .86]
        outcome[fam] = dict(passed=not fails, gated=bool(fails) and all(r["c"] == .50 for r in fails),
                            min=min(min(r[k] for k in keys) for r in xrows))
    tf = [r for r in trows if min(r[m] for m in T_MEASURES) < .86]
    outcome["T1"] = dict(passed=not tf, gated=False, min=min(min(r[m] for m in T_MEASURES) for r in trows))
    out = dict(cross_sectional=xrows, trend=trows, outcome=outcome, draws=draws, criterion_commit=a.criterion_commit,
               seconds=round(time.time()-t0), frozen_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FROZEN})
    if a.smoke:
        print(json.dumps(outcome), out["seconds"]); return
    OUT.with_suffix(".json").write_text(json.dumps(out, indent=1)+"\n")
    L = ["# Round 94: WHO inequality monitoring measures", "",
         f"Criterion commit: `{a.criterion_commit}`. {draws} draws per cell; 90% replicate intervals. Author self-review, "
         "not independent.", "", "| Family | Outcome | Lowest coverage |", "| :--- | :--- | ---: |"]
    L += [f"| {k} | {'pass' if v['passed'] else ('pass for c <= .30 (gate)' if v['gated'] else 'fail')} | {v['min']:.3f} |"
          for k, v in outcome.items()]
    keys = [f"{m}|{ref}" for mem in FAMILIES.values() for m, ref in mem]
    L += ["", "## Cross-sectional cells", "", "| G | c | Spread | "+" | ".join(keys)+" |", "| "+" | ".join(["---:"]*(3+len(keys)))+" |"]
    L += [f"| {r['G']} | {r['c']} | {r['spread']} | "+" | ".join(f"{r[k]:.3f}" for k in keys)+" |" for r in xrows]
    L += ["", "## Change between releases", "", "| G | c | Change | "+" | ".join(T_MEASURES)+" |", "| "+" | ".join(["---:"]*(3+len(T_MEASURES)))+" |"]
    L += [f"| {r['G']} | {r['c']} | {r['change']} | "+" | ".join(f"{r[m]:.3f}" for m in T_MEASURES)+" |" for r in trows]
    L.append("")
    OUT.with_suffix(".md").write_text("\n".join(L))
    print(json.dumps({k: (v["passed"], v["gated"]) for k, v in outcome.items()}))


if __name__ == "__main__":
    main()
