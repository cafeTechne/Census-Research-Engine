# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fixed Round 36 validation of index-score and Cronbach's alpha intervals.

    --prepare-targets       population alpha per cell (400,000-area reference; once, before freezing)
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
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'scripts'))
import numpy as np
from census import index_core as ic
from census.simulation import make_replicates
from spatial_hac_validation import simulation_setup, haversine_matrix

SEED = 20270121
DRAWS = 2000
CELLS = [(rel, dist, method) for rel in (.9, .7) for dist in (0, 100) for method in ('pca', 'equal')]
LAMBDA = np.array([.8, .7, .6, .7, .5])
TARGETS = 'docs/audits/index_targets.json'
GEOMETRY = 'docs/audits/im_acs_beta_star.json'
FROZEN = ('scripts/index_validation.py', 'census/index_core.py', 'census/simulation.py', 'scripts/spatial_hac_validation.py',
          'docs/audits/index_validation_criterion.md', TARGETS, GEOMETRY)
CORR = np.full((5, 5), .2)+.8*np.eye(5)


def setup(cell):
    rel, dist, method = CELLS[cell]
    g = json.loads((ROOT/GEOMETRY).read_text())['coordinates']
    rng, L, _ = simulation_setup('linear', dist, haversine_matrix(np.asarray(g['lon']), np.asarray(g['lat'])), SEED+cell)
    n = len(L)
    se = rng.lognormal(0, .5, (n, 5)); se *= np.sqrt(((1-rel)/rel)/np.mean(se**2, axis=0))
    return rng, L, se


def true_ind(rng, L, n):
    f = L@rng.standard_normal(n) if L is not None else rng.standard_normal(n)
    eps = np.column_stack([(L@rng.standard_normal(n)) if L is not None else rng.standard_normal(n) for _ in range(5)])
    return f[:, None]*LAMBDA+eps*np.sqrt(1-LAMBDA**2)


def prepare_targets():
    path = ROOT/TARGETS
    if path.exists():
        raise ValueError('refusing to replace committed targets')
    rows = []
    for cell, (rel, dist, method) in enumerate(CELLS):
        _, _, se = setup(cell)
        rng = np.random.default_rng(np.random.SeedSequence([SEED, cell, 400000]))
        n = 400000
        t = true_ind(rng, None, n)
        idx = rng.integers(0, len(se), n)
        obs = t+rng.standard_normal((n, 5))@np.linalg.cholesky(CORR).T*se[idx]
        m, s = ic.standardize(obs)
        rows.append(dict(cell=cell, alpha_observed=ic.cronbach((obs-m)/s)))
    path.write_text(json.dumps(dict(seed=SEED, reference_areas=400000, rows=rows), indent=2)+'\n')
    print(rows)


def run_cell(args):
    cell, draws = args
    rel, dist, method = CELLS[cell]
    alpha_t = json.loads((ROOT/TARGETS).read_text())['rows'][cell]['alpha_observed']
    rng, L, se = setup(cell)
    n = len(L)
    per_area = np.zeros(n); a1 = a2 = 0; fails = 0
    start = time.time()
    for draw in range(draws):
        t = true_ind(rng, L, n)
        obs = t+rng.standard_normal((n, 5))@np.linalg.cholesky(CORR).T*se
        aux = np.random.default_rng(np.random.SeedSequence([SEED, cell, draw, 7]))
        reps = make_replicates(obs, se, aux, corr=CORR)
        try:
            m, s = ic.standardize(obs)
            l, _ = ic.loadings((obs-m)/s, method)
            sc, sd, lo, hi = ic.score_intervals(obs, reps, m, s, l)
            target = ic.scores(t, m, s, l)
            per_area += (lo <= target) & (target <= hi)
            z = (obs-m)/s
            r1 = ic.alpha_interval(z); r2 = ic.alpha_interval(z, reps=reps, m=m, s=s)
            a1 += r1['lower'] <= alpha_t <= r1['upper']; a2 += r2['lower'] <= alpha_t <= r2['upper']
        except (ValueError, np.linalg.LinAlgError):
            fails += 1
    row = dict(cell=cell, reliability=rel, range_km=dist, method=method, draws=draws,
               score_mean_coverage=float(per_area.mean()/draws), score_min_coverage=float(per_area.min()/draws),
               alpha_coverage={'A1': a1/draws, 'A2': a2/draws}, alpha_target=alpha_t, failures=fails,
               seconds=time.time()-start)
    print(f"cell {cell} rel={rel} dist={dist} {method} S1 mean={row['score_mean_coverage']:.3f} "
          f"min={row['score_min_coverage']:.3f} A={row['alpha_coverage']} {row['seconds']:.0f}s", flush=True)
    return row


