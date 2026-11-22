# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 86: probabilistic misclassification bias analysis (frozen with the criterion,
docs/audits/bias_analysis_validation_criterion.md). E-values are deterministic and checked in tests against
VanderWeele and Ding (2017).

Truth: two groups of 2,000 (exposed, unexposed) per draw, unexposed risk .10, true RR in {1.0, 2.0}.
Misclassification kinds:
- outcome_nd: cases recorded with Se .85, Sp .95 in both groups;
- outcome_diff: exposed Se .90 / Sp .97, unexposed Se .80 / Sp .93;
- exposure_nd: exposure recorded with Se .85, Sp .95 regardless of outcome (exposed share of persons .5).
Priors (beta, mean and sd): "correct" centred on the true values with sd .02; "offset" with every Se mean lowered by
.05 and every Sp mean lowered by .02 (sd .02). Probabilistic analysis with 5,000 simulations per draw;
90% total-error interval. 12 cells (kind x RR x prior) x 1,000 draws.
Pass (P1): coverage of the true RR and of the true OR >= .86 in every correct-prior cell. Offset-prior coverage and
the conventional uncorrected interval's coverage are reported.
Seeds: [20282601 + cell, draw].

Usage: scripts/bias_analysis_validation.py --criterion-commit SHA [--workers N] [--smoke]
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

from census import bias_analysis_core as ba  # noqa: E402

SEED = 20282601
KINDS = ("outcome_nd", "outcome_diff", "exposure_nd")
CELLS = [(k, rr, pr) for k in KINDS for rr in (1.0, 2.0) for pr in ("correct", "offset")]
TRUE = {"outcome_nd": ((.85, .85), (.95, .95)), "outcome_diff": ((.90, .80), (.97, .93)),
        "exposure_nd": ((.85, .85), (.95, .95))}
DRAWS, CHUNK, SIMS, N, P0 = 1000, 50, 5000, 2000, .10
FROZEN = ["scripts/bias_analysis_validation.py", "census/bias_analysis_core.py",
          "docs/audits/bias_analysis_validation_criterion.md"]
OUT = ROOT/"docs/audits/bias_analysis_validation"


def observe(rng, kind, rr):
    p1 = rr*P0
    se, sp = TRUE[kind]
    if kind.startswith("outcome"):
        a_t = rng.binomial(N, p1); c_t = rng.binomial(N, P0)
        a = rng.binomial(a_t, se[0])+rng.binomial(N-a_t, 1-sp[0])
        c = rng.binomial(c_t, se[1])+rng.binomial(N-c_t, 1-sp[1])
        return a, N-a, c, N-c
    a_t = rng.binomial(N, p1); c_t = rng.binomial(N, P0)     # true cases among exposed / unexposed
    cases_e, noncases_e = a_t, N-a_t
    cases_u, noncases_u = c_t, N-c_t
    a = rng.binomial(cases_e, se[0])+rng.binomial(cases_u, 1-sp[0])        # recorded exposed among cases
    b = rng.binomial(noncases_e, se[1])+rng.binomial(noncases_u, 1-sp[1])  # recorded exposed among non-cases
    return a, b, (cases_e+cases_u)-a, (noncases_e+noncases_u)-b


def job(args):
    cell, start, stop = args
    kind, rr, prior = CELLS[cell]
    se, sp = TRUE[kind]
    shift_se, shift_sp = (0, 0) if prior == "correct" else (-.05, -.02)
    diff = kind == "outcome_diff"
    se_prior = tuple((s+shift_se, .02) for s in se) if diff else (se[0]+shift_se, .02)
    sp_prior = tuple((s+shift_sp, .02) for s in sp) if diff else (sp[0]+shift_sp, .02)
    true_or = (rr*P0/(1-rr*P0))/(P0/(1-P0))
    acc = dict(rr=0, or_=0, naive_rr=0, discarded=0.0)
    z = stats.norm.ppf(.95)
    for d in range(start, stop):
        rng = np.random.default_rng([SEED+cell, d])
        a, b, c, dd = observe(rng, kind, rr)
        r = ba.probabilistic(a, b, c, dd, se_prior, sp_prior, kind="outcome" if kind.startswith("outcome") else "exposure",
                             draws=SIMS, rng=rng, differential=diff)
        acc["rr"] += int(r["rr"]["lower"] <= rr <= r["rr"]["upper"])
        acc["or_"] += int(r["or"]["lower"] <= true_or <= r["or"]["upper"])
        acc["discarded"] += r["discarded"]
        lrr = np.log((a/(a+b))/(c/(c+dd))); se_l = np.sqrt(1/a-1/(a+b)+1/c-1/(c+dd))
        acc["naive_rr"] += int(np.exp(lrr-z*se_l) <= rr <= np.exp(lrr+z*se_l))
    return cell, acc


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
    draws, ch = (4, 2) if a.smoke else (DRAWS, CHUNK)
    tasks = [(c, s, min(s+ch, draws)) for c in range(len(CELLS)) for s in range(0, draws, ch)]
    acc = {}
    t0 = time.time()
    with ProcessPoolExecutor(a.workers) as ex:
        for cell, r in ex.map(job, tasks, chunksize=1):
            dd = acc.setdefault(cell, {})
            for k, v in r.items():
                dd[k] = dd.get(k, 0)+v
    rows = [dict(kind=CELLS[c][0], rr=CELLS[c][1], prior=CELLS[c][2], rr_cov=r["rr"]/draws, or_cov=r["or_"]/draws,
                 naive_rr_cov=r["naive_rr"]/draws, discarded=r["discarded"]/draws) for c, r in sorted(acc.items())]
    passed = dict(P1=all(r["rr_cov"] >= .86 and r["or_cov"] >= .86 for r in rows if r["prior"] == "correct"))
    out = dict(rows=rows, passed=passed, draws=draws, simulations=SIMS, criterion_commit=a.criterion_commit,
               seconds=round(time.time()-t0), frozen_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FROZEN})
    if a.smoke:
        print(json.dumps(passed), out["seconds"]); return
    OUT.with_suffix(".json").write_text(json.dumps(out, indent=1)+"\n")
    L = ["# Round 86: probabilistic misclassification bias analysis", "",
         f"Criterion commit: `{a.criterion_commit}`. {draws} draws per cell, {SIMS} simulations each; 90% total-error "
         "intervals. Author self-review, not independent.", "",
         "| Kind | True RR | Prior | RR coverage | OR coverage | Uncorrected RR coverage | Discarded simulations |",
         "| :--- | ---: | :--- | ---: | ---: | ---: | ---: |"]
    L += [f"| {r['kind']} | {r['rr']} | {r['prior']} | {r['rr_cov']:.3f} | {r['or_cov']:.3f} | {r['naive_rr_cov']:.3f} | "
          f"{r['discarded']:.3f} |" for r in rows]
    L += ["", f"Outcomes: `{json.dumps(passed)}` (offset-prior cells reported only).", ""]
    OUT.with_suffix(".md").write_text("\n".join(L))
    print(json.dumps(passed))


if __name__ == "__main__":
    main()
