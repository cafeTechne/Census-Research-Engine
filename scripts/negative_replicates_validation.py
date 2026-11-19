# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 51: negative replicate estimates (frozen with the criterion).

A. Segregation. Round 50's design (``scripts/segregation_realistic_validation.py``: truth, Gamma-copula
observed counts, noise bins, acceptance rule), except that the 80 replicates are Gaussian:
observed + (published SE / 2) * z, z from the same Gaussian copula (equicorrelation rho between the
groups of a tract), rounded; a zero observed count keeps zero replicates. Negative replicate counts are
clipped at zero before the index refits (the engine policy under test). Plus an affected-draw check:
pooled coverage over (county, draw) pairs inside the validated range in which at least one replicate
cell was clipped must be >= .86 in both rho cells (not judged below 500 pairs).

B. SMR. Five bands, Round 24 reference rates, equal true populations scaled to E; one high-CV band (CV c),
the others CV .05. Observed band populations Gamma (mean truth, SD CV * truth); replicates Gaussian,
SD = SE / 2 around the observed (independent, not rescaled); O ~ Poisson(1.2 E). Policies
``indirect_standardize(negative_replicates="accept" | "clip")``; combined 90% interval covers 1.2.
Refused draws and O = 0 count as non-coverage. A policy passes with coverage >= .86 in all eight cells.

Usage: scripts/negative_replicates_validation.py --criterion-commit SHA [--workers N] [--draws N] [--smoke]
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
from census.segregation import _indices  # noqa: E402
from census.standardize import indirect_standardize  # noqa: E402

OUT = ROOT/"docs/audits/negative_replicates_validation"
R50_AUDIT = ROOT/"docs/audits/segregation_realistic_validation.json"
SEG_CELLS = [("two", 0.), ("two", -.3), ("three", 0.), ("three", -.3)]
SEG_SEED = 20270901
SMR_RATES = np.array([.0005, .001, .003, .01, .04])
SMR_CELLS = [(e, band, c) for e in (10, 100) for band in (0, 3) for c in (.6, 1.)]
SMR_SEED = 20270911
SMR_TARGET = 1.2
POLICIES = ("accept", "clip")
DRAWS = 2000
CHUNK = 250
AFFECTED_MIN_PAIRS = 500
FROZEN = ["scripts/negative_replicates_validation.py", "scripts/segregation_realistic_validation.py",
          "census/segregation.py", "census/standardize.py", "docs/audits/segregation_realistic_counts.csv.gz",
          "docs/audits/negative_replicates_validation_criterion.md"]


def gaussian_replicates(rng, obs, se, rho):
    """(80, tracts, groups) observed + (se/2) z with copula correlation rho, rounded; zero obs stays zero."""
    k = obs.shape[-1]
    z = rng.standard_normal((r50.REPS,)+obs.shape)
    if rho:
        L = np.linalg.cholesky(np.full((k, k), rho)+(1-rho)*np.eye(k))
        z = z @ L.T
    reps = np.rint(obs+se/2*z)
    return np.where(obs > 0, reps, obs)


def seg_chunk(args):
    cell, start, stop = args
    design, rho = SEG_CELLS[cell]
    S = r50.setup(design)
    procs = r50.PROCS[design]; C = len(S["counties"]); J = len(procs)
    hits = np.zeros((C, J)); fails = np.zeros((C, J))
    aff_n = np.zeros(C); aff_hits = np.zeros((C, J))
    neg_cells = 0; pos_cells = 0
    for d in range(start, stop):
        rng = np.random.default_rng([SEG_SEED+cell, d])
        obs = r50.gamma_copula(rng, S["mu"], S["sd"], rho)
        reps = gaussian_replicates(rng, obs, S["sd"], rho)
        negany = (reps < 0).any(axis=0)
        neg_cells += int(negany.sum()); pos_cells += int((obs > 0).sum())
        clipped = np.maximum(reps, 0.)
        for c, idx in enumerate(S["members"]):
            cube = np.concatenate((obs[idx][None], clipped[:, idx]), axis=0)
            v = _indices(cube)
            raw, rr = v[0], v[1:]
            with np.errstate(invalid="ignore"):
                se = np.sqrt(.05*np.sum((rr-raw)**2, axis=0))
                bc = raw-4*(rr.mean(axis=0)-raw)
            affected = bool(negany[idx].any())
            aff_n[c] += affected
            for j, (_, k, corr, _) in enumerate(procs):
                if not (np.isfinite(raw[k]) and np.isfinite(rr[:, k]).all()):
                    fails[c, j] += 1
                    continue
                est = bc[k] if corr else raw[k]
                h = abs(est-S["truth"][c, k]) <= r50.Z90*se[k]
                hits[c, j] += h
                aff_hits[c, j] += h and affected
    return "seg", cell, (hits, fails, aff_n, aff_hits, np.array([neg_cells, pos_cells], float))


