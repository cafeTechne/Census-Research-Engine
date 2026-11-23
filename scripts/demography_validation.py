# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 101: life-table intervals (frozen with the criterion, docs/audits/demography_validation_criterion.md).

Usage: scripts/demography_validation.py --criterion-commit SHA [--workers N] [--smoke]
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

from census import demography_core as dc  # noqa: E402
from census.standardize import standard_weights  # noqa: E402

STARTS = [0, 1, 5, 15, 25, 35, 45, 55, 65, 75, 85]
RATES = np.array([550, 24, 13, 80, 130, 200, 380, 850, 1700, 4000, 13000])/1e5
CELLS = [50_000, 500_000, 5_000_000]
DRAWS, CHUNK = 2000, 100
FROZEN = ["scripts/demography_validation.py", "census/demography_core.py", "docs/audits/demography_validation_criterion.md"]
OUT = ROOT/"docs/audits/demography_validation"
I65 = STARTS.index(65)


def person_years(total):
    bands = [[a, b-1] for a, b in zip(STARTS[:-1], STARTS[1:])]+[[85, None]]
    w = np.array(standard_weights(bands))
    return total*w


def job(args):
    cell, start, stop = args
    py = person_years(CELLS[cell]); true = dc.life_table(STARTS, RATES*py, py)
    t0, t65 = true["e"][0], true["e"][I65]
    acc = dict(e0=0, e65=0)
    for d in range(start, stop):
        rng = np.random.default_rng([20283011, cell, d])
        D = rng.poisson(RATES*py).astype(float)
        while D[-1] == 0:
            D[-1] = rng.poisson(RATES[-1]*py[-1])
        lt = dc.life_table(STARTS, D, py)
        acc["e0"] += lt["lower"][0] <= t0 <= lt["upper"][0]
        acc["e65"] += lt["lower"][I65] <= t65 <= lt["upper"][I65]
    return cell, acc


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
    draws, ch = (20, 10) if a.smoke else (DRAWS, CHUNK)
    tasks = [(c, s, min(s+ch, draws)) for c in range(len(CELLS)) for s in range(0, draws, ch)]
    agg = {}
    with ProcessPoolExecutor(a.workers) as ex:
        for cell, acc in ex.map(job, tasks, chunksize=1):
            g = agg.setdefault(cell, dict(e0=0, e65=0))
            for k, v in acc.items():
                g[k] += int(v)
    rows = [dict(population=CELLS[c], e0=g["e0"]/draws, e65=g["e65"]/draws) for c, g in sorted(agg.items())]
    fails = [r for r in rows if min(r["e0"], r["e65"]) < .86]
    outcome = {"L1": dict(passed=not fails, gated=bool(fails) and all(r["population"] == 50_000 for r in fails),
                          min=float(min(min(r["e0"], r["e65"]) for r in rows)))}
    out = dict(rows=rows, outcome=outcome, draws=draws, criterion_commit=a.criterion_commit, seconds=round(time.time()-t0),
               frozen_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FROZEN})
    if a.smoke:
        print(json.dumps(outcome), rows); return
    OUT.with_suffix(".json").write_text(json.dumps(out, indent=1)+"\n")
    o = outcome["L1"]
    L = ["# Round 101: life-table (Chiang II) intervals", "", f"Criterion commit: `{a.criterion_commit}`. {draws} draws per "
         "cell; 90% intervals. Author self-review, not independent.", "",
         f"**L1: {'pass' if o['passed'] else ('pass from 500,000 person-years (gate)' if o['gated'] else 'fail')}** "
         f"(lowest coverage {o['min']:.3f}).", "", "| Person-years | e0 coverage | e65 coverage |", "| ---: | ---: | ---: |"]
    L += [f"| {r['population']:,} | {r['e0']:.3f} | {r['e65']:.3f} |" for r in rows]
    L.append("")
    OUT.with_suffix(".md").write_text("\n".join(L))
    print(json.dumps({"L1": (o["passed"], o["gated"])}))


if __name__ == "__main__":
    main()