def run(draws, workers):
    with Pool(workers) as pool:
        rows = pool.map(run_cell, [(c, draws) for c in range(len(CELLS))])
    passed = {f'S1/{m}': all(r['score_mean_coverage'] >= .86 and r['score_min_coverage'] >= .80 for r in rows if r['method'] == m)
              for m in ('pca', 'equal')}
    indep = [r for r in rows if r['range_km'] == 0]
    passed.update({k: all(r['alpha_coverage'][k] >= .86 for r in indep) for k in ('A1', 'A2')})
    return dict(rows=rows, passed=passed, draws_per_cell=draws,
                criterion='S1: mean per-area 90% coverage >= .86 and every area >= .80, per weighting (all cells); '
                          'A1/A2: 90% coverage of the population alpha >= .86 in every independent cell; failures count as non-coverage')


def validate_pins(commit):
    subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'], cwd=ROOT, check=True)
    for rel in FROZEN:
        if subprocess.check_output(['git', 'show', commit+':'+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
            raise ValueError('script/design differs from criterion commit: '+rel)


def write_audit(result, commit):
    out = ROOT/'docs/audits/index_validation'
    result['criterion_commit'] = commit
    result['frozen_sha256'] = {rel: hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() for rel in FROZEN}
    out.with_suffix('.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    lines = ['# Composite index scores and Cronbach alpha: validation (Round 36)', '', result['criterion']+'.', '',
             f"Criterion commit: `{commit}`. {result['draws_per_cell']:,} draws per cell.", '',
             '| Reliability | Range km | Weights | S1 mean | S1 min area | A1 Feldt | A2 + replicates | population α |',
             '| ---: | ---: | :--- | ---: | ---: | ---: | ---: | ---: |']
    for r in result['rows']:
        lines.append(f"| {r['reliability']} | {r['range_km']} | {r['method']} | {r['score_mean_coverage']:.4f} | "
                     f"{r['score_min_coverage']:.4f} | {r['alpha_coverage']['A1']:.4f} | {r['alpha_coverage']['A2']:.4f} | {r['alpha_target']:.3f} |")
    lines += ['', 'Outcomes: `'+json.dumps(result['passed'], sort_keys=True)+'`.']
    out.with_suffix('.md').write_text('\n'.join(lines)+'\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepare-targets', action='store_true'); p.add_argument('--smoke-draws', type=int)
    p.add_argument('--criterion-commit'); p.add_argument('--workers', type=int, default=8)
    a = p.parse_args()
    with patch('requests.sessions.Session.request', side_effect=RuntimeError('Round 36: HTTP blocked')):
        if a.prepare_targets:
            prepare_targets(); return
        if a.smoke_draws is not None:
            if not 1 <= a.smoke_draws <= 20:
                p.error('smoke draws must be 1..20')
            run(a.smoke_draws, a.workers); return
        if not a.criterion_commit:
            p.error('full run requires --criterion-commit')
        validate_pins(a.criterion_commit)
        if (ROOT/'docs/audits/index_validation.json').exists():
            p.error('refusing to overwrite the full audit')
        write_audit(run(DRAWS, a.workers), a.criterion_commit)


if __name__ == '__main__':
    main()
