# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fixed Round 34 validation of rank intervals and many-versus-reference comparisons.

    --smoke-draws N         1..20 draws per cell; no files
    --criterion-commit SHA  the full run (2,000 draws per cell)
"""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from multiprocessing import Pool
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from scipy import stats
from census import ranking_core as rc

SEED = 20270107
DRAWS = 2000
CELLS = [(K, snr, ties) for K in (40, 145) for snr in (.5, 2.) for ties in (False, True)]
FROZEN = ('scripts/ranking_validation.py', 'census/ranking_core.py', 'docs/audits/ranking_validation_criterion.md')


def setup(cell):
    K, snr, ties = CELLS[cell]
    rng = np.random.default_rng(SEED+cell)
    s = rng.lognormal(0, .6, K)
    w = rng.lognormal(0, 1, K); w /= w.sum()
    group = np.arange(K)
    if ties:
        half = K//2
        group[:half] = np.arange(half)//5
        group[half:] = 10000+np.arange(K-half)
    return rng, s, w, group, snr*np.median(s)


def true_values(rng, group, tau):
    labels, inverse = np.unique(group, return_inverse=True)
    return rng.normal(0, tau, len(labels))[inverse]


def covered(lo, hi, truth):
    """Interval covers any rank occupied by the area's tie group (rank 1 = highest)."""
    order = stats.rankdata(-truth, method="min")         # best rank of the tie group
    worst = stats.rankdata(-truth, method="max")
    return (lo <= worst) & (hi >= order)


def run_cell(args):
    cell, draws = args
    K, snr, ties = CELLS[cell]
    rng, s, w, group, tau = setup(cell)
    per_area = {k: np.zeros(K) for k in ('R1', 'R2', 'R3')}
    joint = {k: 0 for k in ('R1', 'R2', 'R3')}
    v = dict(V1_fwer=0, V2_fwer=0, V2_joint=0)
    cov = rc.reference_covariance(s, w)
    start = time.time()
    for draw in range(draws):
        truth = true_values(rng, group, tau)
        x = truth+rng.standard_normal(K)*s
        boot = np.random.default_rng(np.random.SeedSequence([SEED, cell, draw, 3]))
        for key, (lo, hi) in (('R1', rc.rank_intervals(x, s)), ('R2', rc.rank_intervals(x, s, joint=True)),
                              ('R3', rc.bootstrap_rank_intervals(x, s, boot))):
            c = covered(lo, hi, truth)
            per_area[key] += c; joint[key] += c.all()
        # Global null: every area equals the state value.
        x0 = rng.standard_normal(K)*s
        out = rc.versus_reference(x0-w@x0, cov)
        v['V1_fwer'] += (out['p_holm'] < .10).any()
        v['V2_fwer'] += (out['p_simultaneous'] < .10).any()
        alt = rc.versus_reference(x-w@x, cov)
        target = truth-w@truth
        v['V2_joint'] += ((alt['lower'] <= target) & (target <= alt['upper'])).all()
    row = dict(cell=cell, K=K, snr=snr, ties=ties, draws=draws,
               mean_area_coverage={k: float(a.mean()/draws) for k, a in per_area.items()},
               min_area_coverage={k: float(a.min()/draws) for k, a in per_area.items()},
               joint_coverage={k: c/draws for k, c in joint.items()},
               reference={k: c/draws for k, c in v.items()}, seconds=time.time()-start)
    print(f"cell {cell} K={K} snr={snr} ties={ties} mean={row['mean_area_coverage']} min={row['min_area_coverage']} "
          f"joint={row['joint_coverage']} ref={row['reference']} {row['seconds']:.0f}s", flush=True)
    return row


def run(draws, workers):
    with Pool(workers) as pool:
        rows = pool.map(run_cell, [(c, draws) for c in range(len(CELLS))])
    passed = dict(R1=all(r['mean_area_coverage']['R1'] >= .86 and r['min_area_coverage']['R1'] >= .80 for r in rows),
                  R2=all(r['joint_coverage']['R2'] >= .86 for r in rows),
                  R3=all(r['mean_area_coverage']['R3'] >= .86 and r['min_area_coverage']['R3'] >= .80 for r in rows),
                  V1=all(r['reference']['V1_fwer'] <= .13 for r in rows),
                  V2=all(r['reference']['V2_fwer'] <= .13 and r['reference']['V2_joint'] >= .86 for r in rows))
    return dict(rows=rows, passed=passed, draws_per_cell=draws,
                criterion='R1: mean per-area coverage >= .86 and every area >= .80; R2: joint coverage >= .86; '
                          'R3 judged like R1 (comparison); V1/V2: familywise error <= .13 under the global null; '
                          'V2: joint coverage >= .86 under the alternative')


def validate_pins(commit):
    subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'], cwd=ROOT, check=True)
    for rel in FROZEN:
        if subprocess.check_output(['git', 'show', commit+':'+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
            raise ValueError('script/design differs from criterion commit: '+rel)


def write_audit(result, commit):
    out = ROOT/'docs/audits/ranking_validation'
    result['criterion_commit'] = commit
    result['frozen_sha256'] = {rel: hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() for rel in FROZEN}
    out.with_suffix('.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    lines = ['# Rank intervals and comparisons with a reference: validation (Round 34)', '', result['criterion']+'.', '',
             f"Criterion commit: `{commit}`. {result['draws_per_cell']:,} draws per cell.", '',
             '| K | SNR | ties | R1 mean / min | R2 joint | R3 mean / min | R1 joint | V1 FWER | V2 FWER | V2 joint |',
             '| ---: | ---: | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for r in result['rows']:
        m, n, j, v = r['mean_area_coverage'], r['min_area_coverage'], r['joint_coverage'], r['reference']
        lines.append(f"| {r['K']} | {r['snr']} | {r['ties']} | {m['R1']:.4f} / {n['R1']:.4f} | {j['R2']:.4f} | "
                     f"{m['R3']:.4f} / {n['R3']:.4f} | {j['R1']:.4f} | {v['V1_fwer']:.4f} | {v['V2_fwer']:.4f} | {v['V2_joint']:.4f} |")
    lines += ['', 'Outcomes: `'+json.dumps(result['passed'], sort_keys=True)+'`.']
    out.with_suffix('.md').write_text('\n'.join(lines)+'\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--smoke-draws', type=int); p.add_argument('--criterion-commit'); p.add_argument('--workers', type=int, default=8)
    a = p.parse_args()
    with patch('requests.sessions.Session.request', side_effect=RuntimeError('Round 34: HTTP blocked')):
        if a.smoke_draws is not None:
            if not 1 <= a.smoke_draws <= 20:
                p.error('smoke draws must be 1..20')
            run(a.smoke_draws, a.workers); return
        if not a.criterion_commit:
            p.error('full run requires --criterion-commit')
        validate_pins(a.criterion_commit)
        if (ROOT/'docs/audits/ranking_validation.json').exists():
            p.error('refusing to overwrite the full audit')
        write_audit(run(DRAWS, a.workers), a.criterion_commit)


if __name__ == '__main__':
    main()
