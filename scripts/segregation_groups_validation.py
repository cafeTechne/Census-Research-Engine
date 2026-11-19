# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 52: segregation with race/ethnicity groups, four and five groups, period contrasts and OH/PA
(frozen with the criterion).

Round 50's observation model (``scripts/segregation_realistic_validation.py``: rounded Gamma-copula counts
with SD = published SE and replicates with SD = SE/2; ``_indices``; 4/80 SE; bias correction
I - 4 (mean I_r - I)) on the truth file ``docs/audits/segregation_groups_counts.csv.gz``. Counties with fewer
than five populated tracts are excluded. Noise level = max over groups of the median tract CV.

Designs: black2, hisp2, race4, race5 (2024 MI/NY B03002); pov_ohpa, black2_ohpa (2024 OH/PA); contrast
(MI/NY poverty, 2024 minus 2015-2019, independent draws, SE = sqrt(SE24^2 + SE19^2), binned by the larger
noise level). Bins [0, .15), [.15, .30), [.30, .50), [.50, .75), [.75, 1), [1, inf). A bin with >= 5 counties
passes when, in both rho cells (0, -.3; -.2 for five groups), mean county coverage >= .86 and >= 90% of counties cover >= .80.

Combination (group-type blind): per (variant, group count) a bin is validated when every design with that
group count judging it passes and at least one judges it; two-group designs include Round 50's MI/NY poverty
audit. The range runs from the lowest bin through validated bins (unjudged bins before the first judged bin
included) and ends at the first failing or unjudged bin after a judged one.

Usage: scripts/segregation_groups_validation.py --criterion-commit SHA [--workers N] [--draws N] [--smoke]
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

COUNTS = ROOT/"docs/audits/segregation_groups_counts.csv.gz"
OUT = ROOT/"docs/audits/segregation_groups_validation"
R50_AUDIT = ROOT/"docs/audits/segregation_realistic_validation.json"
MINY, OHPA = ("26", "36"), ("39", "42")
DESIGNS = {
    "black2": (2024, MINY, ["black", "nonblack"]),
    "hisp2": (2024, MINY, ["hisp", "nonhisp"]),
    "race4": (2024, MINY, ["white", "black", "hisp", "other4"]),
    "race5": (2024, MINY, ["white", "black", "asian", "hisp", "other"]),
    "pov_ohpa": (2024, OHPA, ["below", "above"]),
    "black2_ohpa": (2024, OHPA, ["black", "nonblack"]),
    "contrast": (None, MINY, ["below", "above"]),
}
# Equicorrelation -.3 is not positive definite for five groups (1 + 4 rho < 0); race5 uses -.2.
NEG_RHO = {d: (-.2 if len(g) == 5 else -.3) for d, (_, _, g) in DESIGNS.items()}
CELLS = [(d, rho) for d in DESIGNS for rho in (0., NEG_RHO[d])]
BINS = [0., .15, .30, .50, .75, 1., np.inf]
BIN_LABELS = ["[0, .15)", "[.15, .30)", "[.30, .50)", "[.50, .75)", "[.75, 1)", "[1, inf)"]
TWO = [("D_naive", 0, False), ("I_bc", 1, True), ("H_bc", 2, True), ("H_naive", 2, False),
       ("D_bc", 0, True), ("I_naive", 1, False)]
MULTI = [("H_bc", 2, True), ("H_naive", 2, False)]
DRAWS = 2000
CHUNK = 250
SEED = 20271001
FROZEN = ["scripts/segregation_groups_validation.py", "scripts/segregation_realistic_validation.py",
          "scripts/segregation_groups_counts.py", "census/segregation.py",
          "docs/audits/segregation_groups_counts.csv.gz", "docs/audits/segregation_groups_validation_criterion.md"]


def procs(design):
    return TWO if len(DESIGNS[design][2]) == 2 else MULTI


def release_setup(release, states, groups):
    df = pd.read_csv(COUNTS, dtype={"GEOID": str, "county": str})
    df = df[(df.release == release) & df.county.str[:2].isin(states)].copy()
    if "other4" in groups:
        df["other4"] = df.other+df.asian; df["other4_se"] = np.hypot(df.other_se, df.asian_se)
    mu = df[groups].to_numpy(float); sd = df[[g+"_se" for g in groups]].to_numpy(float)
    pos = mu.sum(axis=1) > 0
    counties, members, noise, truth = [], [], [], []
    cty = df.county.to_numpy()
    for c, idx in df.groupby("county").indices.items():
        if pos[idx].sum() < r50.MIN_TRACTS:
            continue
        m, s = mu[idx], sd[idx]; p = m.sum(axis=1) > 0
        cv = np.where(m > 0, s/np.where(m > 0, m, 1), np.where(s > 0, np.inf, 0.))[p]
        counties.append(c); members.append(idx)
        noise.append(float(np.max(np.median(cv, axis=0)))); truth.append(_indices(m[None])[0])
    assert all((cty[i] == c).all() for c, i in zip(counties, members))
    return dict(mu=mu, sd=sd, counties=counties, members=members, noise=np.array(noise), truth=np.array(truth))