def smr_chunk(args):
    cell, start, stop = args
    e_true, band, c = SMR_CELLS[cell]
    cv = np.full(5, .05); cv[band] = c
    pop = np.repeat(e_true/SMR_RATES.sum(), 5); se = cv*pop
    obs_s = pd.Series([0], index=["synthetic"])
    out = {p: np.zeros(3) for p in POLICIES}    # hits, refused, zero O
    neg_draws = 0
    for d in range(start, stop):
        rng = np.random.default_rng([SMR_SEED+cell, d])
        o = int(rng.poisson(SMR_TARGET*e_true))
        observed = rng.gamma(1/cv**2, cv**2*pop)
        reps = observed[:, None]+se[:, None]/2*rng.standard_normal((5, 80))
        neg_draws += int((reps < 0).any())
        obs_s.iloc[0] = o
        frame = pd.DataFrame([observed], index=obs_s.index)
        for p in POLICIES:
            try:
                row = indirect_standardize(obs_s, frame, SMR_RATES, reps[None], negative_replicates=p).iloc[0]
            except ValueError:
                out[p][1] += 1
                continue
            out[p][2] += o == 0
            out[p][0] += bool(o > 0 and row.smr_lower <= SMR_TARGET <= row.smr_upper)
    return "smr", cell, (out["accept"], out["clip"], np.array([neg_draws], float))


