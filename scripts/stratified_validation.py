# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 83: stratified analysis, Mantel-Haenszel pooling and additive interaction (frozen with the criterion,
docs/audits/stratified_validation_criterion.md).

Counts (45 cells): K in {2, 4, 8} strata x expected cases per stratum and arm E in {5, 20, 100} x design:
- hom_rr: unexposed risk p0_k = linspace(.05, .30, K), exposed 1.5 p0_k (judge RR_MH; Woolf H1 size);
- hom_or: exposed odds 1.8 x unexposed odds (judge OR_MH; Breslow-Day-Tarone size);
- hom_rd: exposed p0_k + .05 (judge RD_MH);
- hom_irr: rates lambda0_k = linspace(.002, .02, K), exposed 1.5 lambda0_k, Poisson cases, person-time
  E / lambda (judge IRR_MH);
- het: stratum RRs linspace(.7, 2.5, K) (H1 power, reported).
Arm sizes n = round(E / risk). Binomial (Poisson) cases. 2,000 draws per cell.
RERI counts (4 cells): RERI in {0, .5} x baseline p00 in {.05, .20}; RR10 = RR01 = 1.5; 2,000 persons per cell;
A1 delta and A1b bootstrap (B = 999) judged separately.
PUMS (12 cells): Round 32 sampling (scripts/pums_tests_validation.py: weight CV 1, household latent share .25, SDR
factors) x K in {2, 4} strata x smallest-stratum records in {300, 3000} x design hom_rr / hom_or / hom_rd (as for
counts, stratum shares .15 for the smallest and equal otherwise); judge the matching MH2 measure and the replicate
Wald H1 size. PUMS RERI (4 cells): RERI {0, .5} x records {3000, 10000}, p00 .1, RR10 = RR01 = 1.5.
2,000 draws per cell. Pass: 90% coverage >= .86 in every cell per measure; H1 size at .10 in [.07, .13] in every
homogeneous cell per test. Gates: a measure failing only at E = 5 is validated for E >= 20; a PUMS measure failing
only at 300 records is validated from 3,000.
Seeds: counts [20282301 + cell, chunk]; PUMS [20282351 + cell, draw].

Usage: scripts/stratified_validation.py --criterion-commit SHA [--workers N] [--smoke]
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

import pums_tests_validation as r32  # noqa: E402
from census import pums_tests as pt  # noqa: E402
from census import stratified_core as sc  # noqa: E402

CSEED, PSEED = 20282301, 20282351
KS, ES = (2, 4, 8), (5, 20, 100)
DESIGNS = ("hom_rr", "hom_or", "hom_rd", "hom_irr", "het")
CCELLS = [(K, E, d) for K in KS for E in ES for d in DESIGNS]
RCELLS = [(r, p) for r in (0.0, .5) for p in (.05, .20)]
PCELLS = [(K, n, d) for K in (2, 4) for n in (300, 3000) for d in ("hom_rr", "hom_or", "hom_rd")]
PRCELLS = [(r, n) for r in (0.0, .5) for n in (3000, 10000)]
DRAWS, CHUNK, PCHUNK, BOOT = 2000, 250, 50, 999
FROZEN = ["scripts/stratified_validation.py", "census/stratified_core.py", "scripts/pums_tests_validation.py",
          "census/pums_tests.py", "docs/audits/stratified_validation_criterion.md"]
OUT = ROOT/"docs/audits/stratified_validation"


def risks(K, design):
    p0 = np.linspace(.05, .30, K)
    if design == "hom_rr":
        return p0, 1.5*p0, ("rr", 1.5)
    if design == "hom_or":
        o = 1.8*p0/(1-p0)
        return p0, o/(1+o), ("or", 1.8)
    if design == "hom_rd":
        return p0, p0+.05, ("rd", .05)
    if design == "het":
        return p0, np.linspace(.7, 2.5, K)*p0, (None, None)
    raise ValueError(design)


