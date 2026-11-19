# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 50: county segregation indices under realistic ACS error (frozen with the criterion).

Truth: the 2024 five-year MI/NY tract counts (``docs/audits/segregation_realistic_counts.csv.gz``).
Each observed count is a Gamma draw (mean = truth, SD = published SE) through a Gaussian copula with
correlation rho between the groups of a tract; the 80 replicates are Gamma draws (mean = observed,
SD = published SE / 2, so that 4/80 * sum (r - x)^2 estimates SE^2 as for ACS replicates) from the same copula. Draws are rounded to whole counts; a zero truth (or zero
observed count) stays zero. Indices: ``census.segregation._indices``; SE = sqrt(4/80 sum (I_r - I)^2) and the
bias correction I - 4 (mean I_r - I), as in ``segregation_replicate``.

Acceptance (per index and design): counties are binned by noise level = max over groups of the median
tract CV (published SE / true count; zero count -> inf) over tracts with a positive total. A bin is
judged when it has >= 5 counties; it passes when, in both rho cells, mean county coverage >= .86 and at
least 90% of its counties cover >= .80. The validated range runs from the lowest bin up to the first
failing judged bin (unjudged bins below the first judged bin are included; an unjudged bin after a
judged one ends the range). Failed draws (undefined index or replicate) count as non-coverage.

Usage: scripts/segregation_realistic_validation.py --criterion-commit SHA [--workers N] [--draws N]
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
from scipy.special import gammaincinv, ndtr
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from census.segregation import _indices  # noqa: E402

COUNTS = ROOT/"docs/audits/segregation_realistic_counts.csv.gz"
OUT = ROOT/"docs/audits/segregation_realistic_validation"
DESIGNS = {"two": ["below", "above"], "three": ["inc_lo", "inc_mid", "inc_hi"]}
CELLS = [("two", 0.), ("two", -.3), ("three", 0.), ("three", -.3)]
BINS = [0., .15, .30, .50, np.inf]
BIN_LABELS = ["[0, .15)", "[.15, .30)", "[.30, .50)", "[.50, inf)"]
# (name, index column of _indices, bias corrected?, judged?)
# Every variant is judged separately; the engine default per index is the variant with the widest
# validated range (ties: the Round 28 default).
PROCS = {"two": [("D_naive", 0, False, True), ("I_bc", 1, True, True), ("H_bc", 2, True, True),
                 ("H_naive", 2, False, True), ("D_bc", 0, True, True), ("I_naive", 1, False, True)],
         "three": [("H_bc", 2, True, True), ("H_naive", 2, False, True)]}
DRAWS = 2000
CHUNK = 250
SEED = 20270801
REPS = 80
Z90 = norm.ppf(.95)
MIN_TRACTS = 5
MIN_COUNTIES = 5
MEAN_MIN, COUNTY_MIN, SHARE_MIN = .86, .80, .90
FROZEN = ["scripts/segregation_realistic_validation.py", "census/segregation.py",
          "docs/audits/segregation_realistic_counts.csv.gz", "docs/audits/segregation_realistic_validation_criterion.md"]


def setup(design):
    """Included tracts (truth, SE), county membership, noise level and true indices."""
    df = pd.read_csv(COUNTS, dtype={"GEOID": str, "county": str})
    g = DESIGNS[design]
    mu = df[g].to_numpy(float); sd = df[[c+"_se" for c in g]].to_numpy(float)
    pos = mu.sum(axis=1) > 0
    counties, excluded = [], []
    for c, idx in df.groupby("county").indices.items():
        (counties if pos[idx].sum() >= MIN_TRACTS else excluded).append(c)
    keep = df.county.isin(counties).to_numpy()
    mu, sd, cty = mu[keep], sd[keep], df.county.to_numpy()[keep]
    members = [np.flatnonzero(cty == c) for c in counties]
    noise, truth = [], []
    for idx in members:
        m, s = mu[idx], sd[idx]
        p = m.sum(axis=1) > 0
        cv = np.where(m > 0, s/np.where(m > 0, m, 1), np.where(s > 0, np.inf, 0.))[p]
        noise.append(float(np.max(np.median(cv, axis=0))))
        truth.append(_indices(m[None])[0])
    return dict(mu=mu, sd=sd, counties=counties, excluded=excluded, members=members,
                noise=np.array(noise), truth=np.array(truth))