def setup(design):
    release, states, groups = DESIGNS[design]
    if design != "contrast":
        return release_setup(release, states, groups)
    a, b = release_setup(2024, states, groups), release_setup(2019, states, groups)
    common = sorted(set(a["counties"]) & set(b["counties"]))
    ia = [a["counties"].index(c) for c in common]; ib = [b["counties"].index(c) for c in common]
    return dict(a=a, b=b, ia=ia, ib=ib, counties=common,
                noise=np.maximum(a["noise"][ia], b["noise"][ib]),
                truth=a["truth"][ia]-b["truth"][ib])


def draw_indices(rng, S, rho):
    """Per county: (raw index vector, SE vector, bias-corrected vector)."""
    obs = r50.gamma_copula(rng, S["mu"], S["sd"], rho)
    sd_rep = np.broadcast_to(S["sd"]/2, (r50.REPS,)+S["sd"].shape)
    reps = r50.gamma_copula(rng, np.broadcast_to(obs, (r50.REPS,)+obs.shape), sd_rep, rho)
    out = []
    for idx in S["members"]:
        v = _indices(np.concatenate((obs[idx][None], reps[:, idx]), axis=0))
        raw, rr = v[0], v[1:]
        with np.errstate(invalid="ignore"):
            se = np.sqrt(.05*np.sum((rr-raw)**2, axis=0)); bc = raw-4*(rr.mean(axis=0)-raw)
        ok = np.isfinite(raw) & np.isfinite(rr).all(axis=0)
        out.append((raw, se, bc, ok))
    return out


def run_chunk(args):
    cell, start, stop = args
    design, rho = CELLS[cell]
    S = setup(design); P = procs(design); C = len(S["counties"])
    hits = np.zeros((C, len(P))); fails = np.zeros((C, len(P)))
    for d in range(start, stop):
        rng = np.random.default_rng([SEED+cell, d])
        if design == "contrast":
            A = draw_indices(rng, S["a"], rho); B = draw_indices(rng, S["b"], rho)
            rows = []
            for ia, ib in zip(S["ia"], S["ib"]):
                (ra, sa, ba, oa), (rb, sb, bb, ob) = A[ia], B[ib]
                rows.append((ra-rb, np.hypot(sa, sb), ba-bb, oa & ob))
        else:
            rows = draw_indices(rng, S, rho)
        for c, (raw, se, bc, ok) in enumerate(rows):
            for j, (_, k, corr) in enumerate(P):
                if not ok[k]:
                    fails[c, j] += 1; continue
                est = bc[k] if corr else raw[k]
                hits[c, j] += abs(est-S["truth"][c, k]) <= r50.Z90*se[k]
    return cell, hits, fails


def judge(cov_by_rho, noise):
    out = []
    for b, label in enumerate(BIN_LABELS):
        sel = (noise >= BINS[b]) & (noise < BINS[b+1])
        row = dict(bin=label, counties=int(sel.sum()), judged=bool(sel.sum() >= r50.MIN_COUNTIES), cells={})
        ok = True
        for rho, cov in cov_by_rho.items():
            c = cov[sel]
            if not len(c):
                row["cells"][rho] = None; ok = False; continue
            mean, share = float(c.mean()), float(np.mean(c >= r50.COUNTY_MIN))
            row["cells"][rho] = dict(mean=mean, share_ge_80=share, min=float(c.min()))
            ok &= mean >= r50.MEAN_MIN and share >= r50.SHARE_MIN
        row["passed"] = bool(row["judged"] and ok)
        out.append(row)
    return out


def range_top(status):
    """status: per bin None (unjudged), True (validated) or False (failed). Upper edge or None."""
    top, seen = None, False
    for b, s in enumerate(status):
        if s is None:
            if seen:
                break
            continue
        seen = True
        if not s:
            break
        top = BINS[b+1]
    return None if top is None else ("inf" if np.isinf(top) else float(top))


def r50_status(name):
    """Round 50 MI/NY poverty bins mapped onto the Round 52 bins (its [.50, inf) bin had no counties)."""
    bins = json.loads(R50_AUDIT.read_text())["designs"]["two"]["procedures"][name]["bins"]
    st = [(b["passed"] if b["judged"] else None) for b in bins[:3]]
    assert bins[3]["counties"] == 0
    return st+[None, None, None]