def count_job(args):
    kind, cell, chunk, n_draws = args
    rng = np.random.default_rng([CSEED+(0 if kind == "c" else 100)+cell, chunk])
    if kind == "r":
        reri_true, b = RCELLS[cell]
        rr11 = 1.5+1.5-1+reri_true
        p = np.array([b, 1.5*b, 1.5*b, rr11*b]); n = np.full(4, 2000.)
        cases = rng.binomial(2000, p, (n_draws, 4)).astype(float)
        res = sc.reri_counts(cases, np.tile(n, (n_draws, 1)), B=BOOT, rng=rng)
        return kind, cell, dict(delta=int(((res["lower"] <= reri_true) & (reri_true <= res["upper"])).sum()),
                                boot=int(((res["boot_lower"] <= reri_true) & (reri_true <= res["boot_upper"])).sum()))
    K, E, design = CCELLS[cell]
    out = {}
    if design == "hom_irr":
        l0 = np.linspace(.002, .02, K); l1 = 1.5*l0
        t0, t1 = E/l0, E/l1
        a = rng.poisson(E, (n_draws, K)).astype(float); c = rng.poisson(E, (n_draws, K)).astype(float)
        r = sc.mh_rate_ratio(a, np.tile(t1, (n_draws, 1)), c, np.tile(t0, (n_draws, 1)))
        out["irr"] = int(((r["lower"] <= 1.5) & (1.5 <= r["upper"])).sum())
        return kind, cell, out
    p0, p1, (m, true) = risks(K, design)
    n1 = np.round(E/p1); n0 = np.round(E/p0)
    a = rng.binomial(n1.astype(int), p1, (n_draws, K)).astype(float); c = rng.binomial(n0.astype(int), p0, (n_draws, K)).astype(float)
    b, d = n1-a, n0-c
    pooled = sc.mh_pooled(a, b, c, d)
    if m is not None:
        out[m] = int(((pooled[m]["lower"] <= true) & (true <= pooled[m]["upper"])).sum())
    _, p_bd, _ = sc.breslow_day_tarone(a, b, c, d, pooled["or"]["estimate"])
    _, p_w, _ = sc.woolf_rr(a, b, c, d, pooled["rr"]["estimate"])
    out["bd_reject"] = int((p_bd <= .10).sum()); out["woolf_reject"] = int((p_w <= .10).sum())
    return kind, cell, out


def pums_sample(rng, size, K, design=None, reri_true=None):
    sigma = r32.sigma_for(1.0)
    shares = np.array([.15]+[.85/(K-1)]*(K-1)) if K else None
    m = int(size/(.15 if K else 1)/2.5)+1
    u = rng.uniform(0, 1, m)
    pi = np.exp(sigma*r32.field(r32.GRID)); cdf = np.cumsum(pi); cdf /= cdf[-1]
    g = np.sort(np.interp(u, cdf, r32.GRID))
    w = 1/np.exp(sigma*r32.field(g))
    hs = 1+rng.poisson(1.5, m); idx = np.repeat(np.arange(m), hs); n = len(idx)
    lat = np.sqrt(.25)*rng.standard_normal(m)[idx]+np.sqrt(.75)*rng.standard_normal(n)
    gp = g[idx]
    W = (w[:, None]*np.column_stack((np.ones(m), pt.sdr_factors(m))))[idx]
    if reri_true is not None:
        e = (rng.random(n) < 1/(1+np.exp(-(lat+.5*np.sin(2*np.pi*gp))))).astype(int)
        f = (rng.random(n) < .4).astype(int)
        b = .1; rr11 = 2+reri_true
        p = np.choose(e+2*f, [b, 1.5*b, 1.5*b, rr11*b])
        y = (rng.random(n) < p).astype(int)
        return y, e, f, W
    s = np.searchsorted(np.cumsum(shares), np.clip(stats_norm_cdf(lat), 0, .999999), side="right")
    e = (rng.random(n) < 1/(1+np.exp(-(.3*s-.5+.5*np.sin(2*np.pi*gp))))).astype(int)
    p0, p1, _ = risks(K, design)
    p = np.where(e == 1, p1[s], p0[s])
    y = (rng.random(n) < p).astype(int)
    return y, e, s, W


def stats_norm_cdf(x):
    from scipy import stats
    return stats.norm.cdf(x)


def pums_job(args):
    kind, cell, start, stop = args
    out = {}
    for dr in range(start, stop):
        rng = np.random.default_rng([PSEED+(0 if kind == "p" else 100)+cell, dr])
        if kind == "pr":
            reri_true, size = PRCELLS[cell]
            y, e, f, W = pums_sample(rng, size, 0, reri_true=reri_true)
            cells = e+2*f
            risk = np.stack([(W[cells == k]*y[cells == k, None]).sum(0)/W[cells == k].sum(0) for k in range(4)], axis=1)
            res = sc.reri(risk[0], reps=risk[1:])
            out["reri"] = out.get("reri", 0)+int(res["lower"] <= reri_true <= res["upper"])
            continue
        K, size, design = PCELLS[cell]
        y, e, s, W = pums_sample(rng, size, K, design)
        _, (m, true) = None, risks(K, design)[2]
        est, hom, _, _ = sc.mh_replicate(y, e, s, W, list(range(K)))
        out[m] = out.get(m, 0)+int(est[m]["lower"] <= true <= est[m]["upper"])
        out["wald_reject"] = out.get("wald_reject", 0)+int(hom[m]["p"] <= .10)
    return kind, cell, out


