# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 57: segregation gaps (frozen with the criterion).

A. Clipped replicates on Round 52's race designs (black2, hisp2, race4, race5; rho 0 and negative): Round 50
   observed counts (Gamma copula), Round 51 Gaussian replicates clipped at zero; Round 52 bins and bin rule plus a
   per-bin affected-draw check (pooled coverage >= .86 over county-draws in the bin with a clipped cell, judged
   when >= 500 pairs). Combination: two groups with Round 51's poverty audit (first three bins; a bin counts only
   if its variant also passed Round 51's affected check), black2 and hisp2; four groups race4; five race5.
B. Six groups (race6 = white, black, asian, hisp, multi, other3; rho 0 and -.15): Round 50 Gamma model; H.
C. Same-release county contrasts: Round 50 MI/NY poverty counts (rho 0 and -.3), consecutive counties within a
   state; per-replicate difference SE; binned by the larger noise level; all six two-group variants.
Failed draws count as non-coverage. 2,000 draws per cell; per-draw seeds [20280301 + cell, draw].

Usage: scripts/segregation_gaps_validation.py --criterion-commit SHA [--workers N] [--draws N] [--chunk N] [--smoke]
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
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/"scripts"))
import segregation_realistic_validation as r50  # noqa: E402
import segregation_groups_validation as r52  # noqa: E402
import negative_replicates_validation as r51  # noqa: E402
from census.segregation import _indices  # noqa: E402

COUNTS6 = ROOT/"docs/audits/segregation_r57_counts.csv.gz"
R51_AUDIT = ROOT/"docs/audits/negative_replicates_validation.json"
OUT = ROOT/"docs/audits/segregation_gaps_validation"
RACE6 = ["white", "black", "asian", "hisp", "multi", "other3"]
CELLS = ([("A", d, rho) for d in ("black2", "hisp2", "race4", "race5") for rho in (0., r52.NEG_RHO[d])]
         + [("B", "race6", rho) for rho in (0., -.15)]
         + [("C", "pov_pairs", rho) for rho in (0., -.3)])
DRAWS = 2000
CHUNK = 100
SEED = 20280301
AFFECTED_MIN = 500
FROZEN = ["scripts/segregation_gaps_validation.py", "scripts/segregation_groups_validation.py",
          "scripts/segregation_realistic_validation.py", "scripts/negative_replicates_validation.py",
          "scripts/segregation_r57_counts.py", "census/segregation.py", "docs/audits/segregation_r57_counts.csv.gz",
          "docs/audits/segregation_groups_counts.csv.gz", "docs/audits/segregation_realistic_counts.csv.gz",
          "docs/audits/segregation_gaps_validation_criterion.md"]


def setup6():
    df = pd.read_csv(COUNTS6, dtype={"GEOID": str, "county": str})
    mu = df[RACE6].to_numpy(float); sd = df[[g+"_se" for g in RACE6]].to_numpy(float)
    pos = mu.sum(axis=1) > 0
    counties, members, noise, truth = [], [], [], []
    for c, idx in df.groupby("county").indices.items():
        if pos[idx].sum() < r50.MIN_TRACTS:
            continue
        m, s = mu[idx], sd[idx]; p = m.sum(axis=1) > 0
        cv = np.where(m > 0, s/np.where(m > 0, m, 1), np.where(s > 0, np.inf, 0.))[p]
        counties.append(c); members.append(idx)
        noise.append(float(np.max(np.median(cv, axis=0)))); truth.append(_indices(m[None])[0])
    return dict(mu=mu, sd=sd, counties=counties, members=members, noise=np.array(noise), truth=np.array(truth))


def setup_pairs():
    S = r50.setup("two")
    pairs = []
    for st in ("26", "36"):
        idx = [i for i, c in enumerate(S["counties"]) if c.startswith(st)]
        pairs += [(idx[k], idx[k+1]) for k in range(0, len(idx)-1, 2)]
    S["pairs"] = pairs
    S["pair_noise"] = np.array([max(S["noise"][a], S["noise"][b]) for a, b in pairs])
    S["pair_truth"] = np.array([S["truth"][a]-S["truth"][b] for a, b in pairs])
    return S


def setup(kind, design):
    return r52.setup(design) if kind == "A" else setup6() if kind == "B" else setup_pairs()


def procs(kind, design):
    if kind == "C":
        return r52.TWO
    if kind == "B":
        return r52.MULTI
    return r52.procs(design)