def gamma_copula(rng, mean, sd, rho):
    """Gamma(mean, sd) margins, Gaussian copula with equicorrelation rho over the last axis, rounded to
    whole counts as ACS estimates and replicate estimates are (so a zero estimate has zero replicates,
    as in the ACS, where it means no sample cases)."""
    k = mean.shape[-1]
    z = rng.standard_normal(mean.shape)
    if rho:
        L = np.linalg.cholesky(np.full((k, k), rho)+(1-rho)*np.eye(k))
        z = z @ L.T
    u = np.clip(ndtr(z), 1e-15, 1-1e-15)
    pos = (mean > 0) & (sd > 0)
    m1 = np.where(pos, mean, 1.); s1 = np.where(pos, sd, 1.)
    x = gammaincinv(m1**2/s1**2, u)*s1**2/m1
    return np.rint(np.where(pos, x, mean))


def run_chunk(args):
    cell, start, stop = args
    design, rho = CELLS[cell]
    S = setup(design)
    procs = PROCS[design]; C = len(S["counties"])
    hits = np.zeros((C, len(procs))); fails = np.zeros((C, len(procs)))
    err = np.zeros((C, len(procs))); err2 = np.zeros((C, len(procs))); se_sum = np.zeros((C, len(procs)))
    sd_rep = np.broadcast_to(S["sd"]/2, (REPS,)+S["sd"].shape)   # 4/80 * sum of squares -> SE^2
    for d in range(start, stop):
        rng = np.random.default_rng([SEED+cell, d])
        obs = gamma_copula(rng, S["mu"], S["sd"], rho)
        reps = gamma_copula(rng, np.broadcast_to(obs, (REPS,)+obs.shape), sd_rep, rho)
        for c, idx in enumerate(S["members"]):
            cube = np.concatenate((obs[idx][None], reps[:, idx]), axis=0)
            v = _indices(cube)
            raw, rr = v[0], v[1:]
            with np.errstate(invalid="ignore"):
                se = np.sqrt(.05*np.sum((rr-raw)**2, axis=0))
                bc = raw-4*(rr.mean(axis=0)-raw)
            for j, (_, k, corr, _) in enumerate(procs):
                ok = np.isfinite(raw[k]) and np.isfinite(rr[:, k]).all()
                if not ok:
                    fails[c, j] += 1
                    continue
                est = bc[k] if corr else raw[k]
                e = est-S["truth"][c, k]
                hits[c, j] += abs(e) <= Z90*se[k]
                err[c, j] += e; err2[c, j] += e*e; se_sum[c, j] += se[k]
    return cell, hits, fails, err, err2, se_sum


def judge(cov_by_rho, noise):
    """Per bin: n, and per rho mean coverage, share >= .80, min; passed / judged."""
    out = []
    for b, label in enumerate(BIN_LABELS):
        sel = (noise >= BINS[b]) & (noise < BINS[b+1])
        row = dict(bin=label, counties=int(sel.sum()), judged=bool(sel.sum() >= MIN_COUNTIES), cells={})
        ok = True
        for rho, cov in cov_by_rho.items():
            c = cov[sel]
            if not len(c):
                row["cells"][rho] = None; ok = False; continue
            mean, share = float(c.mean()), float(np.mean(c >= COUNTY_MIN))
            row["cells"][rho] = dict(mean=mean, share_ge_80=share, min=float(c.min()))
            ok &= mean >= MEAN_MIN and share >= SHARE_MIN
        row["passed"] = bool(row["judged"] and ok)
        out.append(row)
    return out


