# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 95: YPLL intervals and aberration detection (frozen with the criterion,
docs/audits/surveillance_validation_criterion.md).

Usage: scripts/surveillance_validation.py --criterion-commit SHA [--workers N] [--smoke]
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

from census import surveillance_core as sc  # noqa: E402
from census.standardize import standard_weights  # noqa: E402

SEED = 20282951
BANDS = [(0, 0), (1, 4), (5, 14), (15, 24), (25, 34), (35, 44), (45, 54), (55, 64), (65, 74)]
RATES = {"all_cause": np.array([550, 24, 13, 80, 130, 200, 380, 850, 1700])/1e5,
         "overdose": np.array([.5, .3, .3, 10, 35, 40, 35, 25, 8])/1e5}
Y_CELLS = [(tot, cause) for tot in (30_000, 200_000, 5_000_000) for cause in RATES]
A_CELLS = [(pop, tr, od, mult) for pop in (100_000, 1_000_000) for tr in (0., .03) for od in (0., .10) for mult in (1., 1.5, 2.)]
DRAWS, CHUNK = 2000, 100
FROZEN = ["scripts/surveillance_validation.py", "census/surveillance_core.py", "census/standardize.py",
          "docs/audits/surveillance_validation_criterion.md"]
OUT = ROOT/"docs/audits/surveillance_validation"


def pops(total):
    # 2000 standard shares of the bands (over all ages), scaled to the total of these bands
    w = np.array(standard_weights([[lo, hi] for lo, hi in BANDS]+[[75, None]]))[:-1]
    return total*w/w.sum()


def y_chunk(cell, chunk, n):
    tot, cause = Y_CELLS[cell]
    p = pops(tot); r = RATES[cause]
    tgt = sc.ypll(r*p, p, BANDS, 75)["adjusted_rate"]
    rng = np.random.default_rng([SEED, cell, chunk]); cov = 0
    for _ in range(n):
        d = rng.poisson(r*p).astype(float)
        out = sc.ypll(d, p, BANDS, 75)
        cov += out["lower"] <= tgt <= out["upper"]
    return dict(Y1=int(cov))


def a_chunk(cell, chunk, n):
    pop, tr, od, mult = A_CELLS[cell]
    rng = np.random.default_rng([SEED+1, cell, chunk])
    mu = 20e-5*pop*(1+tr)**np.arange(15); mu[-1] *= mult
    a1 = a2 = 0
    for _ in range(n):
        lam = mu*(rng.gamma(1/od**2, od**2, 15) if od > 0 else 1)
        c = rng.poisson(lam).astype(float); r = c/pop*1e5
        a1 += sc.historical_limits(r, np.sqrt(c[-1])/pop*1e5)["flag"] == "high"
        a2 += sc.ears_c2(r)["flag"] == "high"
    return dict(A1=int(a1), A2=int(a2))


def job(args):
    kind, cell, chunk, n = args
    return kind, cell, (y_chunk if kind == "y" else a_chunk)(cell, chunk, n)


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
    tasks = [(k, c, s//ch, min(ch, draws-s)) for k, cells in (("y", Y_CELLS), ("a", A_CELLS))
             for c in range(len(cells)) for s in range(0, draws, ch)]
    agg = {}
    with ProcessPoolExecutor(a.workers) as ex:
        for kind, cell, res in ex.map(job, tasks, chunksize=1):
            d = agg.setdefault((kind, cell), {})
            for k, v in res.items():
                d[k] = d.get(k, 0)+v
    yrows = [dict(population=t, cause=c, Y1=agg[("y", i)]["Y1"]/draws) for i, (t, c) in enumerate(Y_CELLS)]
    arows = [dict(population=p, trend=tr, overdispersion=od, multiplier=m, A1=agg[("a", i)]["A1"]/draws,
                  A2=agg[("a", i)]["A2"]/draws) for i, (p, tr, od, m) in enumerate(A_CELLS)]
    yf = [r for r in yrows if r["Y1"] < .86]
    null = [r for r in arows if r["trend"] == 0 and r["overdispersion"] == 0 and r["multiplier"] == 1]
    outcome = {"Y1": dict(passed=not yf, gated=bool(yf) and all(r["population"] == 30_000 for r in yf),
                          min=min(r["Y1"] for r in yrows)),
               "A1": dict(passed=max(r["A1"] for r in null) <= .05, max_null=max(r["A1"] for r in null)),
               "A2": dict(passed=max(r["A2"] for r in null) <= .05, max_null=max(r["A2"] for r in null))}
    out = dict(ypll=yrows, aberration=arows, outcome=outcome, draws=draws, criterion_commit=a.criterion_commit,
               seconds=round(time.time()-t0), frozen_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FROZEN})
    if a.smoke:
        print(json.dumps(outcome), out["seconds"]); return
    OUT.with_suffix(".json").write_text(json.dumps(out, indent=1)+"\n")
    L = ["# Round 95: YPLL intervals and aberration detection", "",
         f"Criterion commit: `{a.criterion_commit}`. {draws} draws per cell. Author self-review, not independent.", "",
         "| Method | Outcome | Key value |", "| :--- | :--- | ---: |",
         f"| Y1 age-adjusted YPLL-75 interval | {'pass' if outcome['Y1']['passed'] else ('pass from 200,000 (gate)' if outcome['Y1']['gated'] else 'fail')} | lowest coverage {outcome['Y1']['min']:.3f} |",
         f"| A1 historical limits | {'pass' if outcome['A1']['passed'] else 'fail'} | null false-alarm rate {outcome['A1']['max_null']:.3f} |",
         f"| A2 EARS C2 | {'pass' if outcome['A2']['passed'] else 'fail'} | null false-alarm rate {outcome['A2']['max_null']:.3f} |", "",
         "## YPLL", "", "| Population | Cause | Coverage |", "| ---: | :--- | ---: |"]
    L += [f"| {r['population']:,} | {r['cause']} | {r['Y1']:.3f} |" for r in yrows]
    L += ["", "## Aberration flags (share of draws flagged high)", "",
          "| Population | Trend | Overdispersion | Multiplier | A1 | A2 |", "| ---: | ---: | ---: | ---: | ---: | ---: |"]
    L += [f"| {r['population']:,} | {r['trend']} | {r['overdispersion']} | {r['multiplier']} | {r['A1']:.3f} | {r['A2']:.3f} |"
          for r in arows]
    L.append("")
    OUT.with_suffix(".md").write_text("\n".join(L))
    print(json.dumps({k: v["passed"] for k, v in outcome.items()}))


if __name__ == "__main__":
    main()
