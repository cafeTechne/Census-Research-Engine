# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 97: spatial block cross-validation and MAUP sensitivity (frozen with the criterion,
docs/audits/model_assessment_validation_criterion.md).

Usage: scripts/model_assessment_validation.py --criterion-commit SHA [--workers N] [--smoke]
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

from census import model_assessment_core as mc  # noqa: E402
import spatial_models_validation as smv  # noqa: E402

RANGES = (0, 20, 50)
DRAWS, MAUP_DRAWS, CHUNK = 500, 200, 25
FROZEN = ["scripts/model_assessment_validation.py", "census/model_assessment_core.py", "scripts/spatial_models_validation.py",
          "docs/audits/mi_tract_geometry.json", "docs/audits/model_assessment_validation_criterion.md"]
OUT = ROOT/"docs/audits/model_assessment_validation"


@lru_cache(maxsize=None)
def region():
    g = json.loads((ROOT/"docs/audits/mi_tract_geometry.json").read_text())
    idx = [i for i, x in enumerate(g["GEOID"]) if x[:5] in ("26163", "26125", "26099")]
    lon, lat = np.array(g["lon"])[idx], np.array(g["lat"])[idx]
    xy = np.column_stack([(lon-lon.mean())*111.32*np.cos(np.radians(lat.mean())), (lat-lat.mean())*110.57])
    a = np.array([g["GEOID"][i].startswith("26163") for i in idx])
    D = np.hypot(xy[:, :1]-xy[:, 0], xy[:, 1:]-xy[:, 1])
    return xy, a, D


@lru_cache(maxsize=None)
def chol(rng_km):
    _, _, D = region()
    return np.linalg.cholesky(np.exp(-D/rng_km)+1e-8*np.eye(len(D)))


def data(rng, r):
    xy, a, D = region(); n = len(xy)
    x = chol(10) @ rng.standard_normal(n)+np.sqrt(.5)*rng.standard_normal(n); x = (x-x.mean())/x.std()
    e = rng.standard_normal(n) if r == 0 else chol(r) @ rng.standard_normal(n)
    y = 1+.5*x+e+.5*rng.standard_normal(n)
    return y, x, xy, a


def cv_job(cell, start, stop):
    r = RANGES[cell]; out = []
    for d in range(start, stop):
        rng = np.random.default_rng([20282971, cell, d])
        y, x, xy, a = data(rng, r)
        m, s = mc.ols_knn_fit_predict(y[a], x[a, None], xy[a], x[~a, None], xy[~a])
        truth = mc.scores(y[~a], m, s)
        ya, xa, pa = y[a], x[a, None], xy[a]
        v1 = mc.cross_validate(ya, xa, pa, mc.block_folds(pa, 5, rng))
        v10 = mc.cross_validate(ya, xa, pa, mc.block_folds(pa, 10, rng))
        v0 = mc.cross_validate(ya, xa, pa, mc.random_folds(len(ya), 10, rng))
        out.append({k: (v["rmse"], v["coverage"]) for k, v in (("truth", truth), ("V1", v1), ("V1_10", v10), ("V0", v0))})
    return out


def maup_job(cell, start, stop):
    r = RANGES[cell]; xy, a, _ = region()
    edges = smv.geometry()[3]
    out = []
    for d in range(start, stop):
        rng = np.random.default_rng([20282972, cell, d])
        y, x, _, _ = data(rng, r)
        y, x = y[a], x[a]; w = np.ones(len(y))
        base = mc.maup_slope(y, x, w, np.arange(len(y)))
        out.append([mc.maup_slope(y, x, w, mc.random_zoning(len(y), edges, 10, rng))/base for _ in range(20)])
    return out


def job(args):
    kind, cell, start, stop = args
    return kind, cell, (cv_job if kind == "cv" else maup_job)(cell, start, stop)


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
    nd, nm, ch = (4, 2, 2) if a.smoke else (DRAWS, MAUP_DRAWS, CHUNK)
    tasks = [(k, c, s, min(s+ch, n)) for k, n in (("cv", nd), ("maup", nm)) for c in range(len(RANGES)) for s in range(0, n, ch)]
    agg = {}
    with ProcessPoolExecutor(a.workers) as ex:
        for kind, cell, res in ex.map(job, tasks, chunksize=1):
            agg.setdefault((kind, cell), []).extend(res)
    cv_rows, maup_rows = [], []
    for c, r in enumerate(RANGES):
        R = agg[("cv", c)]
        row = dict(range_km=r)
        for k in ("truth", "V1", "V1_10", "V0"):
            row[k] = dict(rmse=float(np.mean([x[k][0] for x in R])), coverage=float(np.mean([x[k][1] for x in R])))
        for k in ("V1", "V1_10", "V0"):
            row[k]["rmse_ratio"] = row[k]["rmse"]/row["truth"]["rmse"]
            row[k]["coverage_diff"] = row[k]["coverage"]-row["truth"]["coverage"]
        cv_rows.append(row)
        M = np.array(agg[("maup", c)])
        maup_rows.append(dict(range_km=r, mean_ratio=float(M.mean()), sd_within_draw=float(M.std(1).mean()),
                              p05=float(np.quantile(M, .05)), p95=float(np.quantile(M, .95))))
    ok = all(abs(r["V1"]["rmse_ratio"]-1) <= .10 and abs(r["V1"]["coverage_diff"]) <= .03 for r in cv_rows)
    outcome = {"V1": dict(passed=ok)}
    out = dict(cv=cv_rows, maup=maup_rows, outcome=outcome, criterion_commit=a.criterion_commit, seconds=round(time.time()-t0),
               frozen_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FROZEN})
    if a.smoke:
        print(json.dumps(outcome), out["seconds"]); print(json.dumps(cv_rows)[:500]); return
    OUT.with_suffix(".json").write_text(json.dumps(out, indent=1)+"\n")
    L = ["# Round 97: spatial block cross-validation and MAUP sensitivity", "",
         f"Criterion commit: `{a.criterion_commit}`. {DRAWS} draws per cell (CV), {MAUP_DRAWS} (MAUP). Author self-review, "
         "not independent.", "", f"**V1 (5 spatial blocks): {'pass' if ok else 'fail'}.**", "",
         "| Residual range (km) | True RMSE (new region) | V1 RMSE ratio | V1-10 ratio | V0 random ratio | True coverage | "
         "V1 coverage | V0 coverage |", "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    L += [f"| {r['range_km']} | {r['truth']['rmse']:.3f} | {r['V1']['rmse_ratio']:.3f} | {r['V1_10']['rmse_ratio']:.3f} | "
          f"{r['V0']['rmse_ratio']:.3f} | {r['truth']['coverage']:.3f} | {r['V1']['coverage']:.3f} | {r['V0']['coverage']:.3f} |"
          for r in cv_rows]
    L += ["", "## MAUP: zone-level slope / tract-level slope (random contiguous zonings of about 10 tracts)", "",
          "| Residual range (km) | Mean ratio | SD across zonings | 5th-95th percentile |", "| ---: | ---: | ---: | :--- |"]
    L += [f"| {r['range_km']} | {r['mean_ratio']:.3f} | {r['sd_within_draw']:.3f} | {r['p05']:.3f}-{r['p95']:.3f} |" for r in maup_rows]
    L.append("")
    OUT.with_suffix(".md").write_text("\n".join(L))
    print(json.dumps(outcome))


if __name__ == "__main__":
    main()
