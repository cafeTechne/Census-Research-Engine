# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 69 S: slope coverage of the spatial error model (ML) on the national county geometry (frozen with the
criterion).

Queen contiguity on the 2014 cartographic counties of the 48 contiguous states and DC (Loving TX, Broomfield CO and
Bedford City VA excluded, as in replication D; islands dropped), row-standardized. x = (I - .5 W)^-1 z;
y = 1 + .5 x + (I - lambda W)^-1 e, lambda in {.3, .55}; z, e standard normal. Estimator: spreg ML_Error
(method "full"), 90% normal interval for the slope. 1,000 draws per cell; seeds [20281101 + cell, draw]. Pass:
coverage >= .86 in both cells.

Usage: scripts/r69_county_sem_validation.py --criterion-commit SHA [--workers N] [--smoke]
"""
import argparse
import hashlib
import json
import subprocess
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402

SEED, DRAWS, CHUNK = 20281101, 1000, 25
LAMBDAS = (.3, .55)
FROZEN = ["scripts/r69_county_sem_validation.py", "docs/audits/r69_replication_criterion.md"]
OUT = ROOT/"docs/audits/r69_county_sem_validation"


@lru_cache(maxsize=None)
def weights():
    from census import boundaries, spatial
    g = boundaries.get_boundaries("county", 2014)
    g = g[~g.GEOID.str[:2].isin({"02", "15", "60", "66", "69", "72", "78"})
          & ~g.GEOID.isin({"48301", "08014", "51515"})]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        w = spatial.spatial_weights(g, "queen")
        isl = set(str(i) for i in w.islands)
        w = spatial.spatial_weights(g[~g.GEOID.isin(isl)], "queen")
    W = w.sparse.toarray()
    return w, W


def job(args):
    from spreg import ML_Error
    cell, start, stop = args
    w, W = weights(); n = len(W); lam = LAMBDAS[cell]
    Ax = np.linalg.inv(np.eye(n)-.5*W); Au = np.linalg.inv(np.eye(n)-lam*W)
    hit = fail = 0
    for d in range(start, stop):
        rng = np.random.default_rng([SEED+cell, d])
        x = Ax@rng.standard_normal(n); y = 1+.5*x+Au@rng.standard_normal(n)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                m = ML_Error(y[:, None], x[:, None], w, method="full")
            b, s = float(m.betas[1, 0]), float(np.sqrt(m.vm[1, 1]))
            hit += b-1.645*s <= .5 <= b+1.645*s
        except Exception:  # noqa: BLE001 - a failed fit counts as non-coverage
            fail += 1
    return cell, hit, fail


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
    draws = 4 if a.smoke else DRAWS; chunk = min(CHUNK, draws)
    tasks = [(c, s, min(s+chunk, draws)) for c in range(len(LAMBDAS)) for s in range(0, draws, chunk)]
    acc = {c: [0, 0] for c in range(len(LAMBDAS))}; t0 = time.time()
    with ProcessPoolExecutor(a.workers) as ex:
        for cell, h, f in ex.map(job, tasks):
            acc[cell][0] += h; acc[cell][1] += f
            print({"cell": cell, "s": round(time.time()-t0)}, flush=True)
    cells = [dict(lam=LAMBDAS[c], coverage=acc[c][0]/draws, failed=acc[c][1]) for c in acc]
    res = dict(cells=cells, passed=bool(all(c["coverage"] >= .86 for c in cells)), draws=draws,
               n_counties=len(weights()[1]), criterion_commit=a.criterion_commit,
               frozen_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FROZEN})
    if a.smoke:
        print(res["cells"], round(time.time()-t0)); return
    OUT.with_suffix(".json").write_text(json.dumps(res, indent=1)+"\n")
    L = ["# Round 69 S: spatial error model slope coverage on national counties", "",
         f"Criterion commit: `{a.criterion_commit}`. {draws:,} draws per cell; {res['n_counties']:,} counties.", "",
         "| lambda | Coverage | Failed fits |", "| ---: | ---: | ---: |"]
    L += [f"| {c['lam']} | {c['coverage']:.4f} | {c['failed']} |" for c in cells]
    L += ["", f"Outcome (>= .86 in both cells): {'passes' if res['passed'] else 'fails'}.", ""]
    OUT.with_suffix(".md").write_text("\n".join(L))
    print(res["passed"])


if __name__ == "__main__":
    main()
