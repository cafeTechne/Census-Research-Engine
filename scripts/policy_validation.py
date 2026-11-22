# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 78: staggered-adoption DiD and synthetic control (frozen with the criterion,
docs/audits/policy_validation_criterion.md).

Panel: N = 51 units (states + DC), T in {12, 18} annual periods, Y_it = a_i + .1 t + tau_it + e_it + s_it with
a_i ~ N(10, 3^2), AR(1) errors e (marginal SD 1, rho in {.3, .7}) and ACS-like sampling error s_it ~ N(0, se_it^2),
se_it = cv_i (a_i + .1 t), cv_i log-uniform on [.01, .08] (fixed per cell).
Staggered (8 cells: T x rho x effect): cohorts first treated at (5, 7, 9) for T = 12 and (7, 10, 13) for T = 18,
ten units each, 21 never treated (assignment fixed per cell). Effect "constant" tau = -2, "growing" tau = -1 - .5 e
for event time e >= 0. S1 Callaway-Sant'Anna (never-treated controls, B = 999 multiplier draws) and S2 Sun-Abraham.
Targets: overall ATT (cohort-size weighted over post (g, t) cells) and each event-time effect (e != -1; 0 before
treatment). Pass: 90% coverage >= .86 for the overall ATT and every event time in every cell, judged per method
(S1, S1r with ACS variance added, S2); uniform-band coverage reported.
Synthetic control (12 cells: T x rho x effect in {none, constant, growing}): unit 0 treated (a_0 = 10, the median),
50 donors never treated, treatment at T0 = T - 3. C1 placebo-in-space test at .10: pass if rejection rate <= .10 in
every no-effect cell (power reported). C2 conformal 90% intervals per post period (grid: gap +- 6 SD of the
pre-period gaps, 121 points): pass if coverage >= .86 for every post period in every cell. Pre-fit flag: treated
pre-RMSPE > 2 x median placebo pre-RMSPE (share reported).
1,000 draws per cell. Seeds: staggered [20281801 + cell, draw]; synthetic [20281851 + cell, draw].

Usage: scripts/policy_validation.py --criterion-commit SHA [--workers N] [--smoke]
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
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402

from census import policy_core as pc  # noqa: E402

SSEED, CSEED = 20281801, 20281851
N = 51
ST_CELLS = [(T, rho, eff) for T in (12, 18) for rho in (.3, .7) for eff in ("constant", "growing")]
SC_CELLS = [(T, rho, eff) for T in (12, 18) for rho in (.3, .7) for eff in ("none", "constant", "growing")]
COHORTS = {12: (5, 7, 9), 18: (7, 10, 13)}
DRAWS, CHUNK, BMULT = 1000, 50, 999
FROZEN = ["scripts/policy_validation.py", "census/policy_core.py", "docs/audits/policy_validation_criterion.md"]
OUT = ROOT/"docs/audits/policy_validation"


def effect(eff, e):
    e = np.asarray(e, float)
    if eff == "none":
        return np.zeros_like(e)
    return np.where(e >= 0, -2.0 if eff == "constant" else -1-.5*e, 0.0)


def setup(seed, T):
    rng = np.random.default_rng([seed, 999999])
    cv = np.exp(rng.uniform(np.log(.01), np.log(.08), N))
    order = rng.permutation(N)
    return rng, cv, order


def panel(rng, T, rho, cv, tau):
    a = rng.normal(10, 3, N)
    e = np.zeros((N, T)); e[:, 0] = rng.standard_normal(N)
    for t in range(1, T):
        e[:, t] = rho*e[:, t-1]+np.sqrt(1-rho**2)*rng.standard_normal(N)
    mean = a[:, None]+.1*np.arange(T)[None, :]
    se = cv[:, None]*mean
    return mean+tau+e+rng.standard_normal((N, T))*se, se, a


def st_job(args):
    cell, start, stop = args
    T, rho, eff = ST_CELLS[cell]
    _, cv, order = setup(SSEED+cell, T)
    G = np.full(N, np.inf)
    for k, g in enumerate(COHORTS[T]):
        G[order[10*k:10*(k+1)]] = g
    E = np.arange(T)[None, :]-np.where(np.isfinite(G), G, 1e9)[:, None]
    tau = effect(eff, E)
    post = [(g, t) for g in COHORTS[T] for t in range(g, T)]
    true_overall = float(np.mean([effect(eff, t-g) for g, t in post]))  # equal cohort sizes
    acc = {}
    for d in range(start, stop):
        rng = np.random.default_rng([SSEED+cell, d])
        Y, se, _ = panel(rng, T, rho, cv, tau)
        cs = pc.cs_estimate(Y, G, B=BMULT, rng=rng, se_y=se)
        sa = pc.sun_abraham(Y, G)
        band = True
        for name, res in (("S1", cs), ("S2", sa)):
            for r in res["event"]+[res["overall"]]:
                tgt = true_overall if r["key"] == "overall" else float(effect(eff, r["key"]))
                key = (name, str(r["key"]))
                acc.setdefault(key, 0); acc[key] += int(r["lower"] <= tgt <= r["upper"])
                if name == "S1":
                    k2 = ("S1r", str(r["key"])); acc.setdefault(k2, 0); acc[k2] += int(r["lower_r"] <= tgt <= r["upper_r"])
                    if r["key"] != "overall":
                        band &= r["band_lower"] <= tgt <= r["band_upper"]
        acc.setdefault(("S1band", "all"), 0); acc[("S1band", "all")] += int(band)
    return "st", cell, {"|".join(k): v for k, v in acc.items()}


