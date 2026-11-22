# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 74: rerun the published replications (docs/replications/*.json) through the engine and compare each with
its original Round 66-69 audit at the tolerance fixed in PLAN_ROUND_74. Writes docs/audits/replication_suite.md and
.json. Missing inputs (the owner's WONDER exports for monnat_d) are reported as skipped; WONDER is never fetched.

Usage: scripts/run_replications.py [--only ID] [--out PATH_WITHOUT_SUFFIX]
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from census import replications as rep  # noqa: E402

OUT = ROOT/"docs/audits/replication_suite"


def _line(r):
    if r["status"] == "skipped":
        return f"| `{r['id']}` | skipped | — | {r['reason']} |"
    tol = r["tolerance"]
    extra = "" if r["status"] == "agrees" else "; beyond: " + ", ".join(
        f"{k} {v:+.4g}" for k, v in list(r.get("beyond_tolerance", {}).items())[:4])
    if r.get("n_missing"):
        extra += f"; {r['n_missing']} key(s) on one side only"
    return (f"| `{r['id']}` | {r['status']} | {r['max_abs_difference']:.3g} over {r['compared']} (tolerance "
            f"{tol['value']:g}) | {tol['text']}{extra} |")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", choices=rep.IDS); ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    ids = [a.only] if a.only else list(rep.IDS)
    results = []
    for rid in ids:
        t0 = time.time()
        r = rep.run(rid)
        r["seconds"] = round(time.time()-t0)
        results.append(r)
        print(rid, r["status"], r.get("max_abs_difference", r.get("reason")), flush=True)
    out = Path(a.out)
    out.with_suffix(".json").write_text(json.dumps(results, indent=1, default=float)+"\n")
    L = ["# Replication suite (Round 74)", "",
         "Replication reruns, not new registered studies: the registered results stay those of Rounds 66-69. Each "
         "row reruns one published replication through the engine's own routes and compares it with the original "
         "audit (`docs/replications/<id>.json` gives the route, rule and tolerance).", "",
         "| Replication | Status | Max \\|difference\\| | Tolerance |", "| :--- | :--- | :--- | :--- |"]
    L += [_line(r) for r in results]
    for r in results:
        if r["id"] == "nc_ice" and r["status"] != "skipped":
            L += ["", "Replication C with the Round 71 tract interval (descriptive):", "",
                  "| ICE | OLS slope | SCPC 90% CI | Validated |", "| :--- | ---: | :--- | :--- |"]
            for var, s in r["slopes"].items():
                sc = s["scpc"]
                ci = f"{sc['lower']:.4f} to {sc['upper']:.4f}" if sc.get("lower") is not None else "—"
                L.append(f"| {var} | {s['ols']:.4f} | {ci} (rho_bar {sc.get('rho_bar')}) | {sc.get('validated')} |")
    L.append("")
    out.with_suffix(".md").write_text("\n".join(L))
    print(json.dumps({r["id"]: r["status"] for r in results}))


if __name__ == "__main__":
    main()
