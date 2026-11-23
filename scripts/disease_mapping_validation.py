# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 96: BYM2 Poisson disease mapping (frozen with the criterion,
docs/audits/disease_mapping_validation_criterion.md).

Usage: scripts/disease_mapping_validation.py --criterion-commit SHA [--workers N] [--smoke]
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
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/"scripts"))
import numpy as np  # noqa: E402

from census import disease_mapping_core as dm  # noqa: E402
from census.rate_smoothing import eb_poisson_gamma  # noqa: E402

CELLS = [(g, phi, sig, m) for g in ("counties", "tracts") for phi in (.2, .8) for sig in (.2, .5) for m in (5, 30)]
DRAWS, CHUNK = 500, 10
FROZEN = ["scripts/disease_mapping_validation.py", "census/disease_mapping_core.py", "docs/audits/mi_county_geometry.json",
          "scripts/spatial_models_validation.py", "docs/audits/mi_tract_geometry.json",
          "docs/audits/disease_mapping_validation_criterion.md"]
OUT = ROOT/"docs/audits/disease_mapping_validation"
BINS = np.linspace(0, 1, 11)


@lru_cache(maxsize=None)
def geometry(name):
    if name == "counties":
        d = json.loads((ROOT/"docs/audits/mi_county_geometry.json").read_text())
        n, edges = len(d["GEOID"]), [tuple(e) for e in d["edges"]]
    else:
        import spatial_models_validation as smv
        x, _, _, edges, _ = smv.geometry(); n = len(x)
    return dm.scaled_icar_eigen(n, edges)


def expected(cell, n):
    rng = np.random.default_rng([20282961, cell])
    z = np.exp(.5*rng.standard_normal(n))
    return CELLS[cell][3]*z/np.median(z)


