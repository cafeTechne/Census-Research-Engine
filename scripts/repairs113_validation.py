#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 113 validation harness: M3c (three-level variance-share logit jackknife gated at G_top >= 49).
Parallelized across the 4 (G_top, split) cells with independent deterministic seeds."""
from concurrent.futures import ProcessPoolExecutor
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from census import multilevel3_core as m3c

SEED = 20293113
LEVEL = 0.90


def _run_cell(args):
    cell_idx, G_top, sname, sb, sm, st, R = args
    rng = np.random.default_rng(SEED + cell_idx * 1000)
    n_mid, n_bot = 5, 6
    top_id = np.repeat(np.arange(G_top), n_mid * n_bot)
    mid_id = np.repeat(np.arange(G_top * n_mid), n_bot)
    N = len(top_id)
    top_s = top_id.astype(str)
    mid_s = mid_id.astype(str)
    truth = {"bottom": sb, "mid": sm, "top": st}
    cov = {"bottom": [], "mid": [], "top": []}
    for _ in range(R):
        u_top = rng.normal(0.0, np.sqrt(st), G_top)[top_id]
        u_mid = rng.normal(0.0, np.sqrt(sm), G_top * n_mid)[mid_id]
        eps = rng.normal(0.0, np.sqrt(sb), N)
        x = rng.normal(0.0, 1.0, N)
        y = 2.0 + 0.5 * x + u_top + u_mid + eps
        df = pd.DataFrame({"y": y, "x": x, "top": top_s, "mid": mid_s})
        jk = m3c.jackknife_shares(df, "y ~ x", "top", "mid", level=LEVEL)
        for k in ("bottom", "mid", "top"):
            cov[k].append(jk[k]["lower"] <= truth[k] <= jk[k]["upper"])
    return [dict(G_top=G_top, split=sname, share=k, coverage=float(np.mean(cov[k]))) for k in ("bottom", "mid", "top")]


def main():
    t0 = time.time()
    R = 200
    splits = [
        ("70_15_15", 0.70, 0.15, 0.15),
        ("50_25_25", 0.50, 0.25, 0.25),
    ]
    tasks = []
    idx = 0
    for G_top in (49, 51):
        for sname, sb, sm, st in splits:
            idx += 1
            tasks.append((idx, G_top, sname, sb, sm, st, R))

    workers = min(len(tasks), os.cpu_count() or 1)
    print(f"Running M3c across {len(tasks)} cells ({workers} workers, R={R})...", flush=True)
    rows = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for cell_rows in ex.map(_run_cell, tasks):
            rows.extend(cell_rows)
    elapsed = time.time() - t0
    passed = all(r["coverage"] >= 0.86 for r in rows)

    summary = {
        "elapsed_seconds": round(elapsed, 2),
        "seed": SEED,
        "verdicts": {"M3c": passed},
        "M3c": rows,
    }
    os.makedirs("docs/audits", exist_ok=True)
    with open("docs/audits/repairs113_validation.json", "w") as f:
        json.dump(summary, f, indent=2)

    lines = [
        "# Round 113 Validation Report — Domain-Gated Three-Level Variance Shares (`G_top ≥ 49`)",
        "",
        f"Runtime: {elapsed:.1f}s (`scripts/repairs113_validation.py`, seed `{SEED}`).",
        "",
        "## Verdict",
        "",
        f"- **M3c** (`G_top ≥ 49`, 12 share-cells): **{'PASS' if passed else 'FAIL'}** "
        f"(min coverage {min(r['coverage'] for r in rows):.3f}, max {max(r['coverage'] for r in rows):.3f})",
        "",
        "| G_top | split | share | coverage |",
        "| ---: | :--- | :--- | ---: |",
        *[f"| {r['G_top']} | {r['split']} | {r['share']} | {r['coverage']:.3f} |" for r in rows],
        "",
    ]
    with open("docs/audits/repairs113_validation.md", "w") as f:
        f.write("\n".join(lines))
    print(json.dumps(summary["verdicts"], indent=2))
    print(f"Done in {elapsed:.1f}s.")


if __name__ == "__main__":
    main()
