# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 84: marginal risk ratios and differences, prevalence ratios, attributable fractions and dose-response
(frozen with the criterion, docs/audits/epi_measures_validation_criterion.md).

Area (18 cells): geometry {MI+NY counties (145), 1,000 MI tracts sampled once} with trials n_i = round(n_eff_i)
from docs/audits/sae_extensions_neff.csv.gz x mean prevalence {.05, .15, .35} x marginal RR {1.0, 1.3, 1.8}.
Exposure x ~ N(0, 1) and confounder z (corr .4) fixed per cell; logit p_i = b0 + b1 x_i + .3 z_i with b0, b1 set by
bisection so that the n-weighted mean risk is the prevalence and the marginal RR (x = +1 vs x = -1) is the target;
y_i ~ BetaBinomial(n_i, p_i, ICC .01). G1a (HC3 delta) RR, RD and F1 PAF (x set to -1) judged against the same
quantities from the true model on these areas. D1 area: quintile dummies of x; size of the trend test in the
RR = 1 cells.
PUMS (24 cells): Round 32 sampling (weight CV 1, household latent share .25, SDR factors) x prevalence {.05, .15,
.35} x records {1,000, 5,000} x design {bin_effect (logit coefficient log 1.6 on a binary exposure), bin_null,
ord3_null, ord3_lin (coefficients 0, .3, .6)}; confounder z (household latent) in exposure and outcome. Targets:
the same estimators on a 300,000-household reference population with unit weights. Judged: G1p RR, RD, F1 PAF and
P1 PR (binary designs); D1 trend size (ord3_null). P1b robust and D1 power reported.
2,000 draws per cell. Pass: 90% coverage >= .86 in every cell per quantity; D1 size at .10 in [.07, .13] in every
null cell (area and PUMS separately). Gate: a PUMS quantity failing only at 1,000 records is validated from 5,000.
Seeds: area [20282401 + cell, draw]; PUMS [20282451 + cell, draw]; reference [20282499, prevalence, design].

