# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 71: tract-level spatial intervals (frozen with the criterion, docs/audits/tract_spatial_validation_criterion.md).

Geometries: NC 2018 tracts (docs/audits/nc_tract_geometry.json; queen weights from 2018 cartographic tracts) and
Michigan 2020 land tracts (docs/audits/mi_tract_geometry.json; 2020 cartographic tracts). Generator: Round 22's
linear design (spatial_hac_validation.simulation_setup/simulation_draw; target .5) at ranges {0, 20, 50, 100} km.
Procedures: T1 spatial error ML, T2 SCPC rho_bar .20 and .30, T3 SCPC distance benchmark (100 km), T4 HC3.
1,000 draws per cell; seeds [20281201 + cell, draw]. A procedure passes when it covers >= .86 in every cell of both
geometries; one passing only for ranges <= 50 km is reported as validated with that scope.

Usage: scripts/tract_spatial_validation.py --criterion-commit SHA [--workers N] [--smoke]
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

from census import scpc_core as sc, tract_spatial_core as tc  # noqa: E402
from spatial_hac_validation import simulation_draw, simulation_setup  # noqa: E402

SEED, DRAWS, CHUNK = 20281201, 1000, 20
GEOS = {"nc": ("docs/audits/nc_tract_geometry.json", 2018, "37"), "mi": ("docs/audits/mi_tract_geometry.json", 2020, "26")}
RANGES = (0, 20, 50, 100)
CELLS = [(g, r) for g in GEOS for r in RANGES]
KEYS = ["T1_sem", "T2_scpc20", "T2_scpc30", "T3_scpc_dist", "T4_hc3"]
FROZEN = ["scripts/tract_spatial_validation.py", "census/tract_spatial_core.py", "census/scpc_core.py",
          "scripts/spatial_hac_validation.py", "docs/audits/nc_tract_geometry.json", "docs/audits/mi_tract_geometry.json",
          "docs/audits/tract_spatial_validation_criterion.md"]
OUT = ROOT/"docs/audits/tract_spatial_validation"


@lru_cache(maxsize=None)
def geometry(name):
    path, year, st = GEOS[name]
    g = json.loads((ROOT/path).read_text())
    from census import boundaries, spatial
    b = boundaries.get_boundaries("tract", year, state=st)
    b = b.set_index(b.GEOID.astype(str)).loc[g["GEOID"]].reset_index(drop=True)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        w = spatial.spatial_weights(b, "queen")
    keep = np.array([i not in set(w.islands) for i in range(len(b))]) if w.islands else np.ones(len(b), bool)
    ids = [g["GEOID"][i] for i in np.where(keep)[0]]
    if not keep.all():
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            w = spatial.spatial_weights(b[keep].reset_index(drop=True), "queen")
    lon, lat = np.array(g["lon"])[keep], np.array(g["lat"])[keep]
    return ids, sc.haversine(lon, lat), w


@lru_cache(maxsize=None)
def cell_setup(cell):
    name, rng_km = CELLS[cell]
    ids, D, w = geometry(name)
    _, L, _ = simulation_setup("linear", rng_km, D, SEED+cell)
    S = {"T2_scpc20": sc.setup(D, .20), "T2_scpc30": sc.setup(D, .30), "T3_scpc_dist": sc.setup(D, tc.distance_rho(D, 100.))}
    return L, w, S


def job(args):
    cell, start, stop = args
    L, w, S = cell_setup(cell)
    hit = {k: 0 for k in KEYS}; fail = {k: 0 for k in KEYS}; length = {k: [] for k in KEYS}
    for d in range(start, stop):
        rng = np.random.default_rng([SEED+cell, d])
        X, y = simulation_draw("linear", L, None, rng)
        for k in KEYS:
            try:
                if k == "T1_sem":
                    b, lo, hi = tc.sem(X, y, w)
                elif k == "T4_hc3":
                    b, lo, hi = tc.hc3(X, y)
                else:
                    b, lo, hi = tc.scpc_interval(X, y, S[k])
                if not np.isfinite([lo, hi]).all():
                    raise ValueError
                hit[k] += lo <= .5 <= hi; length[k].append(hi-lo)
            except Exception:  # noqa: BLE001 - a failed fit counts as non-coverage
                fail[k] += 1
    return cell, hit, fail, length


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
    draws = 3 if a.smoke else DRAWS; chunk = min(CHUNK, draws)
    tasks = [(c, s, min(s+chunk, draws)) for c in range(len(CELLS)) for s in range(0, draws, chunk)]
    acc = {c: ({k: 0 for k in KEYS}, {k: 0 for k in KEYS}, {k: [] for k in KEYS}) for c in range(len(CELLS))}
    t0 = time.time()
    with ProcessPoolExecutor(a.workers) as ex:
        for cell, h, f, ln in ex.map(job, tasks):
            for k in KEYS:
                acc[cell][0][k] += h[k]; acc[cell][1][k] += f[k]; acc[cell][2][k] += ln[k]
            print({"cell": cell, "s": round(time.time()-t0)}, flush=True)
    cells = [dict(geometry=CELLS[c][0], range_km=CELLS[c][1], n=len(geometry(CELLS[c][0])[0]),
                  coverage={k: acc[c][0][k]/draws for k in KEYS}, failed=acc[c][1],
                  median_length={k: float(np.median(acc[c][2][k])) if acc[c][2][k] else None for k in KEYS})
             for c in range(len(CELLS))]
    passed = {}
    for k in KEYS:
        full = all(c["coverage"][k] >= .86 for c in cells)
        short = all(c["coverage"][k] >= .86 for c in cells if c["range_km"] <= 50)
        passed[k] = "all" if full else ("<=50km" if short else None)
    res = dict(cells=cells, passed=passed, draws=draws, criterion_commit=a.criterion_commit,
               frozen_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FROZEN})
    if a.smoke:
        print(json.dumps(passed), round(time.time()-t0)); return
    OUT.with_suffix(".json").write_text(json.dumps(res, indent=1)+"\n")
    L = ["# Round 71: tract-level spatial intervals", "", f"Criterion commit: `{a.criterion_commit}`. {draws:,} draws per cell.", "",
         "| Geometry | Range km | n | "+" | ".join(KEYS)+" |", "| :--- | ---: | ---: |"+" ---: |"*len(KEYS)]
    for c in cells:
        L.append(f"| {c['geometry']} | {c['range_km']} | {c['n']} | "+" | ".join(f"{c['coverage'][k]:.4f}" for k in KEYS)+" |")
    L += ["", "Median interval length:", "", "| Geometry | Range km | "+" | ".join(KEYS)+" |", "| :--- | ---: |"+" ---: |"*len(KEYS)]
    for c in cells:
        L.append(f"| {c['geometry']} | {c['range_km']} | "+" | ".join("-" if c['median_length'][k] is None else f"{c['median_length'][k]:.4f}" for k in KEYS)+" |")
    L += ["", f"Outcomes: `{json.dumps(passed)}`.", ""]
    OUT.with_suffix(".md").write_text("\n".join(L))
    print(json.dumps(passed))


if __name__ == "__main__":
    main()
