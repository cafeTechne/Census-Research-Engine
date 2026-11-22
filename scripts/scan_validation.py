# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 81: Kulldorff Poisson spatial scan (frozen with the criterion, docs/audits/scan_validation_criterion.md).

Geometry: docs/audits/scan_geometry.csv (2022 county populations, B01003, and representative points; MI+NY 145
counties, OH+PA 155). Expected counts proportional to population with mean E in {5, 20, 100} per county; max
window 50% of the expected total; R = 999 Monte Carlo data sets per draw; alpha .10.
Null (6 cells, 1,000 draws): counts Poisson(mu). Pass: rejection rate of the primary cluster (p_mc <= .10) in
[.07, .13] in every cell.
Sensitivity (6 cells, 1,000 draws, reported): counts Poisson(mu) but the analysis uses denominators with
independent N(0, .05^2) relative error (ACS-like), size reported.
Power (36 cells, 250 draws, reported): a planted cluster of 1, 3 or 8 counties (the centre county and its
nearest neighbours; centre 26065 for MI+NY, 42027 for OH+PA) with relative risk 1.5 or 2. Power, sensitivity and
positive predictive value of the detected primary cluster (when p <= .10) reported.
Seeds: [20282101 + cell, draw].

Usage: scripts/scan_validation.py --criterion-commit SHA [--workers N] [--smoke]
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
import pandas as pd  # noqa: E402

from census import scan_core as sc  # noqa: E402

SEED = 20282101
GEOM = ROOT/"docs/audits/scan_geometry.csv"
PAIRS, ES = ("MINY", "OHPA"), (5, 20, 100)
CENTRE = {"MINY": "26065", "OHPA": "42027"}
CELLS = ([("null", p, E, 0, 1.0) for p in PAIRS for E in ES]+[("noisy", p, E, 0, 1.0) for p in PAIRS for E in ES]
         + [("power", p, E, k, rr) for p in PAIRS for E in ES for k in (1, 3, 8) for rr in (1.5, 2.0)])
DRAWS, PDRAWS, CHUNK, R = 1000, 250, 25, 999
FROZEN = ["scripts/scan_validation.py", "census/scan_core.py", "docs/audits/scan_geometry.csv",
          "docs/audits/scan_validation_criterion.md"]
OUT = ROOT/"docs/audits/scan_validation"


def geometry(pair):
    g = pd.read_csv(GEOM, dtype={"GEOID": str})
    return g[g.pair == pair].reset_index(drop=True)


def job(args):
    cell, start, stop = args
    kind, pair, E, k, rr = CELLS[cell]
    g = geometry(pair)
    lon, lat = g.lon.to_numpy(), g.lat.to_numpy()
    mu = g.population.to_numpy(float)/g.population.mean()*E
    truth = np.array([], int)
    lam = mu.copy()
    if kind == "power":
        D = sc.distances(lon, lat)
        truth = np.argsort(D[list(g.GEOID).index(CENTRE[pair])], kind="stable")[:k]
        lam[truth] *= rr
    acc = dict(reject=0, sens=0.0, ppv=0.0, gumbel_reject=0)
    for d in range(start, stop):
        rng = np.random.default_rng([SEED+cell, d])
        c = rng.poisson(lam)
        m_use = mu*(1+.05*rng.standard_normal(len(mu))) if kind == "noisy" else mu
        r = sc.scan(c, m_use, lon, lat, R=R, rng=rng, secondary=0)
        p = r["primary"]["p_mc"] if r["primary"] else 1.0
        acc["gumbel_reject"] += int(r["primary"] is not None and r["primary"]["p_gumbel"] <= .10)
        if p <= .10:
            acc["reject"] += 1
            if kind == "power":
                det = set(r["primary"]["members"]); tru = set(truth.tolist())
                acc["sens"] += len(det & tru)/len(tru); acc["ppv"] += len(det & tru)/len(det)
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
    nd = {c: (2 if a.smoke else (PDRAWS if CELLS[c][0] == "power" else DRAWS)) for c in range(len(CELLS))}
    chunk = 1 if a.smoke else CHUNK
    tasks = [(c, s, min(s+chunk, nd[c])) for c in range(len(CELLS)) for s in range(0, nd[c], chunk)]
    acc = {}
    t0 = time.time()
    with ProcessPoolExecutor(a.workers) as ex:
        for i, (cell, r) in enumerate(ex.map(job, tasks, chunksize=1)):
            if cell not in acc:
                acc[cell] = r
            else:
                for k_, v in r.items():
                    acc[cell][k_] += v
            if i % 50 == 0:
                print({"done": i, "of": len(tasks), "s": round(time.time()-t0)}, flush=True)
    rows = []
    for c, r in sorted(acc.items()):
        kind, pair, E, k, rr = CELLS[c]
        n = nd[c]
        rows.append(dict(kind=kind, pair=pair, E=E, k=k, rr=rr, draws=n, rejection=r["reject"]/n,
                         gumbel_rejection=r["gumbel_reject"]/n,
                         sensitivity=r["sens"]/r["reject"] if kind == "power" and r["reject"] else None,
                         ppv=r["ppv"]/r["reject"] if kind == "power" and r["reject"] else None))
    passed = dict(K1=all(.07 <= r["rejection"] <= .13 for r in rows if r["kind"] == "null"))
    out = dict(rows=rows, passed=passed, replicates=R, criterion_commit=a.criterion_commit, seconds=round(time.time()-t0),
               frozen_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FROZEN})
    if a.smoke:
        print(json.dumps(passed), out["seconds"]); return
    OUT.with_suffix(".json").write_text(json.dumps(out, indent=1)+"\n")
    L = ["# Round 81: Kulldorff Poisson spatial scan", "",
         f"Criterion commit: `{a.criterion_commit}`. {R} Monte Carlo data sets per draw; alpha .10; windows up to 50% "
         "of the expected total. Author self-review, not independent.", "",
         "## Size (pass: rejection rate in [.07, .13] in every null cell)", "",
         "| Design | States | Mean expected per county | Rejection (MC) | Rejection (Gumbel) |", "| :--- | :--- | ---: | ---: | ---: |"]
    L += [f"| {r['kind']} | {r['pair']} | {r['E']} | {r['rejection']:.3f} | {r['gumbel_rejection']:.3f} |"
          for r in rows if r["kind"] in ("null", "noisy")]
    L += ["", "## Power and location (reported; 250 draws)", "",
          "| States | Mean expected | Cluster counties | RR | Power | Sensitivity | PPV |", "| :--- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    f = lambda v: "–" if v is None else f"{v:.3f}"  # noqa: E731
    L += [f"| {r['pair']} | {r['E']} | {r['k']} | {r['rr']} | {r['rejection']:.3f} | {f(r['sensitivity'])} | {f(r['ppv'])} |"
          for r in rows if r["kind"] == "power"]
    L += ["", f"Outcomes: `{json.dumps(passed)}`.", ""]
    OUT.with_suffix(".md").write_text("\n".join(L))
    print(json.dumps(passed))


if __name__ == "__main__":
    main()
