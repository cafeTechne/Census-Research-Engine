# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 66 S: segregation coverage on GA, TX and AZ county geometry (frozen with the criterion).

Round 52's observation model and judging rules (scripts/segregation_groups_validation.py: Gamma-copula counts with
SD = published SE, replicates with SD = SE/2, bias correction I - 4 (mean I_r - I), counties with >= 5 populated
tracts, noise bins [0, .15) ... [1, inf), a bin with >= 5 counties passes when in both rho cells (0, -.3) mean
county coverage >= .86 and >= 90% of counties cover >= .80), on the truth file
docs/audits/segregation_r66_counts.csv.gz (2019-2023). Designs: black2 (black/nonblack) and pov (below/above)
for each of GA, TX and AZ. Pass: for every two-group procedure the engine validates (bias-corrected D, isolation and
H; segregation.REALISTIC_RANGES), every judged bin inside its validated range passes in every design.

Usage: scripts/r66_segregation_geometry_validation.py --criterion-commit SHA [--workers N] [--draws N] [--smoke]
"""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/"scripts"))
import segregation_groups_validation as r52  # noqa: E402
from census import segregation  # noqa: E402

r52.COUNTS = ROOT/"docs/audits/segregation_r66_counts.csv.gz"
STATES = {"GA": "13", "TX": "48", "AZ": "04"}
DESIGNS = {f"{d}_{k}": (2023, (v,), g) for k, v in STATES.items()
           for d, g in (("black2", ["black", "nonblack"]), ("pov", ["below", "above"]))}
CELLS = [(d, rho) for d in DESIGNS for rho in (0., -.3)]
PROCS = r52.TWO
SEED = 20280901
FROZEN = ["scripts/r66_segregation_geometry_validation.py", "scripts/segregation_groups_validation.py",
          "scripts/segregation_realistic_validation.py", "scripts/r66_segregation_counts.py", "census/segregation.py",
          "docs/audits/segregation_r66_counts.csv.gz", "docs/audits/r66_replication_criterion.md"]
OUT = ROOT/"docs/audits/r66_segregation_geometry_validation"
RANGE_KEY = {"D_bc": ("dissimilarity", "bias_corrected"), "I_bc": ("isolation", "bias_corrected"),
             "H_bc": ("theil_h", "bias_corrected")}


def setup(design):
    release, states, groups = DESIGNS[design]
    return r52.release_setup(release, states, groups)


def run_chunk(args):
    cell, start, stop = args
    design, rho = CELLS[cell]
    S = setup(design); C = len(S["counties"])
    hits = np.zeros((C, len(PROCS))); fails = np.zeros((C, len(PROCS)))
    for d in range(start, stop):
        rng = np.random.default_rng([SEED+cell, d])
        for c, (raw, se, bc, ok) in enumerate(r52.draw_indices(rng, S, rho)):
            for j, (_, k, corr) in enumerate(PROCS):
                if not ok[k]:
                    fails[c, j] += 1; continue
                est = bc[k] if corr else raw[k]
                hits[c, j] += abs(est-S["truth"][c, k]) <= r52.r50.Z90*se[k]
    return cell, hits, fails


def in_range(b, rng_):
    lo, hi = rng_
    return r52.BINS[b] >= lo and r52.BINS[b+1] <= hi


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--criterion-commit"); ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--draws", type=int, default=r52.DRAWS); ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    if not a.smoke:
        subprocess.run(["git", "merge-base", "--is-ancestor", a.criterion_commit, "HEAD"], cwd=ROOT, check=True)
        for rel in FROZEN:
            if subprocess.check_output(["git", "show", a.criterion_commit+":"+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
                raise SystemExit("differs from criterion commit: "+rel)
    draws = 20 if a.smoke else a.draws
    chunk = min(r52.CHUNK, draws)
    tasks = [(c, s, min(s+chunk, draws)) for c in range(len(CELLS)) for s in range(0, draws, chunk)]
    acc = {}; t0 = time.time()
    with ProcessPoolExecutor(a.workers) as ex:
        for cell, h, f in ex.map(run_chunk, tasks):
            if cell in acc:
                acc[cell][0] += h; acc[cell][1] += f
            else:
                acc[cell] = [h, f]
            print({"cell": cell, "s": round(time.time()-t0)}, flush=True)
    designs = {}
    for d in DESIGNS:
        S = setup(d)
        per = {}
        for j, (name, _, _) in enumerate(PROCS):
            cov = {rho: acc[CELLS.index((d, rho))][0][:, j]/draws for rho in (0., -.3)}
            per[name] = r52.judge(cov, S["noise"])
        designs[d] = dict(counties=len(S["counties"]), procedures=per)
    passed = {}
    for name, key in RANGE_KEY.items():
        rng_ = segregation.REALISTIC_RANGES[key+(2,)]
        fails = [(d, row["bin"]) for d, r in designs.items() for b, row in enumerate(r["procedures"][name])
                 if in_range(b, rng_) and row["judged"] and not row["passed"]]
        judged = sum(1 for r in designs.values() for b, row in enumerate(r["procedures"][name])
                     if in_range(b, rng_) and row["judged"])
        passed[name] = dict(range=[rng_[0], "inf" if np.isinf(rng_[1]) else rng_[1]], judged_bins=judged,
                            failed_bins=fails, passed=bool(judged > 0 and not fails))
    res = dict(designs=designs, passed=passed, draws=draws, seed=SEED, criterion_commit=a.criterion_commit,
               frozen_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FROZEN})
    if a.smoke:
        print(json.dumps(passed)); return
    OUT.with_suffix(".json").write_text(json.dumps(res, indent=1, default=str)+"\n")
    L = ["# Round 66 S: segregation coverage on GA, TX and AZ", "", f"Criterion commit: `{a.criterion_commit}`. "
         f"{draws:,} draws per cell.", "", "| Procedure | Validated range | Judged bins | Failed bins | Outcome |",
         "| :--- | :--- | ---: | :--- | :--- |"]
    for name, p in passed.items():
        L.append(f"| {name} | {p['range']} | {p['judged_bins']} | {p['failed_bins'] or 'none'} | "
                 f"{'passes' if p['passed'] else 'fails'} |")
    L += ["", "| Design | Counties | Procedure | Bin | Counties in bin | Mean coverage (rho 0 / -.3) | Passed |",
          "| :--- | ---: | :--- | :--- | ---: | :--- | :--- |"]
    for d, r in designs.items():
        for name, rows in r["procedures"].items():
            for row in rows:
                if row["judged"]:
                    m = " / ".join(f"{row['cells'][rho]['mean']:.3f}" for rho in (0., -.3))
                    L.append(f"| {d} | {r['counties']} | {name} | {row['bin']} | {row['counties']} | {m} | {row['passed']} |")
    OUT.with_suffix(".md").write_text("\n".join(L)+"\n")
    print(json.dumps({k: v["passed"] for k, v in passed.items()}))


if __name__ == "__main__":
    main()