def sc_job(args):
    cell, start, stop = args
    T, rho, eff = SC_CELLS[cell]
    _, cv, _ = setup(CSEED+cell, T)
    T0 = T-3
    E = np.full((N, T), -1e9); E[0] = np.arange(T)-T0
    tau = effect(eff, E)
    acc = dict(reject=0, flagged=0, **{f"c2_{t}": 0 for t in range(T0, T)}, c2_failed=0)
    for d in range(start, stop):
        rng = np.random.default_rng([CSEED+cell, d])
        Y, se, a = panel(rng, T, rho, cv, tau)
        # unit 0 at the median level
        Y[0] += 10-a[0]
        pt = pc.placebo_test(Y, 0, T0)
        acc["reject"] += int(pt["p"] <= .10)
        acc["flagged"] += int(pt["prefit_ratio"] > 2)
        gap = pt["main"]["gap"]
        sd = max(float(np.std(gap[:T0], ddof=1)), 1e-6)
        for t in range(T0, T):
            grid = np.linspace(gap[t]-6*sd, gap[t]+6*sd, 121)
            lo, hi = pc.conformal_interval(Y, 0, T0, t, grid)
            if not np.isfinite(lo):
                acc["c2_failed"] += 1; continue
            acc[f"c2_{t}"] += int(lo <= float(effect(eff, t-T0)) <= hi)
    return "sc", cell, acc


def job(a):
    return st_job(a[1:]) if a[0] == "st" else sc_job(a[1:])


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
    draws, chunk = (4, 2) if a.smoke else (DRAWS, CHUNK)
    tasks = [("st", c, s, min(s+chunk, draws)) for c in range(len(ST_CELLS)) for s in range(0, draws, chunk)]
    tasks += [("sc", c, s, min(s+chunk, draws)) for c in range(len(SC_CELLS)) for s in range(0, draws, chunk)]
    st, sc = {}, {}
    t0 = time.time()
    with ProcessPoolExecutor(a.workers) as ex:
        for kind, cell, res in ex.map(job, tasks, chunksize=1):
            acc = (st if kind == "st" else sc).setdefault(cell, {})
            for k, v in res.items():
                acc[k] = acc.get(k, 0)+v
    st_rows = []
    for c, r in sorted(st.items()):
        T, rho, eff = ST_CELLS[c]
        cov = {k: v/draws for k, v in r.items()}
        st_rows.append(dict(T=T, rho=rho, effect=eff, coverage=cov,
                            min={m: min(v for k, v in cov.items() if k.split("|")[0] == m) for m in ("S1", "S1r", "S2")},
                            band=cov["S1band|all"]))
    sc_rows = []
    for c, r in sorted(sc.items()):
        T, rho, eff = SC_CELLS[c]
        T0 = T-3
        n_ok = {t: draws-0 for t in range(T0, T)}
        sc_rows.append(dict(T=T, rho=rho, effect=eff, reject=r["reject"]/draws, flagged=r["flagged"]/draws,
                            c2={str(t-T0): r[f"c2_{t}"]/draws for t in range(T0, T)}, c2_failed=r["c2_failed"],
                            c2_min=min(r[f"c2_{t}"]/n_ok[t] for t in range(T0, T))))
    passed = dict(S1=all(r["min"]["S1"] >= .86 for r in st_rows), S1r=all(r["min"]["S1r"] >= .86 for r in st_rows),
                  S2=all(r["min"]["S2"] >= .86 for r in st_rows),
                  C1=all(r["reject"] <= .10 for r in sc_rows if r["effect"] == "none"),
                  C2=all(r["c2_min"] >= .86 for r in sc_rows))
    out = dict(staggered=st_rows, synthetic=sc_rows, passed=passed, draws=draws, criterion_commit=a.criterion_commit,
               seconds=round(time.time()-t0),
               frozen_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FROZEN})
    if a.smoke:
        print(json.dumps(passed), out["seconds"]); return
    OUT.with_suffix(".json").write_text(json.dumps(out, indent=1)+"\n")
    L = ["# Round 78: staggered-adoption DiD and synthetic control", "",
         f"Criterion commit: `{a.criterion_commit}`. {draws} draws per cell; 90% intervals. Author self-review, not "
         "independent.", "", "## Staggered adoption (lowest coverage over the overall ATT and every event time)", "",
         "| T | rho | Effect | S1 CS | S1r CS + ACS | S2 SA | S1 uniform band |", "| ---: | ---: | :--- | ---: | ---: | ---: | ---: |"]
    L += [f"| {r['T']} | {r['rho']} | {r['effect']} | {r['min']['S1']:.3f} | {r['min']['S1r']:.3f} | {r['min']['S2']:.3f} | "
          f"{r['band']:.3f} |" for r in st_rows]
    L += ["", "## Synthetic control (one treated unit, 50 donors, 3 post periods)", "",
          "| T | rho | Effect | Placebo rejection at .10 | C2 coverage by post period | Pre-fit flagged |",
          "| ---: | ---: | :--- | ---: | :--- | ---: |"]
    L += [f"| {r['T']} | {r['rho']} | {r['effect']} | {r['reject']:.3f} | "
          + ", ".join(f"{k}: {v:.3f}" for k, v in r["c2"].items())+f" | {r['flagged']:.3f} |" for r in sc_rows]
    L += ["", f"Outcomes: `{json.dumps(passed)}`.", ""]
    OUT.with_suffix(".md").write_text("\n".join(L))
    print(json.dumps(passed))


if __name__ == "__main__":
    main()