def job(args):
    cell, start, stop = args
    g, phi, sig, m = CELLS[cell]
    eig = geometry(g); n = len(eig[1]); E = expected(cell, n)
    cov = {"B1": np.zeros(n), "B2": np.zeros(n), "EB": np.zeros(n)}
    sq = {"B1": 0., "EB": 0., "SMR": 0.}
    calib = {k: np.zeros((10, 2)) for k in ("B1", "B2")}
    for d in range(start, stop):
        rng = np.random.default_rng([20282962, cell, d])
        b = dm.simulate_field(rng, eig, sig, phi); th = np.exp(b)
        y = rng.poisson(E*th).astype(float)
        both = dm.bym2(y, E, eigen=eig)
        for k in ("B1", "B2"):
            f = both[k]
            cov[k] += (f["lower"] <= th) & (th <= f["upper"])
            p = dm.exceedance(f, 1.2)
            bins = np.minimum((p*10).astype(int), 9)
            for j in range(10):
                sel = bins == j
                calib[k][j] += [sel.sum(), (th[sel] > 1.2).sum()]
            if k == "B1":
                sq["B1"] += np.mean((f["log_rr"]-b)**2)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                eb = eb_poisson_gamma(y, E, interval=None)
                cov["EB"] += (eb.eb_lower.to_numpy() <= th) & (th <= eb.eb_upper.to_numpy())
                sq["EB"] += np.mean((np.log(eb.eb_ratio.to_numpy())-b)**2)
            except (ValueError, FloatingPointError, np.linalg.LinAlgError):
                sq["EB"] += np.nan
        sq["SMR"] += np.mean((np.log((y+.5)/E)-b)**2)
    return cell, {k: v.tolist() for k, v in cov.items()}, sq, {k: v.tolist() for k, v in calib.items()}


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
    draws, ch = (2, 1) if a.smoke else (DRAWS, CHUNK)
    tasks = [(c, s, min(s+ch, draws)) for c in range(len(CELLS)) for s in range(0, draws, ch)]
    agg = {}
    with ProcessPoolExecutor(a.workers) as ex:
        for i, (cell, cov, sq, cal) in enumerate(ex.map(job, tasks, chunksize=1)):
            gg = agg.setdefault(cell, dict(cov={k: np.zeros(len(v)) for k, v in cov.items()}, sq={k: 0. for k in sq},
                                           cal={k: np.zeros((10, 2)) for k in cal}))
            for k, v in cov.items():
                gg["cov"][k] += v
            for k, v in sq.items():
                gg["sq"][k] += v
            for k, v in cal.items():
                gg["cal"][k] += np.array(v)
            if i % 100 == 0:
                print({"done": i, "of": len(tasks), "s": round(time.time()-t0)}, flush=True)
    rows = []
    for c, gg in sorted(agg.items()):
        g, phi, sig, m = CELLS[c]
        r = dict(geometry=g, phi=phi, sigma=sig, median_E=m)
        for k in ("B1", "B2", "EB"):
            cv = gg["cov"][k]/draws
            r[k] = dict(mean=float(cv.mean()), share_ge80=float(np.mean(cv >= .8)))
        for k in ("B1", "B2"):
            cal = gg["cal"][k]
            hi = cal[8:].sum(0)
            r[k]["exceed_n"] = int(hi[0]); r[k]["exceed_true_share"] = float(hi[1]/hi[0]) if hi[0] else None
            r[k]["calibration"] = [[float(BINS[j]), int(cal[j, 0]), float(cal[j, 1]/cal[j, 0]) if cal[j, 0] else None] for j in range(10)]
        r["rmse"] = {k: float(np.sqrt(v/draws)) for k, v in gg["sq"].items()}
        rows.append(r)
    outcome = {}
    for k in ("B1", "B2"):
        cov_ok = all(r[k]["mean"] >= .86 and r[k]["share_ge80"] >= .9 for r in rows)
        cal_ok = all(r[k]["exceed_true_share"] >= .75 for r in rows if r[k]["exceed_n"] >= 50)
        outcome[k] = dict(passed=cov_ok and cal_ok, coverage_ok=cov_ok, calibration_ok=cal_ok,
                          min_mean=min(r[k]["mean"] for r in rows))
    out = dict(rows=rows, outcome=outcome, draws=draws, criterion_commit=a.criterion_commit, seconds=round(time.time()-t0),
               frozen_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FROZEN})
    if a.smoke:
        print(json.dumps(outcome), out["seconds"]); print(json.dumps(rows[-1])[:600]); return
    OUT.with_suffix(".json").write_text(json.dumps(out, indent=1)+"\n")
    L = ["# Round 96: BYM2 Poisson disease mapping (Laplace approximation)", "",
         f"Criterion commit: `{a.criterion_commit}`. {draws} draws per cell; 90% intervals. Author self-review, not "
         "independent.", "", "| Estimator | Outcome | Coverage rule | Exceedance rule | Lowest mean coverage |",
         "| :--- | :--- | :--- | :--- | ---: |"]
    L += [f"| {k} | {'pass' if v['passed'] else 'fail'} | {'met' if v['coverage_ok'] else 'not met'} | "
          f"{'met' if v['calibration_ok'] else 'not met'} | {v['min_mean']:.3f} |" for k, v in outcome.items()]
    L += ["", "| Geometry | phi | sigma | median E | B1 mean (areas >= .80) | B2 mean (areas >= .80) | EB mean | "
          "B1 P>=.8 true share (n) | RMSE B1 / EB / SMR |", "| :--- | ---: | ---: | ---: | :--- | :--- | ---: | :--- | :--- |"]
    for r in rows:
        ex = r["B1"]["exceed_true_share"]
        L.append(f"| {r['geometry']} | {r['phi']} | {r['sigma']} | {r['median_E']} | {r['B1']['mean']:.3f} "
                 f"({r['B1']['share_ge80']:.2f}) | {r['B2']['mean']:.3f} ({r['B2']['share_ge80']:.2f}) | "
                 f"{r['EB']['mean']:.3f} | {'-' if ex is None else f'{ex:.2f}'} ({r['B1']['exceed_n']}) | "
                 f"{r['rmse']['B1']:.3f} / {r['rmse']['EB']:.3f} / {r['rmse']['SMR']:.3f} |")
    L.append("")
    OUT.with_suffix(".md").write_text("\n".join(L))
    print(json.dumps({k: v["passed"] for k, v in outcome.items()}))


if __name__ == "__main__":
    main()
