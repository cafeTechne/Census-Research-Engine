# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 93: GWR, classification, regionalization and diversity with ACS uncertainty (frozen with the criterion,
docs/audits/spatial_models_validation_criterion.md).

Usage: scripts/spatial_models_validation.py --criterion-commit SHA [--workers N] [--smoke]
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
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
from scipy.spatial import Delaunay  # noqa: E402

from census import spatial_models_core as sm  # noqa: E402

GWR_CELLS = [(slope, noise) for slope in ("constant", "varying") for noise in ("low", "high")]
CLS_CELLS = [(kind, noise) for kind in ("kmeans", "skater") for noise in ("low", "high")]
DIV_CELLS = [50, 200]
DRAWS = {"gwr": 500, "cls": 200, "div": 1000}
CHUNK = {"gwr": 5, "cls": 10, "div": 50}
FROZEN = ["scripts/spatial_models_validation.py", "census/spatial_models_core.py", "docs/audits/mi_tract_geometry.json",
          "docs/audits/spatial_models_validation_criterion.md"]
OUT = ROOT/"docs/audits/spatial_models_validation"
CENTRES = np.array([[1.5, 0, 0], [0, 1.5, 0], [0, 0, 1.5], [-1.5, -1.5, -1.5]])/1.0


@lru_cache(maxsize=None)
def geometry():
    g = json.loads((ROOT/"docs/audits/mi_tract_geometry.json").read_text())
    idx = [i for i, x in enumerate(g["GEOID"]) if x.startswith("26163")]
    lon, lat = np.array(g["lon"])[idx], np.array(g["lat"])[idx]
    x = (lon-lon.mean())*111.32*np.cos(np.radians(lat.mean())); y = (lat-lat.mean())*110.57
    D = np.hypot(x[:, None]-x[None], y[:, None]-y[None])
    E = set()
    for s in Delaunay(np.column_stack([x, y])).simplices:
        for a in range(3):
            for b in range(a+1, 3):
                e = tuple(sorted((int(s[a]), int(s[b]))))
                if D[e] < 5:
                    E.add(e)
    L = np.linalg.cholesky(np.exp(-D/5)+1e-8*np.eye(len(x)))
    return x, y, D, sorted(E), L


def field(rng):
    x, _, _, _, L = geometry()
    v = L @ rng.standard_normal(len(x))+np.sqrt(.5)*rng.standard_normal(len(x))
    return (v-v.mean())/v.std()


def gwr_job(cell, d):
    slope, noise = GWR_CELLS[cell]
    xc, _, D, _, _ = geometry()
    rng = np.random.default_rng([20282931, cell, d])
    n = len(xc)
    b1 = np.ones(n) if slope == "constant" else 1+.5*(xc-xc.mean())/xc.std()
    se = rng.uniform(*((.3, 1.) if noise == "low" else (.6, 2.)), n)
    x = field(rng)
    y = 1+b1*x+.5*rng.standard_normal(n)+se*rng.standard_normal(n)
    r = sm.gwr(y, x[:, None], D, perms=99, rng=rng)
    cov = (r["lower"][:, 1] <= b1) & (b1 <= r["upper"][:, 1])
    return cov.astype(float), float(r["nonstationarity_p"] <= .10), r["bandwidth_km"]


def cls_job(cell, d):
    kind, noise = CLS_CELLS[cell]
    xc, yc, _, E, _ = geometry()
    rng = np.random.default_rng([20282932, cell, d])
    n = len(xc)
    if kind == "kmeans":
        truth = rng.integers(0, 4, n)
    else:
        truth = (xc > np.median(xc)).astype(int)*2+(yc > np.median(yc)).astype(int)
    se = rng.uniform(*((.2, .5) if noise == "low" else (.5, 1.)), n)[:, None]
    F = CENTRES[truth]+rng.standard_normal((n, 3))+se*rng.standard_normal((n, 3))
    fit = (lambda G: sm.kmeans(G, 4, rng)) if kind == "kmeans" else (lambda G: sm.skater(G, E, 4))
    main = fit(F)
    reps = [fit(F+se*rng.standard_normal((n, 3))) for _ in range(20)]
    stab = sm.stability(main, reps, 4)
    wrong = sm.match_labels(truth, main, 4) != truth
    lo = stab < .8
    return dict(ari=sm.adjusted_rand(truth, main), stability=float(stab.mean()), share_unstable=float(lo.mean()),
                wrong_unstable=float(wrong[lo].mean()) if lo.any() else np.nan,
                wrong_stable=float(wrong[~lo].mean()) if (~lo).any() else np.nan)


def div_job(cell, d):
    neff = DIV_CELLS[cell]
    rng = np.random.default_rng([20282933, cell, d])
    n = len(geometry()[0])
    p = rng.dirichlet([2, 1, 1, .5], n)
    ph = np.array([rng.multinomial(neff, pi) for pi in p])/neff
    q = np.stack([np.array([rng.multinomial(neff, pi) for pi in ph])/neff for _ in range(80)])
    reps = ph+(q-ph)/2
    true = sm.entropy(p)
    out = {}
    for k, bc in (("D1", False), ("D1bc", True)):
        r = sm.diversity(ph, reps, bc)
        out[k] = ((r["lower"] <= true) & (true <= r["upper"])).astype(float)
    return out


