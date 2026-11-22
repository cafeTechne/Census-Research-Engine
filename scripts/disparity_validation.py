# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 76: between-group disparity measures and Kitagawa decomposition (frozen with the criterion,
docs/audits/disparity_validation_criterion.md).

Disparity, ACS design (9 cells): G in {2, 4, 6} groups x smallest-group rate CV c in {.10, .30, .50}. True rates
R = (.10, .22, .30, .16, .35, .26)[:G], population shares P = (.60, .15, .10, .08, .04, .03)[:G] (normalised),
reference group 0. Rate CV_g = max(.05, c * sqrt(min P / P_g)) (reference .05); group population CV = CV_g / 2.
Observed values: Gaussian-copula Gamma draws (mean = truth, CV as above) with error correlation SIGMA (rates .2
across groups, populations .2, rate-population of the same group -.2). 80 replicates from make_replicates with
the same correlation and SE = true SE. Target: the measure on true rates and true shares.
Disparity, count design (9 cells): G x expected count per group E in {20, 100, 1000}; mortality-like rates
RC = (.008, .012, .015, .010, .018, .009)[:G]; populations n_g = E / RC_g (known); d_g ~ Poisson(E).
Kitagawa (6 cells): 10 age strata, areas A and B. ACS: stratum rates CV c in {.10, .30, .50} (composition
counts CV c/2, independent errors, replicate SE); counts: populations with mean expected count E in
{20, 100, 1000} per stratum, Poisson.
2,000 draws per cell. Pass per measure and design: 90% coverage >= .86 in every cell (rd/log_rr: every
non-reference contrast; Kitagawa: each of difference, rate and composition effects). Range gates (stated before
the run): a measure failing only at c = .50 is validated for c <= .30; failing only at E = 20 is validated for E >= 100.
Seeds: [20281601 + design*100 + cell, chunk].

Usage: scripts/disparity_validation.py --criterion-commit SHA [--workers N] [--smoke]
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
from scipy import stats  # noqa: E402

from census import disparity_core as dc  # noqa: E402
from census.simulation import make_replicates  # noqa: E402

SEED = 20281601
R = np.array([.10, .22, .30, .16, .35, .26]); P = np.array([.60, .15, .10, .08, .04, .03])
RC = np.array([.008, .012, .015, .010, .018, .009])
GS, CVS, ES = (2, 4, 6), (.10, .30, .50), (20, 100, 1000)
ACS_CELLS = [(G, c) for G in GS for c in CVS]
CNT_CELLS = [(G, E) for G in GS for E in ES]
S = 10
AGE = np.arange(S)
KR_A = .02*np.exp(.3*AGE); KR_B = KR_A*(1.25+.05*np.sin(AGE))
KC_A = np.exp(-.12*AGE); KC_A /= KC_A.sum(); KC_B = np.exp(-.02*AGE); KC_B /= KC_B.sum()
DRAWS, CHUNK, BOOT = 2000, 100, 500
MEASURES = dc.GROUP_MEASURES+dc.INDEX_MEASURES
KPARTS = ("difference", "rate_effect", "composition_effect")
FROZEN = ["scripts/disparity_validation.py", "census/disparity_core.py", "census/simulation.py",
          "docs/audits/disparity_validation_criterion.md"]
OUT = ROOT/"docs/audits/disparity_validation"


def sigma(G):
    C = np.full((2*G, 2*G), 0.0)
    C[:G, :G] = .2; C[G:, G:] = .2
    for g in range(G):
        C[g, G+g] = C[G+g, g] = -.2
    np.fill_diagonal(C, 1.0)
    return C


def gamma_copula(mean, cv, z):
    shape = 1/cv**2
    return stats.gamma.ppf(stats.norm.cdf(z), shape, scale=mean/shape)


def acs_truth(G, c):
    r, p = R[:G], P[:G]/P[:G].sum()
    cv = np.maximum(.05, c*np.sqrt(p.min()/p)); cv[0] = .05
    if G == 2:
        cv[1] = c
    return r, p, cv