def run_chunk(args):
    cell, start, stop = args
    kind, design, rho = CELLS[cell]
    S = setup(kind, design); P = procs(kind, design)
    units = len(S["pairs"]) if kind == "C" else len(S["counties"])
    hits = np.zeros((units, len(P))); fails = np.zeros((units, len(P)))
    aff_n = np.zeros(units); aff_hits = np.zeros((units, len(P)))
    for d in range(start, stop):
        rng = np.random.default_rng([SEED+cell, d])
        obs = r50.gamma_copula(rng, S["mu"], S["sd"], rho)
        if kind == "A":
            reps = r51.gaussian_replicates(rng, obs, S["sd"], rho)
            negany = (reps < 0).any(axis=0); reps = np.maximum(reps, 0.)
        else:
            sd_rep = np.broadcast_to(S["sd"]/2, (r50.REPS,)+S["sd"].shape)
            reps = r50.gamma_copula(rng, np.broadcast_to(obs, (r50.REPS,)+obs.shape), sd_rep, rho)
            negany = None
        per = []
        for idx in S["members"]:
            v = _indices(np.concatenate((obs[idx][None], reps[:, idx]), axis=0))
            per.append((v[0], v[1:]))
        if kind == "C":
            rows = []
            for a, b in S["pairs"]:
                (ra, rra), (rb, rrb) = per[a], per[b]
                raw = ra-rb; rr = rra-rrb
                with np.errstate(invalid="ignore"):
                    se = np.sqrt(.05*np.sum((rr-raw)**2, axis=0))
                    bca = ra-4*(rra.mean(axis=0)-ra); bcb = rb-4*(rrb.mean(axis=0)-rb)
                ok = np.isfinite(raw) & np.isfinite(rr).all(axis=0)
                rows.append((raw, se, bca-bcb, ok, False))
            truth = S["pair_truth"]
        else:
            rows = []
            for c, idx in enumerate(S["members"]):
                raw, rr = per[c]
                with np.errstate(invalid="ignore"):
                    se = np.sqrt(.05*np.sum((rr-raw)**2, axis=0)); bc = raw-4*(rr.mean(axis=0)-raw)
                ok = np.isfinite(raw) & np.isfinite(rr).all(axis=0)
                rows.append((raw, se, bc, ok, bool(negany[idx].any()) if negany is not None else False))
            truth = S["truth"]
        for u, (raw, se, bc, ok, affected) in enumerate(rows):
            aff_n[u] += affected
            for j, (_, k, corr) in enumerate(P):
                if not ok[k]:
                    fails[u, j] += 1; continue
                h = abs((bc[k] if corr else raw[k])-truth[u, k]) <= r50.Z90*se[k]
                hits[u, j] += h; aff_hits[u, j] += h and affected
    return cell, hits, fails, aff_n, aff_hits


def bin_affected(acc_cells, noise, j):
    """Per bin: (pairs, pooled coverage) per rho cell over county-draws with a clipped cell."""
    out = []
    for b in range(len(r52.BINS)-1):
        sel = (noise >= r52.BINS[b]) & (noise < r52.BINS[b+1])
        row = {}
        for rho, (_, _, aff_n, aff_hits) in acc_cells.items():
            n = float(aff_n[sel].sum())
            row[rho] = dict(pairs=int(n), coverage=float(aff_hits[sel, j].sum()/n) if n else None)
        out.append(row)
    return out


def r51_status(name):
    r = json.loads(R51_AUDIT.read_text())["segregation"]["two"]["procedures"][name]
    st = [((b["passed"] and r["affected_passed"]) if b["judged"] else None) for b in r["bins"][:3]]
    assert r["bins"][3]["counties"] == 0
    return st+[None, None, None]