def combine(per_design, names, extra=None):
    """Per bin: validated if every judging design passes and at least one judges."""
    statuses = [per_design[n] for n in names]+([extra] if extra else [])
    combined = []
    for b in range(len(BINS)-1):
        vals = [s[b] for s in statuses if s[b] is not None]
        combined.append(None if not vals else all(vals))
    return combined, range_top(combined)


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
    ap.add_argument("--chunk", type=int, default=CHUNK, help="draws per task (seeds are per draw; results do not depend on it)")
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
                  frozen_sha256=None if a.smoke else {p: sha(p) for p in FROZEN}, designs={}, combined={})
    status = {}
    for design in DESIGNS:
        S = setup(design)
        cells = [c for c in range(len(CELLS)) if CELLS[c][0] == design]
        dres = dict(counties=len(S["counties"]), noise_bins=np.histogram(S["noise"], BINS)[0].tolist(), procedures={})
        for j, (name, _, corr) in enumerate(procs(design)):
            cov, fails = {}, {}
            for c in cells:
                hits, f = acc[c]
                cov[str(CELLS[c][1])] = hits[:, j]/a.draws; fails[str(CELLS[c][1])] = int(f[:, j].sum())
            bins = judge(cov, S["noise"])
            st = [(b["passed"] if b["judged"] else None) for b in bins]
            status[(design, name)] = st
            dres["procedures"][name] = dict(bias_corrected=corr, bins=bins, failed_draws=fails,
                                            validated_max_noise=range_top(st),
                                            county_coverage={r: dict(zip(S["counties"], map(float, v))) for r, v in cov.items()})
        result["designs"][design] = dres
    two = ["black2", "hisp2", "pov_ohpa", "black2_ohpa"]
    for name, _, _ in TWO:
        comb, top = combine({d: status[(d, name)] for d in two}, two, extra=r50_status(name))
        result["combined"].setdefault("two", {})[name] = dict(bins=comb, validated_max_noise=top)
        comb, top = combine({"contrast": status[("contrast", name)]}, ["contrast"])
        result["combined"].setdefault("contrast", {})[name] = dict(bins=comb, validated_max_noise=top)
    for design, key in (("race4", "four"), ("race5", "five")):
        for name, _, _ in MULTI:
            comb, top = combine({design: status[(design, name)]}, [design])
            result["combined"].setdefault(key, {})[name] = dict(bins=comb, validated_max_noise=top)
    result["passed"] = {k: {n: v["validated_max_noise"] for n, v in d.items()} for k, d in result["combined"].items()}
    if a.smoke:
        print(json.dumps(result["passed"]))
        for design, d in result["designs"].items():
            print(design, d["noise_bins"])
            for name, p in d["procedures"].items():
                print("  ", name, p["validated_max_noise"], [(b["bin"], {r: None if c is None else round(c["mean"], 3) for r, c in b["cells"].items()}, b["passed"]) for b in p["bins"] if b["counties"]])
        return
    OUT.with_suffix(".json").write_text(json.dumps(result, indent=1)+"\n")
    write_md(result)
    print("done", round(time.time()-t0), "s", result["passed"])


def write_md(r):
    L = ["# Segregation beyond poverty and income: validation (Round 52)", "",
         "Round 50 observation model on real tract counts and MOEs: 2024 MI/NY race/ethnicity groups (B03002), "
         "four and five groups, OH/PA poverty and Black/non-Black, and the MI/NY poverty change 2015–2019 to "
         "2020–2024. Bin rule as Round 50 on finer bins; engine ranges combine designs (a bin is validated when "
         "every design judging it passes).", "",
         f"Criterion commit: `{r['criterion_commit']}`. {r['draws_per_cell']:,} draws per cell.", ""]
    for design, d in r["designs"].items():
        L += [f"## {design}", "", f"{d['counties']} counties; per bin: {d['noise_bins']}.", "",
              "| Index | Bin | Counties | Judged | rho 0: mean / share >= .80 / min | rho negative: mean / share >= .80 / min | Passed |",
              "| :--- | :--- | ---: | :--- | :--- | :--- | :--- |"]
        for name, p in d["procedures"].items():
            for b in p["bins"]:
                if not b["counties"]:
                    continue
                cells = ["—" if b["cells"].get(rho) is None else
                         f"{b['cells'][rho]['mean']:.4f} / {b['cells'][rho]['share_ge_80']:.3f} / {b['cells'][rho]['min']:.4f}"
                         for rho in b["cells"]]
                L.append(f"| {name} | {b['bin']} | {b['counties']} | {b['judged']} | {cells[0]} | {cells[1]} | {b['passed']} |")
            L.append(f"| {name} | **validated to** | | | {p['validated_max_noise']} | | |")
        L.append("")
    L += ["## Combined engine ranges", "", "| Group count | Index | Bin status (" + ", ".join(BIN_LABELS) + ") | Validated to |",
          "| :--- | :--- | :--- | :--- |"]
    for key, d in r["combined"].items():
        for name, v in d.items():
            st = " ".join({None: "·", True: "pass", False: "FAIL"}[x] for x in v["bins"])
            L.append(f"| {key} | {name} | {st} | {v['validated_max_noise']} |")
    L += ["", f"Outcomes: `{json.dumps(r['passed'], sort_keys=True)}`.", ""]
    OUT.with_suffix(".md").write_text("\n".join(L))


if __name__ == "__main__":
    main()