def job(a):
    return count_job(a) if a[0] in ("c", "r") else pums_job(a)


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
    draws = 20 if a.smoke else DRAWS
    ch, pch = (10, 10) if a.smoke else (CHUNK, PCHUNK)
    tasks = [("c", c, k, ch) for c in range(len(CCELLS)) for k in range(draws//ch)]
    tasks += [("r", c, k, ch) for c in range(len(RCELLS)) for k in range(draws//ch)]
    tasks += [("p", c, s, min(s+pch, draws)) for c in range(len(PCELLS)) for s in range(0, draws, pch)]
    tasks += [("pr", c, s, min(s+pch, draws)) for c in range(len(PRCELLS)) for s in range(0, draws, pch)]
    acc = {}
    t0 = time.time()
    with ProcessPoolExecutor(a.workers) as ex:
        for i, (kind, cell, res) in enumerate(ex.map(job, tasks, chunksize=1)):
            d = acc.setdefault((kind, cell), {})
            for k, v in res.items():
                d[k] = d.get(k, 0)+v
            if i % 200 == 0:
                print({"done": i, "of": len(tasks), "s": round(time.time()-t0)}, flush=True)
    rows = []
    for (kind, cell), r in sorted(acc.items()):
        desc = {"c": CCELLS, "r": RCELLS, "p": PCELLS, "pr": PRCELLS}[kind][cell]
        rows.append(dict(kind=kind, cell=list(desc), **{k: v/draws for k, v in r.items()}))

    def judge(kind, key, gate_pos=None, gate_val=None, select=lambda r: True):
        sub = [r for r in rows if r["kind"] == kind and key in r and select(r)]
        fails = [r for r in sub if r[key] < .86]
        gated = bool(fails) and gate_pos is not None and all(r["cell"][gate_pos] == gate_val for r in fails)
        return dict(passed=not fails, range_gated=gated, min=min((r[key] for r in sub), default=None), cells=len(sub))

    def size(kind, key, select):
        sub = [r for r in rows if r["kind"] == kind and key in r and select(r)]
        return dict(passed=all(.07 <= r[key] <= .13 for r in sub), min=min((r[key] for r in sub), default=None),
                    max=max((r[key] for r in sub), default=None), cells=len(sub))
    outcome = {
        "MH_rr": judge("c", "rr", 1, 5), "MH_or": judge("c", "or", 1, 5), "MH_rd": judge("c", "rd", 1, 5),
        "MH_irr": judge("c", "irr", 1, 5),
        "H1_woolf": size("c", "woolf_reject", lambda r: r["cell"][2] == "hom_rr"),
        "H1_breslow_day": size("c", "bd_reject", lambda r: r["cell"][2] == "hom_or"),
        "RERI_delta": judge("r", "delta"), "RERI_boot": judge("r", "boot"),
        "MH2_rr": judge("p", "rr", 1, 300), "MH2_or": judge("p", "or", 1, 300), "MH2_rd": judge("p", "rd", 1, 300),
        "H1_pums_wald": size("p", "wald_reject", lambda r: True), "RERI_pums": judge("pr", "reri", 1, 3000)}
    out = dict(rows=rows, outcome=outcome, draws=draws, criterion_commit=a.criterion_commit, seconds=round(time.time()-t0),
               frozen_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FROZEN})
    if a.smoke:
        print(json.dumps({k: v["passed"] for k, v in outcome.items()}), out["seconds"]); return
    OUT.with_suffix(".json").write_text(json.dumps(out, indent=1)+"\n")
    L = ["# Round 83: stratified analysis, Mantel-Haenszel pooling and additive interaction", "",
         f"Criterion commit: `{a.criterion_commit}`. {draws} draws per cell; 90% intervals; H1 at .10. Author "
         "self-review, not independent.", "", "| Family | Outcome | Min (coverage or size) | Max | Cells |",
         "| :--- | :--- | ---: | ---: | ---: |"]
    for k, v in outcome.items():
        res = "pass" if v["passed"] else ("pass with gate" if v.get("range_gated") else "fail")
        L.append(f"| {k} | {res} | {v['min']:.3f} | {v.get('max') if v.get('max') is None else round(v['max'], 3)} | {v['cells']} |")
    L += ["", "## Cells", "", "| Kind | Cell | Values |", "| :--- | :--- | :--- |"]
    L += [f"| {r['kind']} | {r['cell']} | "+", ".join(f"{k} {v:.3f}" for k, v in r.items() if k not in ("kind", "cell"))+" |"
          for r in rows]
    L.append("")
    OUT.with_suffix(".md").write_text("\n".join(L))
    print(json.dumps({k: (v["passed"], v.get("range_gated")) for k, v in outcome.items()}))


if __name__ == "__main__":
    main()
