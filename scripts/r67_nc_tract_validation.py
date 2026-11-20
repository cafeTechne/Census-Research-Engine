# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 67 S: SCPC coverage for an OLS slope on North Carolina tract geometry (frozen with the criterion).

All 2,192 NC tract representative points (docs/audits/nc_tract_geometry.json). Round 22's linear generator
(spatial_hac_validation.simulation_setup/simulation_draw: x and the error are exponential-covariance fields with
the cell's range; y = 1 + .5 x + error; target .5) at ranges {0, 20, 100} km. Procedures: SCPC rho_bar .05 and
.10 (census.scpc_core), HC3. 2,000 draws per cell; seeds [20281001 + cell, draw]. SCPC (per rho_bar) passes when
it covers >= .86 in every cell.

Usage: scripts/r67_nc_tract_validation.py --criterion-commit SHA [--workers N] [--smoke]
"""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/"scripts"))
import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402

from census import scpc_core as sc  # noqa: E402
from spatial_hac_validation import simulation_draw, simulation_setup  # noqa: E402

SEED, DRAWS, CHUNK = 20281001, 2000, 100
RANGES = (0, 20, 100)
RHOS = (.05, .10)
GEO = ROOT/"docs/audits/nc_tract_geometry.json"
FROZEN = ["scripts/r67_nc_tract_validation.py", "scripts/spatial_hac_validation.py", "census/scpc_core.py",
          "docs/audits/nc_tract_geometry.json", "docs/audits/r67_replication_criterion.md"]
OUT = ROOT/"docs/audits/r67_nc_tract_validation"


@lru_cache(maxsize=None)
def geometry():
    g = json.loads(GEO.read_text())
    lon, lat = np.array(g["lon"]), np.array(g["lat"])
    return lon, lat, sc.haversine(lon, lat)


@lru_cache(maxsize=None)
def setups(cell):
    lon, lat, D = geometry()
    _, L, _ = simulation_setup("linear", RANGES[cell], D, SEED+cell)
    return L, {r: sc.setup(D, r) for r in RHOS}


def job(args):
    cell, start, stop = args
    L, S = setups(cell)
    n = len(L); hits = {k: 0 for k in ["HC3"]+[f"SCPC{int(100*r):02d}" for r in RHOS]}; fails = 0
    for d in range(start, stop):
        rng = np.random.default_rng([SEED+cell, d])
        X, y = simulation_draw("linear", L, None, rng)
        try:
            XtX = np.linalg.inv(X.T@X); b = XtX@X.T@y; u = y-X@b
            h = np.einsum("ij,jk,ik->i", X, XtX, X)
            V = XtX@(X.T*(u/(1-h))**2)@X@XtX
            s = np.sqrt(V[1, 1]); t = stats.norm.ppf(.95)
            hits["HC3"] += b[1]-t*s <= .5 <= b[1]+t*s
            theta, e = sc.influence(X, y, "linear", 1)
            for r in RHOS:
                iv = sc.interval(theta, e, S[r])
                hits[f"SCPC{int(100*r):02d}"] += iv["lower"] <= .5 <= iv["upper"]
        except (np.linalg.LinAlgError, ValueError, FloatingPointError):
            fails += 1
    return cell, hits, fails


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
    draws = 20 if a.smoke else DRAWS
    chunk = min(CHUNK, draws)
    tasks = [(c, s, min(s+chunk, draws)) for c in range(len(RANGES)) for s in range(0, draws, chunk)]
    acc = {}; t0 = time.time()
    with ProcessPoolExecutor(a.workers) as ex:
        for cell, hits, fails in ex.map(job, tasks):
            A = acc.setdefault(cell, [dict.fromkeys(hits, 0), 0])
            for k, v in hits.items():
                A[0][k] += v
            A[1] += fails
            print({"cell": cell, "s": round(time.time()-t0)}, flush=True)
    cells = [dict(range_km=RANGES[c], coverage={k: v/draws for k, v in acc[c][0].items()}, failed=acc[c][1])
             for c in range(len(RANGES))]
    passed = {k: bool(all(c["coverage"][k] >= .86 for c in cells)) for k in cells[0]["coverage"]}
    res = dict(cells=cells, passed=passed, draws=draws, n_tracts=len(geometry()[0]), criterion_commit=a.criterion_commit,
               frozen_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FROZEN})
    if a.smoke:
        print(json.dumps(res["passed"]), [c["coverage"] for c in cells]); return
    OUT.with_suffix(".json").write_text(json.dumps(res, indent=1)+"\n")
    L = ["# Round 67 S: SCPC on North Carolina tract geometry", "",
         f"Criterion commit: `{a.criterion_commit}`. {draws:,} draws per cell; {res['n_tracts']:,} tracts.", "",
         "| Range km | HC3 | SCPC .05 | SCPC .10 |", "| ---: | ---: | ---: | ---: |"]
    for c in cells:
        cv = c["coverage"]
        L.append(f"| {c['range_km']} | {cv['HC3']:.4f} | {cv['SCPC05']:.4f} | {cv['SCPC10']:.4f} |")
    L += ["", f"Outcomes (>= .86 in every cell): `{json.dumps(passed)}`.", ""]
    OUT.with_suffix(".md").write_text("\n".join(L))
    print(json.dumps(passed))


if __name__ == "__main__":
    main()