def validate_pins(commit):
    subprocess.run(["git", "merge-base", "--is-ancestor", commit, "HEAD"], cwd=ROOT, check=True)
    for rel in FROZEN:
        if subprocess.check_output(["git", "show", commit+":"+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
            raise ValueError("script/design differs from criterion commit: "+rel)


def sha(path):
    return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--criterion-commit", required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--draws", type=int, default=DRAWS)
    ap.add_argument("--smoke", action="store_true", help="skip the pin check and write nothing (never for the audit)")
    a = ap.parse_args()
    if not a.smoke:
        validate_pins(a.criterion_commit)
    t0 = time.time()
    tasks = [(seg_chunk, (c, s, min(s+CHUNK, a.draws))) for c in range(len(SEG_CELLS)) for s in range(0, a.draws, CHUNK)]
    tasks += [(smr_chunk, (c, s, min(s+CHUNK, a.draws))) for c in range(len(SMR_CELLS)) for s in range(0, a.draws, CHUNK)]
    acc = {}
    with ProcessPoolExecutor(a.workers) as ex:
        futs = [ex.submit(f, x) for f, x in tasks]
        for fut in futs:
            kind, cell, arrs = fut.result()
            key = (kind, cell)
            if key not in acc:
                acc[key] = [x.copy() for x in arrs]
            else:
                for x, y in zip(acc[key], arrs):
                    x += y
            print({"part": kind, "cell": cell, "seconds": round(time.time()-t0)}, flush=True)
    r50_passed = json.loads(R50_AUDIT.read_text())["passed"]
    result = dict(criterion_commit=a.criterion_commit, draws_per_cell=a.draws, seeds=[SEG_SEED, SMR_SEED],
                  frozen_sha256=None if a.smoke else {p: sha(p) for p in FROZEN}, segregation={}, smr={}, passed={})
    seg_pass = {}
    for design in r50.DESIGNS:
        S = r50.setup(design)
        cells = [c for c in range(len(SEG_CELLS)) if SEG_CELLS[c][0] == design]
        neg = {str(SEG_CELLS[c][1]): float(acc[("seg", c)][4][0]/acc[("seg", c)][4][1]) for c in cells}
        dres = dict(counties=len(S["counties"]), noise_bins=np.histogram(S["noise"], r50.BINS)[0].tolist(),
                    share_cells_with_negative_replicate=neg, procedures={})
        seg_pass[design] = {}
        for j, (name, _, corr, _) in enumerate(r50.PROCS[design]):
            cov, fails = {}, {}
            for c in cells:
                hits, f, *_ = acc[("seg", c)]
                cov[str(SEG_CELLS[c][1])] = hits[:, j]/a.draws
                fails[str(SEG_CELLS[c][1])] = int(f[:, j].sum())
            bins = r50.judge(cov, S["noise"])
            vmax = r50.validated_max(bins)
            top = np.inf if vmax == "inf" else (vmax if vmax is not None else -np.inf)
            inside = S["noise"] < top
            affected = {}
            for c in cells:
                _, _, aff_n, aff_hits, _ = acc[("seg", c)]
                n = float(aff_n[inside].sum())
                affected[str(SEG_CELLS[c][1])] = dict(pairs=int(n), coverage=float(aff_hits[inside, j].sum()/n) if n else None)
            judged = all(v["pairs"] >= AFFECTED_MIN_PAIRS for v in affected.values())
            aff_ok = (not judged) or all(v["coverage"] >= r50.MEAN_MIN for v in affected.values())
            prior = r50_passed[design][name]
            ok = vmax is not None and aff_ok
            final = None
            if ok:
                cand = [x for x in (vmax, prior) if x is not None]
                final = min(float("inf") if x == "inf" else x for x in cand) if prior is not None else vmax
                final = "inf" if final == float("inf") else final
            dres["procedures"][name] = dict(bias_corrected=corr, bins=bins, failed_draws=fails,
                                            validated_max_noise=vmax, round50_max_noise=prior,
                                            affected=affected, affected_judged=judged, affected_passed=aff_ok,
                                            clip_validated_max_noise=final)
            seg_pass[design][name] = final
        result["segregation"][design] = dres
    smr_ok = {p: True for p in POLICIES}
    for c, (e, band, cv) in enumerate(SMR_CELLS):
        accept, clip, neg = acc[("smr", c)]
        row = dict(expected=e, high_cv_band=band+1, high_cv=cv, negative_draw_share=float(neg[0]/a.draws))
        for p, arr in (("accept", accept), ("clip", clip)):
            row[p] = dict(coverage=float(arr[0]/a.draws), refused=int(arr[1]), zero_o=int(arr[2]))
            smr_ok[p] = bool(smr_ok[p] and arr[0]/a.draws >= r50.MEAN_MIN)
        result["smr"][str(c)] = row
    result["passed"] = dict(segregation_clip=seg_pass, smr=smr_ok)
    if a.smoke:
        print(json.dumps(result["passed"]))
        for design, d in result["segregation"].items():
            print(design, d["share_cells_with_negative_replicate"])
            for name, p in d["procedures"].items():
                print(" ", name, p["validated_max_noise"], p["affected"], [(b["bin"], b["cells"]) for b in p["bins"] if b["judged"]])
        for row in result["smr"].values():
            print(row)
        return
    OUT.with_suffix(".json").write_text(json.dumps(result, indent=1)+"\n")
    write_md(result)
    print("done", round(time.time()-t0), "s", result["passed"])


def write_md(r):
    L = ["# Negative replicate estimates: validation (Round 51)", "",
         "A. Segregation: Round 50 design with Gaussian replicates (negative counts clipped at zero before the "
         "index refits); Round 50 bin rule plus an affected-draw check (pooled coverage >= .86 over county-draws "
         "with a clipped replicate, inside the validated range). B. SMR: negative band replicates accepted as "
         "published or clipped; coverage >= .86 in all eight cells. Failed or refused draws count as non-coverage.", "",
         f"Criterion commit: `{r['criterion_commit']}`. {r['draws_per_cell']:,} draws per cell.", ""]
    for design, d in r["segregation"].items():
        L += [f"## A. Segregation, {design} groups", "",
              f"{d['counties']} counties; per bin: {d['noise_bins']}. Share of populated tract-group cells with a "
              f"negative replicate: {', '.join(f'rho {k}: {v:.3f}' for k, v in d['share_cells_with_negative_replicate'].items())}.", "",
              "| Index | Bin | Counties | Judged | rho 0: mean / share >= .80 / min | rho -.3: mean / share >= .80 / min | Passed |",
              "| :--- | :--- | ---: | :--- | :--- | :--- | :--- |"]
        for name, p in d["procedures"].items():
            for b in p["bins"]:
                cells = []
                for rho in ("0.0", "-0.3"):
                    c = b["cells"].get(rho)
                    cells.append("—" if c is None else f"{c['mean']:.4f} / {c['share_ge_80']:.3f} / {c['min']:.4f}")
                L.append(f"| {name} | {b['bin']} | {b['counties']} | {b['judged']} | {cells[0]} | {cells[1]} | {b['passed']} |")
        L += ["", "| Index | Clipped range up to | Round 50 range up to | Affected pairs / coverage (rho 0; rho -.3) | Affected check | Clip validated up to |",
              "| :--- | :--- | :--- | :--- | :--- | :--- |"]
        for name, p in d["procedures"].items():
            aff = "; ".join(f"{v['pairs']} / {'—' if v['coverage'] is None else format(v['coverage'], '.4f')}" for v in p["affected"].values())
            chk = ("passed" if p["affected_passed"] else "failed") if p["affected_judged"] else "not judged"
            L.append(f"| {name} | {p['validated_max_noise']} | {p['round50_max_noise']} | {aff} | {chk} | {p['clip_validated_max_noise']} |")
        L.append("")
    L += ["## B. SMR", "", "| E | High-CV band | CV | Draws with a negative band replicate | accept: coverage / refused | clip: coverage / refused |",
          "| ---: | ---: | ---: | ---: | :--- | :--- |"]
    for row in r["smr"].values():
        L.append(f"| {row['expected']} | {row['high_cv_band']} | {row['high_cv']} | {row['negative_draw_share']:.3f} | "
                 f"{row['accept']['coverage']:.4f} / {row['accept']['refused']} | {row['clip']['coverage']:.4f} / {row['clip']['refused']} |")
    L += ["", f"Outcomes: `{json.dumps(r['passed'], sort_keys=True)}`.", ""]
    OUT.with_suffix(".md").write_text("\n".join(L))


if __name__ == "__main__":
    main()