def validated_max(bins):
    """Upper edge of the validated noise range, or None."""
    top, seen_judged = None, False
    for b, row in enumerate(bins):
        if not row["judged"]:
            if seen_judged:
                break
            continue
        seen_judged = True
        if not row["passed"]:
            break
        top = BINS[b+1]
    if top is None:
        return None
    return "inf" if np.isinf(top) else float(top)


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
    ap.add_argument("--smoke", action="store_true", help="skip the pin check (never for the audit)")
    a = ap.parse_args()
    if not a.smoke:
        validate_pins(a.criterion_commit)
    t0 = time.time()
    tasks = [(c, s, min(s+CHUNK, a.draws)) for c in range(len(CELLS)) for s in range(0, a.draws, CHUNK)]
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
                  frozen_sha256={p: sha(p) for p in FROZEN}, designs={}, passed={})
    for design in DESIGNS:
        S = setup(design)
        cells = [c for c in range(len(CELLS)) if CELLS[c][0] == design]
        dres = dict(counties=len(S["counties"]), excluded=S["excluded"],
                    noise_bins=np.histogram(S["noise"], BINS)[0].tolist(), procedures={})
        result["passed"][design] = {}
        for j, (name, k, corr, judged) in enumerate(PROCS[design]):
            cov, diag = {}, {}
            for c in cells:
                hits, fails, err, err2, se_sum = acc[c]
                ok = a.draws-fails[:, j]
                cov[str(CELLS[c][1])] = hits[:, j]/a.draws
                with np.errstate(invalid="ignore", divide="ignore"):
                    bias = err[:, j]/ok; sdv = np.sqrt(np.maximum(err2[:, j]/ok-bias**2, 0)); mse = se_sum[:, j]/ok
                diag[str(CELLS[c][1])] = dict(failed_draws=int(fails[:, j].sum()),
                                              median_abs_bias=float(np.nanmedian(np.abs(bias))),
                                              median_se_over_sd=float(np.nanmedian(mse/sdv)))
            bins = judge(cov, S["noise"])
            vmax = validated_max(bins)
            dres["procedures"][name] = dict(judged=judged, bias_corrected=corr, bins=bins, diagnostics=diag,
                                            validated_max_noise=vmax,
                                            county_coverage={r: dict(zip(S["counties"], map(float, v)))
                                                             for r, v in cov.items()})
            if judged:
                result["passed"][design][name] = vmax
        result["designs"][design] = dres
    OUT.with_suffix(".json").write_text(json.dumps(result, indent=1)+"\n")
    write_md(result)
    print("done", round(time.time()-t0), "s", result["passed"])


def write_md(r):
    L = ["# Segregation under realistic ACS error: validation (Round 50)", "",
         "Truth: 2024 five-year MI/NY tract counts; Gamma-copula observed counts and replicates with the "
         "published SEs. Per index: counties binned by noise level (max over groups of the median tract CV); "
         "a judged bin (>= 5 counties) passes when, for rho 0 and -.3, mean county coverage >= .86 and >= 90% "
         "of counties cover >= .80. Failed draws count as non-coverage.", "",
         f"Criterion commit: `{r['criterion_commit']}`. {r['draws_per_cell']:,} draws per cell.", ""]
    for design, d in r["designs"].items():
        L += [f"## {design} groups", "",
              f"{d['counties']} counties (excluded, fewer than {MIN_TRACTS} populated tracts: "
              f"{', '.join(d['excluded']) or 'none'}). Counties per bin: {d['noise_bins']}.", "",
              "| Index | Bin | Counties | Judged | rho 0: mean / share >= .80 / min | rho -.3: mean / share >= .80 / min | Passed |",
              "| :--- | :--- | ---: | :--- | :--- | :--- | :--- |"]
        for name, p in d["procedures"].items():
            for b in p["bins"]:
                cells = []
                for rho in ("0.0", "-0.3"):
                    c = b["cells"].get(rho)
                    cells.append("—" if c is None else f"{c['mean']:.4f} / {c['share_ge_80']:.3f} / {c['min']:.4f}")
                L.append(f"| {name}{'' if p['judged'] else ' (comparison)'} | {b['bin']} | {b['counties']} | "
                         f"{b['judged']} | {cells[0]} | {cells[1]} | {b['passed']} |")
        L += ["", "| Index | Validated noise up to | rho 0: failed draws / median abs bias / median SE/SD | rho -.3 |",
              "| :--- | :--- | :--- | :--- |"]
        for name, p in d["procedures"].items():
            dg = [f"{x['failed_draws']} / {x['median_abs_bias']:.4f} / {x['median_se_over_sd']:.3f}"
                  for x in p["diagnostics"].values()]
            L.append(f"| {name} | {p['validated_max_noise']} | {dg[0]} | {dg[1]} |")
        L.append("")
    L += [f"Outcomes (validated upper noise level per judged index; null = none): `{json.dumps(r['passed'], sort_keys=True)}`.", ""]
    OUT.with_suffix(".md").write_text("\n".join(L))


if __name__ == "__main__":
    main()