def acs_chunk(cell, chunk, n):
    G, c = ACS_CELLS[cell]
    r, p, cv = acs_truth(G, c)
    rng = np.random.default_rng([SEED+cell, chunk])
    C = sigma(G); L = np.linalg.cholesky(C)
    z = rng.standard_normal((n, 2*G))@L.T
    pop_true = p*100000
    est_r = gamma_copula(r, cv, z[:, :G]); est_n = gamma_copula(pop_true, cv/2, z[:, G:])
    obs = np.hstack([est_r, est_n]); se = np.tile(np.hstack([r*cv, pop_true*cv/2]), (n, 1))
    reps = make_replicates(obs, se, rng, corr=C)
    res = dc.replicate_intervals(est_r, est_n, reps[:, :G, :], reps[:, G:, :], 0)
    tgt = dc.measures(r, p, 0)
    return {m: cover(res[m], tgt[m]) for m in MEASURES}


def cnt_chunk(cell, chunk, n):
    G, E = CNT_CELLS[cell]
    rng = np.random.default_rng([SEED+100+cell, chunk])
    pop = E/RC[:G]
    d = rng.poisson(E, (n, G)).astype(float)
    res = dc.poisson_intervals(d, np.tile(pop, (n, 1)), 0, B=BOOT, rng=rng)
    tgt = dc.measures(RC[:G], pop, 0)
    return {m: cover(res[m], tgt[m]) for m in MEASURES}


def kit_chunk(cell, chunk, n):
    rng = np.random.default_rng([SEED+200+cell, chunk])
    tgt = dc.kitagawa(KR_A, KC_A, KR_B, KC_B)
    if cell < 3:
        c = CVS[cell]
        ra = gamma_copula(KR_A, c, rng.standard_normal((n, S))); rb = gamma_copula(KR_B, c, rng.standard_normal((n, S)))
        na = gamma_copula(KC_A*1e5, c/2, rng.standard_normal((n, S))); nb = gamma_copula(KC_B*1e5, c/2, rng.standard_normal((n, S)))
        rep = lambda est, sd: make_replicates(est, np.tile(sd, (n, 1)), rng)  # noqa: E731
        res = dc.kitagawa_replicate(ra, na, rb, nb, rep(ra, KR_A*c), rep(na, KC_A*1e5*c/2), rep(rb, KR_B*c),
                                    rep(nb, KC_B*1e5*c/2))
    else:
        E = ES[cell-3]
        Na = S*E/(KC_A*KR_A).sum(); Nb = S*E/(KC_B*KR_B).sum()
        pa, pb = KC_A*Na, KC_B*Nb
        da = rng.poisson(pa*KR_A, (n, S)).astype(float); db = rng.poisson(pb*KR_B, (n, S)).astype(float)
        res = dc.kitagawa_poisson(da, np.tile(pa, (n, 1)), db, np.tile(pb, (n, 1)))
    return {k: cover(res[k], tgt[k]) for k in KPARTS}


def cover(iv, target):
    lo, hi = iv["lower"], iv["upper"]
    ok = (lo <= target) & (target <= hi)  # NaN intervals count as non-coverage
    ok = ok.sum(axis=0) if ok.ndim > 1 else ok.sum()
    return np.atleast_1d(ok).astype(int).tolist()


def job(args):
    design, cell, chunk, n = args
    f = dict(acs=acs_chunk, counts=cnt_chunk, kitagawa=kit_chunk)[design]
    return design, cell, f(cell, chunk, n)