Usage: scripts/epi_measures_validation.py --criterion-commit SHA [--workers N] [--smoke]
"""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/"scripts"))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import pums_tests_validation as r32  # noqa: E402
from census import epi_measures_core as em  # noqa: E402
from census import pums_tests as pt  # noqa: E402

ASEED, PSEED, RSEED = 20282401, 20282451, 20282499
NEFF = ROOT/"docs/audits/sae_extensions_neff.csv.gz"
PREVS = (.05, .15, .35)
ACELLS = [(g, p, rr) for g in ("counties", "tracts") for p in PREVS for rr in (1.0, 1.3, 1.8)]
PCELLS = [(p, n, d) for p in PREVS for n in (1000, 5000) for d in ("bin_effect", "bin_null", "ord3_null", "ord3_lin")]
DRAWS, CHUNK = 2000, 50
FROZEN = ["scripts/epi_measures_validation.py", "census/epi_measures_core.py", "scripts/pums_tests_validation.py",
          "census/pums_tests.py", "docs/audits/sae_extensions_neff.csv.gz",
          "docs/audits/epi_measures_validation_criterion.md"]
OUT = ROOT/"docs/audits/epi_measures_validation"


def area_design(cell):
    g, prev, rr = ACELLS[cell]
    f = pd.read_csv(NEFF, dtype={"GEOID": str, "state": str})
    n = f[f.level == "county"].n_eff.to_numpy() if g == "counties" else \
        np.random.default_rng([ASEED, 999]).choice(f[(f.level == "tract") & (f.state == "26")].n_eff.to_numpy(), 1000, replace=False)
    n = np.maximum(10, np.round(n))
    rng = np.random.default_rng([ASEED+cell, 999999])
    x = rng.standard_normal(len(n)); z = .4*x+np.sqrt(1-.16)*rng.standard_normal(len(n))
    X = np.column_stack([np.ones(len(n)), x, z])
    w = n/n.sum()

    def risk(b0, b1, xv=None):
        xx = x if xv is None else np.full(len(n), xv)
        return w@em.expit(b0+b1*xx+.3*z)

    def solve_b0(b1):
        lo, hi = -10.0, 5.0
        for _ in range(60):
            mid = (lo+hi)/2
            lo, hi = (mid, hi) if risk(mid, b1) < prev else (lo, mid)
        return (lo+hi)/2
    b1 = 0.0
    if rr != 1.0:
        lo, hi = 0.0, 3.0
        for _ in range(60):
            mid = (lo+hi)/2; b0 = solve_b0(mid)
            lo, hi = (mid, hi) if risk(b0, mid, 1)/risk(b0, mid, -1) < rr else (lo, mid)
        b1 = (lo+hi)/2
    b0 = solve_b0(b1)
    r_hi, r_lo, r_obs = risk(b0, b1, 1), risk(b0, b1, -1), risk(b0, b1)
    truth = dict(rr=r_hi/r_lo, rd=r_hi-r_lo, paf=1-r_lo/r_obs)
    q = np.quantile(x, [.2, .4, .6, .8]); lev = np.digitize(x, q)
    D = np.eye(5)[lev][:, 1:]
    return n, X, em.expit(X@np.array([b0, b1, .3])), truth, np.column_stack([np.ones(len(n)), D, z])


def area_job(args):
    cell, start, stop = args
    g, prev, rr = ACELLS[cell]
    n, X, p, truth, XD = area_design(cell)
    acc = dict(rr=0, rd=0, paf=0, trend_reject=0, failed=0)
    icc = .01
    for d in range(start, stop):
        rng = np.random.default_rng([ASEED+cell, d])
        a = p*(1-icc)/icc; bb = (1-p)*(1-icc)/icc
        y = rng.binomial(n.astype(int), rng.beta(a, bb))/n
        try:
            r = em.area_marginal(y, X, n, [1], -1.0, 1.0)
            acc["rr"] += int(r["rr_lower"] <= truth["rr"] <= r["rr_upper"])
            acc["rd"] += int(r["rd_lower"] <= truth["rd"] <= r["rd_upper"])
            acc["paf"] += int(min(r["paf_lower"], r["paf_upper"]) <= truth["paf"] <= max(r["paf_lower"], r["paf_upper"]))
            if rr == 1.0:
                levels = [np.eye(5)[k][1:] for k in range(5)]
                dr = em.area_dose(y, XD, n, [1, 2, 3, 4], levels)
                acc["trend_reject"] += int(dr["trend_p"] <= .10)
        except (np.linalg.LinAlgError, ValueError, FloatingPointError):
            acc["failed"] += 1
    return "a", cell, acc


def persons(rng, g, design, prev_b0):
    H = len(g); size = 1+rng.poisson(1.5, H); idx = np.repeat(np.arange(H), size); n = len(idx)
    z = np.sqrt(.25)*rng.standard_normal(H)[idx]+np.sqrt(.75)*rng.standard_normal(n)
    gp = g[idx]
    if design.startswith("bin"):
        e = (rng.random(n) < em.expit(-.3+.6*z+.4*np.sin(2*np.pi*gp))).astype(float)
        X = np.column_stack([np.ones(n), e, z])
        beta = np.array([prev_b0, np.log(1.6) if design == "bin_effect" else 0.0, .5])
    else:
        lev = np.digitize(.6*z+.4*np.sin(2*np.pi*gp)+.8*rng.standard_normal(n), [-.5, .5])
        D = np.eye(3)[lev][:, 1:]
        X = np.column_stack([np.ones(n), D, z])
        beta = np.array([prev_b0, 0.0, 0.0, .5]) if design == "ord3_null" else np.array([prev_b0, .3, .6, .5])
    y = (rng.random(n) < em.expit(X@beta)).astype(float)
    return idx, X, y


def b0_for(prev, design):
    rng = np.random.default_rng([RSEED, 1])
    lo, hi = -8.0, 3.0
    for _ in range(40):
        mid = (lo+hi)/2
        _, X, _ = persons(np.random.default_rng([RSEED, 2]), rng.uniform(0, 1, 20000), design, mid)
        beta = np.array([mid, np.log(1.6) if design == "bin_effect" else 0, .5]) if design.startswith("bin") else \
            (np.array([mid, 0, 0, .5]) if design == "ord3_null" else np.array([mid, .3, .6, .5]))
        lo, hi = (mid, hi) if em.expit(X@beta).mean() < prev else (lo, mid)
    return (lo+hi)/2


def reference(prev, design):
    b0 = b0_for(prev, design)
    rng = np.random.default_rng([RSEED, int(100*prev), ("bin_effect", "bin_null", "ord3_null", "ord3_lin").index(design)])
    _, X, y = persons(rng, rng.uniform(0, 1, 300000), design, b0)
    w = np.ones(len(y))
    out = dict(b0=b0)
    if design.startswith("bin"):
        b = em.logit_fit(y, X, w)
        r, _ = em.marginal_risks(b, X, w, [1], [0.0, 1.0]); ro, _ = em.observed_risk(b, X, w)
        out.update(rr=r[1]/r[0], rd=r[1]-r[0], paf=1-r[0]/ro, pr=float(np.exp(em.poisson_fit(y, X, w)[1])))
    return out


def pums_job(args):
    cell, start, stop, ref = args
    prev, size, design = PCELLS[cell]
    sigma = r32.sigma_for(1.0)
    m = int(size/2.5)+1
    acc = dict(rr=0, rd=0, paf=0, pr=0, pr_robust=0, trend_reject=0, failed=0)
    for d in range(start, stop):
        rng = np.random.default_rng([PSEED+cell, d])
        u = rng.uniform(0, 1, m)
        pi = np.exp(sigma*r32.field(r32.GRID)); cdf = np.cumsum(pi); cdf /= cdf[-1]
        g = np.sort(np.interp(u, cdf, r32.GRID)); w = 1/np.exp(sigma*r32.field(g))
        idx, X, y = persons(rng, g, design, ref["b0"])
        W = (w[:, None]*np.column_stack((np.ones(m), pt.sdr_factors(m))))[idx]
        try:
            if design.startswith("bin"):
                r = em.replicate_marginal(y, X, W, [1], 0.0, 1.0)
                acc["rr"] += int(r["rr_lower"] <= ref["rr"] <= r["rr_upper"])
                acc["rd"] += int(r["rd_lower"] <= ref["rd"] <= r["rd_upper"])
                acc["paf"] += int(min(r["paf_lower"], r["paf_upper"]) <= ref["paf"] <= max(r["paf_lower"], r["paf_upper"]))
                p = em.prevalence_ratio(y, X, W, 1)
                acc["pr"] += int(p["lower"] <= ref["pr"] <= p["upper"])
                acc["pr_robust"] += int(p["robust_lower"] <= ref["pr"] <= p["robust_upper"])
            else:
                dr = em.replicate_dose(y, X, W, [1, 2], [np.array([0., 0.]), np.array([1., 0.]), np.array([0., 1.])])
                acc["trend_reject"] += int(dr["trend_p"] <= .10)
        except (np.linalg.LinAlgError, ValueError, FloatingPointError):
            acc["failed"] += 1
    return "p", cell, acc


def job(a):
    return area_job(a[1:]) if a[0] == "a" else pums_job(a[1:])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--criterion-commit"); ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    if not a.smoke:
        subprocess.run(["git", "merge-base", "--is-ancestor", a.criterion_commit, "HEAD"], cwd=ROOT, check=True)
        for rel in FROZEN:
            if subprocess.check_output(["git", "show", a.criterion_commit+":"+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
                raise SystemExit("differs from criterion commit: "+rel)
    t0 = time.time()
    combos = sorted({(p, d) for p, _, d in PCELLS})
    with ProcessPoolExecutor(min(a.workers, 12)) as ex:
        refs = dict(zip(combos, ex.map(reference, *zip(*combos))))
    print({"references_s": round(time.time()-t0)}, flush=True)
    draws, ch = (4, 2) if a.smoke else (DRAWS, CHUNK)
    tasks = [("a", c, s, min(s+ch, draws)) for c in range(len(ACELLS)) for s in range(0, draws, ch)]
    tasks += [("p", c, s, min(s+ch, draws), refs[(PCELLS[c][0], PCELLS[c][2])]) for c in range(len(PCELLS))
              for s in range(0, draws, ch)]
    acc = {}
    with ProcessPoolExecutor(a.workers) as ex:
        for i, (kind, cell, res) in enumerate(ex.map(job, tasks, chunksize=1)):
            dd = acc.setdefault((kind, cell), {})
            for k, v in res.items():
                dd[k] = dd.get(k, 0)+v
            if i % 200 == 0:
                print({"done": i, "of": len(tasks), "s": round(time.time()-t0)}, flush=True)
    rows = []
    for (kind, cell), r in sorted(acc.items()):
        desc = (ACELLS if kind == "a" else PCELLS)[cell]
        used = draws-r["failed"]
        rows.append(dict(kind=kind, cell=list(desc), failed=r["failed"],
                         **{k: v/used for k, v in r.items() if k != "failed"}))

    def applies(r, key):
        if r["kind"] == "a":
            return key != "trend_reject" or r["cell"][2] == 1.0
        d = r["cell"][2]
        return (key in ("rr", "rd", "paf", "pr", "pr_robust") and d.startswith("bin")) or \
            (key == "trend_reject" and d == "ord3_null")

    def judge(kind, key, gate=None):
        sub = [r for r in rows if r["kind"] == kind and applies(r, key)]
        fails = [r for r in sub if r[key] < .86]
        gated = bool(fails) and gate is not None and all(r["cell"][1] == gate for r in fails)
        return dict(passed=not fails, gated=gated, min=min(r[key] for r in sub), cells=len(sub))

    def size(kind):
        sub = [r for r in rows if r["kind"] == kind and applies(r, "trend_reject")]
        vals = [r["trend_reject"] for r in sub]
        return dict(passed=all(.07 <= v <= .13 for v in vals), min=min(vals), max=max(vals), cells=len(sub))
    outcome = {"G1a_rr": judge("a", "rr"), "G1a_rd": judge("a", "rd"), "F1a_paf": judge("a", "paf"),
               "D1a_size": size("a"), "G1p_rr": judge("p", "rr", 1000), "G1p_rd": judge("p", "rd", 1000),
               "F1p_paf": judge("p", "paf", 1000), "P1_pr": judge("p", "pr", 1000), "P1b_robust": judge("p", "pr_robust"),
               "D1p_size": size("p")}
    out = dict(rows=rows, outcome=outcome, references={f"{p}/{d}": v for (p, d), v in refs.items()}, draws=draws,
               criterion_commit=a.criterion_commit, seconds=round(time.time()-t0),
               frozen_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FROZEN})
    if a.smoke:
        print(json.dumps({k: v["passed"] for k, v in outcome.items()}), out["seconds"]); return
    OUT.with_suffix(".json").write_text(json.dumps(out, indent=1, default=float)+"\n")
    L = ["# Round 84: marginal risk ratios and differences, prevalence ratios, attributable fractions, dose-response",
         "", f"Criterion commit: `{a.criterion_commit}`. {draws} draws per cell; 90% intervals; trend tests at .10. "
         "P1b (design-blind robust SE) is reported only. Author self-review, not independent.", "",
         "| Quantity | Outcome | Min | Max | Cells |", "| :--- | :--- | ---: | ---: | ---: |"]
    for k, v in outcome.items():
        res = "pass" if v["passed"] else ("pass with gate (from 5,000 records)" if v.get("gated") else "fail")
        L.append(f"| {k} | {res} | {v['min']:.3f} | {v.get('max', '')} | {v['cells']} |")
    L += ["", "| Kind | Cell | Values |", "| :--- | :--- | :--- |"]
    L += [f"| {r['kind']} | {r['cell']} | "+", ".join(f"{k} {v:.3f}" for k, v in r.items() if k not in ("kind", "cell", "failed"))
          + f" (failed {r['failed']}) |" for r in rows]
    L.append("")
    OUT.with_suffix(".md").write_text("\n".join(L))
    print(json.dumps({k: (v["passed"], v.get("gated")) for k, v in outcome.items()}))


if __name__ == "__main__":
    main()