def validate_pins(commit):
    subprocess.run(["git", "merge-base", "--is-ancestor", commit, "HEAD"], cwd=ROOT, check=True)
    for rel in FROZEN:
        if subprocess.check_output(["git", "show", commit+":"+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
            raise ValueError("script/design differs from criterion commit: "+rel)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--criterion-commit", required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--draws", type=int, default=DRAWS)
    ap.add_argument("--chunk", type=int, default=CHUNK, help="draws per task (seeds are per draw)")
    ap.add_argument("--smoke", action="store_true", help="skip the pin check and write nothing (never for the audit)")
    a = ap.parse_args()
    if not a.smoke:
        validate_pins(a.criterion_commit)
    t0 = time.time()
    tasks = [(c, s, min(s+a.chunk, a.draws)) for c in range(len(CELLS)) for s in range(0, a.draws, a.chunk)]
    acc = {}
    with ProcessPoolExecutor(a.workers) as ex:
        for cell, *arrs in ex.map(run_chunk, tasks):
            if cell not in acc:
                acc[cell] = [x.copy() for x in arrs]
            else:
                for x, y in zip(acc[cell], arrs):
                    x += y
            print({"cell": cell, "seconds": round(time.time()-t0)}, flush=True)
    result = dict(criterion_commit=a.criterion_commit, draws_per_cell=a.draws, seed=SEED,
                  frozen_sha256=None if a.smoke else {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FROZEN},
                  designs={}, combined={})
    status = {}
    for kind, design in dict.fromkeys((k, d) for k, d, _ in CELLS):
        S = setup(kind, design)
        noise = S["pair_noise"] if kind == "C" else S["noise"]
        cells = [c for c in range(len(CELLS)) if CELLS[c][:2] == (kind, design)]
        dres = dict(kind=kind, units=int(len(noise)), noise_bins=np.histogram(noise[np.isfinite(noise)], r52.BINS)[0].tolist(),
                    infinite_noise=int(np.isinf(noise).sum()), procedures={})
        for j, (name, _, corr) in enumerate(procs(kind, design)):
            cov = {str(CELLS[c][2]): acc[c][0][:, j]/a.draws for c in cells}
            bins = r52.judge(cov, noise)
            if kind == "A":
                aff = bin_affected({str(CELLS[c][2]): acc[c] for c in cells}, noise, j)
                for b, row in zip(bins, aff):
                    row_ok = all(v["coverage"] >= r50.MEAN_MIN for v in row.values() if v["pairs"] >= AFFECTED_MIN)
                    b["affected"] = row; b["affected_ok"] = bool(row_ok)
                    b["passed"] = bool(b["passed"] and row_ok)
            st = [(b["passed"] if b["judged"] else None) for b in bins]
            status[(design, name)] = st
            dres["procedures"][name] = dict(bias_corrected=corr, bins=bins, validated_max_noise=r52.range_top(st),
                                            failed_draws={str(CELLS[c][2]): int(acc[c][1][:, j].sum()) for c in cells})
        result["designs"][design] = dres
    for name, _, _ in r52.TWO:
        comb, top = r52.combine({d: status[(d, name)] for d in ("black2", "hisp2")}, ["black2", "hisp2"], extra=r51_status(name))
        result["combined"].setdefault("clip_two", {})[name] = dict(bins=comb, validated_max_noise=top)
        comb, top = r52.combine({"pov_pairs": status[("pov_pairs", name)]}, ["pov_pairs"])
        result["combined"].setdefault("same_release_contrast", {})[name] = dict(bins=comb, validated_max_noise=top)
    for design, key in (("race4", "clip_four"), ("race5", "clip_five"), ("race6", "six")):
        for name, _, _ in r52.MULTI:
            comb, top = r52.combine({design: status[(design, name)]}, [design])
            result["combined"].setdefault(key, {})[name] = dict(bins=comb, validated_max_noise=top)
    result["passed"] = {k: {n: v["validated_max_noise"] for n, v in d.items()} for k, d in result["combined"].items()}
    if a.smoke:
        print(json.dumps(result["passed"]))
        for design, d in result["designs"].items():
            print(design, d["noise_bins"], d["infinite_noise"])
            for name, p in d["procedures"].items():
                print("  ", name, p["validated_max_noise"], [(b["bin"], {r: None if c is None else round(c["mean"], 3) for r, c in b["cells"].items()}, b["passed"]) for b in p["bins"] if b["counties"]])
        return
    OUT.with_suffix(".json").write_text(json.dumps(result, indent=1, default=float)+"\n")
    write_md(result)
    print("done", round(time.time()-t0), "s", result["passed"])


def write_md(r):
    L = ["# Segregation gaps: validation (Round 57)", "",
         "A: clipped Gaussian replicates on Round 52's race designs (bin rule plus a per-bin affected-draw check). "
         "B: six-group H (Gamma model). C: same-release county contrasts on MI/NY poverty (per-replicate "
         "differences). Round 52 bins; a bin with >= 5 units passes when, for both rho cells, mean coverage >= .86 and "
         ">= 90% of units cover >= .80. Combined ranges: a bin counts only if every design judging it passes.", "",
         f"Criterion commit: `{r['criterion_commit']}`. {r['draws_per_cell']:,} draws per cell.", ""]
    for design, d in r["designs"].items():
        L += [f"## {d['kind']}: {design}", "", f"{d['units']} units; per finite bin: {d['noise_bins']}; infinite noise: {d['infinite_noise']}.", "",
              "| Index | Bin | Units | Judged | rho 0: mean / share >= .80 / min | rho negative: mean / share >= .80 / min | Affected (pairs / coverage) | Passed |",
              "| :--- | :--- | ---: | :--- | :--- | :--- | :--- | :--- |"]
        for name, p in d["procedures"].items():
            for b in p["bins"]:
                if not b["counties"]:
                    continue
                cells = ["—" if b["cells"].get(k) is None else
                         f"{b['cells'][k]['mean']:.4f} / {b['cells'][k]['share_ge_80']:.3f} / {b['cells'][k]['min']:.4f}"
                         for k in b["cells"]]
                aff = "; ".join(f"{v['pairs']} / {'—' if v['coverage'] is None else format(v['coverage'], '.4f')}"
                                for v in b.get("affected", {}).values()) or "—"
                L.append(f"| {name} | {b['bin']} | {b['counties']} | {b['judged']} | {cells[0]} | {cells[1]} | {aff} | {b['passed']} |")
            L.append(f"| {name} | **validated to** | | | {p['validated_max_noise']} | | | |")
        L.append("")
    L += ["## Combined ranges", "", "| Set | Index | Bin status (" + ", ".join(r52.BIN_LABELS) + ") | Validated to |",
          "| :--- | :--- | :--- | :--- |"]
    for key, d in r["combined"].items():
        for name, v in d.items():
            st = " ".join({None: "·", True: "pass", False: "FAIL"}[x] for x in v["bins"])
            L.append(f"| {key} | {name} | {st} | {v['validated_max_noise']} |")
    L += ["", f"Outcomes: `{json.dumps(r['passed'], sort_keys=True)}`.", ""]
    OUT.with_suffix(".md").write_text("\n".join(L))


if __name__ == "__main__":
    main()
