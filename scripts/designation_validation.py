# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 85: area designations as screening tests (frozen with the criterion,
docs/audits/designation_validation_criterion.md).

Geometries (Round 80 design file docs/audits/sae_extensions_neff.csv.gz): MI tracts, NY tracts, MI+NY counties.
Truth per draw: theta_i = .3218 + .1 x_i + u_i (arcsine scale; x_i ~ N(0, 1) fixed per cell, u_i ~ N(0, .10^2)),
p_i = sin^2(clip(theta_i, 0, pi/2)); direct p_hat_i = Binomial(m_i, p_i) / m_i with m_i = max(1, round(n_eff_i)).
Thresholds t: the (1 - s) quantile of p over areas and 200 setup draws, s in {.10, .25, .50} truly qualifying.
9 cells x 1,000 draws.
Q1a (direct, flat prior) and Q1b (Fay-Herriot posterior with covariate x) probabilities of p_i >= t.
Calibration pass (per method): in every decile bin of predicted probability holding >= 200 area-draws (pooled over
the cell's draws), |realized share truly qualifying - mean predicted probability| <= .05, in every cell.
Q2 pass (per probability source Q1a / Q1b): for every rule (point, lower, prob50, prob80), |mean predicted -
mean realized| <= .05 for sensitivity, specificity, PPV and NPV (draws where defined), and the 90% predictive
interval of the realized PPV covers it in >= 86% of draws where the rule designates at least one area, in every cell.
Q3 (top-k overlap, k = the expected number qualifying) reported only.
Seeds: setup [20282501, cell]; draws [20282511 + cell, draw].

Usage: scripts/designation_validation.py --criterion-commit SHA [--workers N] [--smoke]
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
import pandas as pd  # noqa: E402

from census import designation_core as dc  # noqa: E402

SEED = 20282501
NEFF = ROOT/"docs/audits/sae_extensions_neff.csv.gz"
CELLS = [(g, s) for g in ("MI tract", "NY tract", "counties") for s in (.10, .25, .50)]
RULES = ("point", "lower", "prob50", "prob80")
DRAWS, CHUNK = 1000, 25
FROZEN = ["scripts/designation_validation.py", "census/designation_core.py", "census/sae_extensions_core.py",
          "docs/audits/sae_extensions_neff.csv.gz", "docs/audits/designation_validation_criterion.md"]
OUT = ROOT/"docs/audits/designation_validation"


def design(cell):
    g, share = CELLS[cell]
    f = pd.read_csv(NEFF, dtype={"GEOID": str, "state": str})
    n = (f[f.level == "county"] if g == "counties" else
         f[(f.level == "tract") & (f.state == {"MI": "26", "NY": "36"}[g.split()[0]])]).n_eff.to_numpy()
    rng = np.random.default_rng([SEED, cell])
    x = rng.standard_normal(len(n))
    X = np.column_stack([np.ones(len(n)), x])
    sims = np.sin(np.clip(.3218+.1*x+rng.normal(0, .10, (200, len(n))), 0, np.pi/2))**2
    t = float(np.quantile(sims, 1-share))
    return n, x, X, t


def job(args):
    cell, start, stop = args
    n, x, X, t = design(cell)
    m = np.maximum(1, np.round(n)).astype(int)
    bins = np.linspace(0, 1, 11)
    acc = {"cal": {k: np.zeros((3, 10)) for k in ("a", "b")}, "q2": {}, "q3": 0.0}
    for d in range(start, stop):
        rng = np.random.default_rng([SEED+10+cell, d])
        p = np.sin(np.clip(.3218+.1*x+rng.normal(0, .10, len(n)), 0, np.pi/2))**2
        truth = p >= t
        ph = rng.binomial(m, p)/m
        Pa = dc.q1_direct(ph, n, t)
        Pb, theta, mse = dc.q1_fh(ph, n, X, t)
        for key, P in (("a", Pa), ("b", Pb)):
            idx = np.clip(np.digitize(P, bins)-1, 0, 9)
            np.add.at(acc["cal"][key][0], idx, 1)
            np.add.at(acc["cal"][key][1], idx, truth)
            np.add.at(acc["cal"][key][2], idx, P)
            for rule in RULES:
                S = dc.designate(rule, ph, n, t, P)
                e = dc.expected_accuracy(S, P)
                tp = int((S & truth).sum()); fp = int((S & ~truth).sum()); fn = int((~S & truth).sum()); tn = int((~S & ~truth).sum())
                real = dict(sensitivity=tp/(tp+fn) if tp+fn else np.nan, specificity=tn/(tn+fp) if tn+fp else np.nan,
                            ppv=tp/(tp+fp) if tp+fp else np.nan, npv=tn/(tn+fn) if tn+fn else np.nan)
                q = acc["q2"].setdefault(f"{key}|{rule}", {m_: [0.0, 0.0, 0] for m_ in real} | {"ppv_cover": [0, 0]})
                for m_, rv in real.items():
                    if np.isfinite(rv) and np.isfinite(e[m_]):
                        q[m_][0] += e[m_]; q[m_][1] += rv; q[m_][2] += 1
                if S.any():
                    q["ppv_cover"][0] += int(e["ppv_lower"]-1e-12 <= real["ppv"] <= e["ppv_upper"]+1e-12); q["ppv_cover"][1] += 1
        k = max(1, int(round(truth.mean()*len(n))))
        if d < start+2:
            acc["q3"] += dc.top_k_overlap(theta, mse, k, draws=200, rng=rng)
    acc["q3_n"] = min(2, stop-start)
    return cell, acc


def merge(a, b):
    if a is None:
        return b
    for k in ("a", "b"):
        a["cal"][k] += b["cal"][k]
    for key, q in b["q2"].items():
        t = a["q2"].setdefault(key, q)
        if t is not q:
            for m_, v in q.items():
                t[m_] = [x+y for x, y in zip(t[m_], v)]
    a["q3"] += b["q3"]; a["q3_n"] += b["q3_n"]
    return a


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--criterion-commit"); ap.add_argument("--workers", type=int, default=9)
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
        for i, (cell, r) in enumerate(ex.map(job, tasks, chunksize=1)):
            acc[cell] = merge(acc.get(cell), r)
            if i % 50 == 0:
                print({"done": i, "of": len(tasks), "s": round(time.time()-t0)}, flush=True)
    out_rows = []
    passed = {"Q1a": True, "Q1b": True, "Q2a": True, "Q2b": True}
    for cell, r in sorted(acc.items()):
        g, share = CELLS[cell]
        row = dict(geometry=g, share=share, calibration={}, q2={}, q3=r["q3"]/max(r["q3_n"], 1))
        for key in ("a", "b"):
            cnt, hit, psum = r["cal"][key]
            bins = [dict(bin=j, n=int(cnt[j]), realized=float(hit[j]/cnt[j]), mean_predicted=float(psum[j]/cnt[j]))
                    for j in range(10) if cnt[j] >= 200]
            ok = all(abs(bn["realized"]-bn["mean_predicted"]) <= .05 for bn in bins)
            row["calibration"][key] = bins; row["calibration"][key+"_ok"] = ok
            passed["Q1"+key] &= ok
        for qk, q in r["q2"].items():
            src, rule = qk.split("|")
            res = {m_: dict(pred=v[0]/v[2], real=v[1]/v[2], n=v[2]) for m_, v in q.items() if m_ != "ppv_cover" and v[2]}
            cov = q["ppv_cover"][0]/q["ppv_cover"][1] if q["ppv_cover"][1] else None
            ok = all(abs(v["pred"]-v["real"]) <= .05 for v in res.values()) and (cov is None or cov >= .86)
            row["q2"][qk] = dict(metrics=res, ppv_interval_coverage=cov, ok=ok)
            passed["Q2"+src] &= ok
        out_rows.append(row)
    out = dict(rows=out_rows, passed=passed, draws=draws, criterion_commit=a.criterion_commit, seconds=round(time.time()-t0),
               frozen_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FROZEN})
    if a.smoke:
        print(json.dumps(passed), out["seconds"]); return
    OUT.with_suffix(".json").write_text(json.dumps(out, indent=1, default=float)+"\n")
    L = ["# Round 85: area designations as screening tests", "",
         f"Criterion commit: `{a.criterion_commit}`. {draws} draws per cell. Author self-review, not independent.", "",
         "## Calibration of the probability of truly exceeding the threshold (bins with >= 200 area-draws)", "",
         "| Geometry | Share qualifying | Q1a direct: worst |realized - predicted| | Q1b FH: worst |", "| :--- | ---: | ---: | ---: |"]
    for row in out_rows:
        w = {k: max((abs(b["realized"]-b["mean_predicted"]) for b in row["calibration"][k]), default=float("nan")) for k in ("a", "b")}
        L.append(f"| {row['geometry']} | {row['share']} | {w['a']:.3f} | {w['b']:.3f} |")
    L += ["", "## Expected accuracy of designation rules (predicted vs realized means; PPV interval coverage)", "",
          "| Geometry | Share | Source | Rule | Sn pred/real | Sp pred/real | PPV pred/real | NPV pred/real | PPV PI cover |",
          "| :--- | ---: | :--- | :--- | :--- | :--- | :--- | :--- | ---: |"]
    for row in out_rows:
        for qk, q in row["q2"].items():
            src, rule = qk.split("|")
            mm = q["metrics"]
            f = lambda k: f"{mm[k]['pred']:.3f}/{mm[k]['real']:.3f}" if k in mm else "–"  # noqa: E731
            cv = q["ppv_interval_coverage"]
            L.append(f"| {row['geometry']} | {row['share']} | Q1{src} | {rule} | {f('sensitivity')} | {f('specificity')} | "
                     f"{f('ppv')} | {f('npv')} | {'–' if cv is None else f'{cv:.3f}'} |")
    L += ["", "Q3 (expected top-k overlap, reported): "+", ".join(f"{r['geometry']} {r['share']}: {r['q3']:.3f}" for r in out_rows)+".",
          "", f"Outcomes: `{json.dumps(passed)}`.", ""]
    OUT.with_suffix(".md").write_text("\n".join(L))
    print(json.dumps(passed))


if __name__ == "__main__":
    main()