def judge(cov, cells, draws, gate_value, gate_index):
    """Per measure: pass in every cell, or (range gate) fail only in cells whose gate parameter is gate_value."""
    out = {}
    for m in next(iter(cov.values())):
        rates = {c: [h/draws for h in cov[c][m]] for c in cov}
        failing = [c for c in rates if min(rates[c]) < .86]
        gated = bool(failing) and all((cells[c] if gate_index is None else cells[c][gate_index]) == gate_value for c in failing)
        out[m] = dict(coverage={str(cells[c]): rates[c] for c in rates}, passed=not failing, range_gated=gated)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--criterion-commit"); ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    if not a.smoke:
        subprocess.run(["git", "merge-base", "--is-ancestor", a.criterion_commit, "HEAD"], cwd=ROOT, check=True)
        for rel in FROZEN:
            if subprocess.check_output(["git", "show", a.criterion_commit+":"+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
                raise SystemExit("differs from criterion commit: "+rel)
    draws, chunk = (20, 10) if a.smoke else (DRAWS, CHUNK)
    tasks = [(d, c, k, chunk) for d, ncell in (("acs", 9), ("counts", 9), ("kitagawa", 6))
             for c in range(ncell) for k in range(draws//chunk)]
    cov = {"acs": {}, "counts": {}, "kitagawa": {}}
    t0 = time.time()
    with ProcessPoolExecutor(a.workers) as ex:
        for design, cell, res in ex.map(job, tasks):
            acc = cov[design].setdefault(cell, {})
            for m, hits in res.items():
                acc[m] = [x+y for x, y in zip(acc.get(m, [0]*len(hits)), hits)]
    kcells = {c: (("acs", CVS[c]) if c < 3 else ("counts", ES[c-3])) for c in range(6)}
    result = dict(
        acs=judge(cov["acs"], ACS_CELLS, draws, .50, 1),
        counts=judge(cov["counts"], CNT_CELLS, draws, 20, 1),
        kitagawa_acs=judge({c: v for c, v in cov["kitagawa"].items() if c < 3}, kcells, draws, ("acs", .50), None),
        kitagawa_counts=judge({c: v for c, v in cov["kitagawa"].items() if c >= 3}, kcells, draws, ("counts", 20), None),
        draws=draws, criterion_commit=a.criterion_commit, seconds=round(time.time()-t0),
        frozen_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FROZEN})
    if a.smoke:
        print(json.dumps({k: {m: (v["passed"], v["range_gated"]) for m, v in result[k].items()}
                          for k in ("acs", "counts", "kitagawa_acs", "kitagawa_counts")}), result["seconds"]); return
    OUT.with_suffix(".json").write_text(json.dumps(result, indent=1)+"\n")
    write_md(result)
    print(json.dumps({k: {m: (v["passed"], v["range_gated"]) for m, v in result[k].items()}
                      for k in ("acs", "counts", "kitagawa_acs", "kitagawa_counts")}))


def outcome(v):
    return "pass" if v["passed"] else ("pass with range gate" if v["range_gated"] else "fail")


def write_md(r):
    L = ["# Round 76: between-group disparity measures and Kitagawa decomposition", "",
         f"Criterion commit: `{r['criterion_commit']}`. {r['draws']} draws per cell; 90% intervals; pass = coverage "
         ">= .86 in every cell (lowest contrast for rd/log_rr). Author self-review, not independent.", ""]
    for key, title in (("acs", "ACS replicate design (G groups, smallest-group CV)"),
                       ("counts", "Count design (G groups, expected count per group)"),
                       ("kitagawa_acs", "Kitagawa, ACS replicates (stratum-rate CV)"),
                       ("kitagawa_counts", "Kitagawa, Poisson counts (expected count per stratum)")):
        block = r[key]
        cells = list(next(iter(block.values()))["coverage"])
        L += [f"## {title}", "", "| Measure | "+" | ".join(cells)+" | Outcome |", "| :--- |"+" ---: |"*len(cells)+" :--- |"]
        for m, v in block.items():
            L.append(f"| {m} | "+" | ".join(f"{min(v['coverage'][c]):.3f}" for c in cells)+f" | {outcome(v)} |")
        L.append("")
    OUT.with_suffix(".md").write_text("\n".join(L))


if __name__ == "__main__":
    main()