def job(args):
    fam, cell, start, stop = args
    res = [{"gwr": gwr_job, "cls": cls_job, "div": div_job}[fam](cell, d) for d in range(start, stop)]
    return fam, cell, res


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
    draws = {k: 2 for k in DRAWS} if a.smoke else DRAWS
    chunk = {k: 1 for k in CHUNK} if a.smoke else CHUNK
    ncell = {"gwr": len(GWR_CELLS), "cls": len(CLS_CELLS), "div": len(DIV_CELLS)}
    tasks = [(f, c, s, min(s+chunk[f], draws[f])) for f in ("gwr", "cls", "div") for c in range(ncell[f])
             for s in range(0, draws[f], chunk[f])]
    agg = {}
    with ProcessPoolExecutor(a.workers) as ex:
        for i, (fam, cell, res) in enumerate(ex.map(job, tasks, chunksize=1)):
            agg.setdefault((fam, cell), []).extend(res)
            if i % 100 == 0:
                print({"done": i, "of": len(tasks), "s": round(time.time()-t0)}, flush=True)
    rows = {"gwr": [], "cls": [], "div": []}
    for c, (slope, noise) in enumerate(GWR_CELLS):
        R = agg[("gwr", c)]
        cov = np.mean([r[0] for r in R], 0)
        rows["gwr"].append(dict(slope=slope, noise=noise, mean_coverage=float(cov.mean()),
                                share_areas_ge80=float(np.mean(cov >= .8)), min_area=float(cov.min()),
                                reject_rate=float(np.mean([r[1] for r in R])),
                                median_bandwidth_km=float(np.median([r[2] for r in R]))))
    for c, (kind, noise) in enumerate(CLS_CELLS):
        R = agg[("cls", c)]
        rows["cls"].append(dict(kind=kind, noise=noise, **{k: float(np.nanmean([r[k] for r in R])) for k in R[0]}))
    for c, neff in enumerate(DIV_CELLS):
        R = agg[("div", c)]
        row = dict(n_eff=neff)
        for k in ("D1", "D1bc"):
            cov = np.mean([r[k] for r in R], 0)
            row[k] = dict(mean_coverage=float(cov.mean()), share_areas_ge80=float(np.mean(cov >= .8)))
        rows["div"].append(row)
    g = rows["gwr"]
    outcome = {"R1": dict(passed=all(r["mean_coverage"] >= .86 and r["share_areas_ge80"] >= .9 for r in g)
                          and all(r["reject_rate"] <= .10 for r in g if r["slope"] == "constant"))}
    for k in ("D1", "D1bc"):
        outcome[k] = dict(passed=all(r[k]["mean_coverage"] >= .86 and r[k]["share_areas_ge80"] >= .9 for r in rows["div"]))
    out = dict(rows=rows, outcome=outcome, draws=draws, criterion_commit=a.criterion_commit, seconds=round(time.time()-t0),
               frozen_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FROZEN})
    if a.smoke:
        print(json.dumps(out["rows"], default=float)[:1500]); print(json.dumps(outcome), out["seconds"]); return
    OUT.with_suffix(".json").write_text(json.dumps(out, indent=1)+"\n")
    L = ["# Round 93: GWR, classification, regionalization and diversity with ACS uncertainty", "",
         f"Criterion commit: `{a.criterion_commit}`. Wayne County tracts (625). Author self-review, not independent.", "",
         "| Family | Outcome |", "| :--- | :--- |"] + [f"| {k} | {'pass' if v['passed'] else 'fail'} |" for k, v in outcome.items()]
    L += ["", "## R1 GWR (local slope, 90% robust intervals; 500 draws)", "",
          "| Slope | Sampling error | Mean coverage | Areas >= .80 | Lowest area | Non-stationarity rejections | Bandwidth (km) |",
          "| :--- | :--- | ---: | ---: | ---: | ---: | ---: |"]
    L += [f"| {r['slope']} | {r['noise']} | {r['mean_coverage']:.3f} | {r['share_areas_ge80']:.3f} | {r['min_area']:.3f} | "
          f"{r['reject_rate']:.3f} | {r['median_bandwidth_km']:.1f} |" for r in g]
    L += ["", "## C1/C2 classification and regionalization (reported; 200 draws)", "",
          "| Method | Sampling error | ARI | Mean stability | Share unstable (< .8) | Misclassified if unstable | Misclassified if stable |",
          "| :--- | :--- | ---: | ---: | ---: | ---: | ---: |"]
    L += [f"| {r['kind']} | {r['noise']} | {r['ari']:.3f} | {r['stability']:.3f} | {r['share_unstable']:.3f} | "
          f"{r['wrong_unstable']:.3f} | {r['wrong_stable']:.3f} |" for r in rows["cls"]]
    L += ["", "## D1 entropy diversity (1,000 draws)", "", "| n_eff | D1 mean coverage | D1 areas >= .80 | D1bc mean coverage | D1bc areas >= .80 |",
          "| ---: | ---: | ---: | ---: | ---: |"]
    L += [f"| {r['n_eff']} | {r['D1']['mean_coverage']:.3f} | {r['D1']['share_areas_ge80']:.3f} | "
          f"{r['D1bc']['mean_coverage']:.3f} | {r['D1bc']['share_areas_ge80']:.3f} |" for r in rows["div"]]
    L.append("")
    OUT.with_suffix(".md").write_text("\n".join(L))
    print(json.dumps({k: v["passed"] for k, v in outcome.items()}))


if __name__ == "__main__":
    main()
