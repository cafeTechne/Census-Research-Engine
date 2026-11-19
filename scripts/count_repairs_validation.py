# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fixed Round 45 validation: censored NB2 (K1), IM-8 count slopes (K2), noisy exposure offsets (K3).

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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'scripts'))
import numpy as np
from census import count_repairs_core as cr
from census import mci_core as mi
from spatial_hac_validation import simulation_setup, haversine_matrix

SEED = 20270320
DRAWS = 2000
N = 145
BETA = .3
GEOMETRY = 'docs/audits/im_acs_beta_star.json'
CELLS = ([('K1', dict(median=m, shape=s)) for m in (10, 30) for s in (4., 1.5)]
         + [('K2', dict(median=m, range_km=d)) for m in (10, 30) for d in (0, 100)]
         + [('K3', dict(c=c)) for c in (.05, .15)])
FROZEN = ('scripts/count_repairs_validation.py', 'census/count_repairs_core.py', 'census/mci_core.py',
          'scripts/spatial_hac_validation.py', 'docs/audits/count_repairs_validation_criterion.md', GEOMETRY)


def geometry():
    g = json.loads((ROOT/GEOMETRY).read_text())
    c = g['coordinates']; ids = c['GEOID']
    return (np.asarray(c['lon']), np.asarray(c['lat']), np.array([g['assignment'][i] for i in ids]),
            np.array([float(i.startswith('36')) for i in ids]))


def run_cell(args):
    cell, draws = args
    kind, par = CELLS[cell]
    cov, fails = {}, {}
    def judge(key, fn):
        try:
            r = fn()
            cov[key] = cov.get(key, 0)+(r['lower'] <= BETA <= r['upper'])
        except (ValueError, np.linalg.LinAlgError, FloatingPointError, RuntimeError):
            fails[key] = fails.get(key, 0)+1
    start = time.time()
    if kind == 'K2':
        lon, lat, labels, state = geometry()
        rng, L, _ = simulation_setup('linear', par['range_km'], haversine_matrix(lon, lat), SEED+cell)
    else:
        rng = np.random.default_rng(SEED+cell); L = None
    E = np.maximum(1, np.rint(rng.lognormal(np.log(par.get('median', 30)), 1, N)))
    for draw in range(draws):
        if kind == 'K1':
            x = rng.standard_normal(N)
            lam = E*np.exp(BETA*x)*rng.gamma(par['shape'], 1/par['shape'], N)
            y = rng.poisson(lam).astype(float); cens = (y >= 1) & (y <= 9)
            X = np.column_stack((np.ones(N), x))
            judge('K1a', lambda: cr.censored_negbin(y, X, E, cens))
            judge('K1b', lambda: mi.censored_poisson(y, X, E, cens))
            judge('K1c', lambda: cr.negbin_hc3(y[~cens], X[~cens], E[~cens]))
        elif kind == 'K2':
            x = L@rng.standard_normal(N); u = .3*(L@rng.standard_normal(N))
            lam = E*np.exp(BETA*x+.2*state+u)*rng.gamma(4., .25, N)
            y = rng.poisson(lam).astype(float)
            X = np.column_stack((np.ones(N), x, state))
            judge('K2a', lambda: cr.im_counts(y, X, E, labels, 'negbin'))
            judge('K2b', lambda: cr.im_counts(y, X, E, labels, 'poisson'))
            judge('K2c', lambda: cr.negbin_hc3(y, X, E))
        else:
            x = rng.standard_normal(N)
            Eo = E*np.exp(par['c']*rng.standard_normal(N)/np.sqrt(E/30))
            y = rng.poisson(E*np.exp(BETA*x)*rng.gamma(4., .25, N)).astype(float)
            X = np.column_stack((np.ones(N), x))
            judge('K3a', lambda: cr.negbin_hc3(y, X, Eo))
            judge('K3b', lambda: cr.poisson_hc3(y, X, Eo))
    keys = {'K1': ('K1a', 'K1b', 'K1c'), 'K2': ('K2a', 'K2b', 'K2c'), 'K3': ('K3a', 'K3b')}[kind]
    row = dict(cell=cell, kind=kind, parameters=par, draws=draws, coverage={k: cov.get(k, 0)/draws for k in keys},
               failed={k: fails.get(k, 0) for k in keys}, seconds=time.time()-start)
    print(row, flush=True)
    return row


def run(draws, workers):
    with Pool(workers) as pool:
        rows = pool.map(run_cell, [(c, draws) for c in range(len(CELLS))])
    passed = {}
    for key in ('K1a', 'K2a', 'K2b', 'K3a'):
        sel = [r for r in rows if key in r['coverage']]
        passed[key] = all(r['coverage'][key] >= .86 for r in sel)
    return dict(rows=rows, passed=passed, draws_per_cell=draws,
                criterion='90% coverage of the true slope 0.3 >= .86 in every cell of the problem, per procedure; '
                          'failed fits count as non-coverage; K1b, K1c, K2c, K3b are comparisons')


def validate_pins(commit):
    subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'], cwd=ROOT, check=True)
    for rel in FROZEN:
        if subprocess.check_output(['git', 'show', commit+':'+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
            raise ValueError('script/design differs from criterion commit: '+rel)


def write_audit(result, commit):
    out = ROOT/'docs/audits/count_repairs_validation'
    result['criterion_commit'] = commit
    result['frozen_sha256'] = {rel: hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() for rel in FROZEN}
    out.with_suffix('.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    lines = ['# Count-model repairs: validation (Round 45)', '', result['criterion']+'.', '',
             f"Criterion commit: `{commit}`. {result['draws_per_cell']:,} draws per cell; 145 areas.", '',
             '| Problem | Setting | Coverage | Failed fits |', '| :--- | :--- | :--- | :--- |']
    for r in result['rows']:
        lines.append(f"| {r['kind']} | {', '.join(f'{k} {v}' for k, v in r['parameters'].items())} | "
                     + ', '.join(f"{k} {v:.4f}" for k, v in r['coverage'].items()) + ' | '
                     + ', '.join(f"{k} {v}" for k, v in r['failed'].items()) + ' |')
    lines += ['', 'Outcomes: `'+json.dumps(result['passed'], sort_keys=True)+'`.']
    out.with_suffix('.md').write_text('\n'.join(lines)+'\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--smoke-draws', type=int); p.add_argument('--criterion-commit'); p.add_argument('--workers', type=int, default=6)
    a = p.parse_args()
    if a.smoke_draws is not None:
        if not 1 <= a.smoke_draws <= 20:
            p.error('smoke draws must be 1..20')
        run(a.smoke_draws, a.workers); return
    if not a.criterion_commit:
        p.error('full run requires --criterion-commit')
    validate_pins(a.criterion_commit)
    if (ROOT/'docs/audits/count_repairs_validation.json').exists():
        p.error('refusing to overwrite the full audit')
    write_audit(run(DRAWS, a.workers), a.criterion_commit)


if __name__ == '__main__':
    main()
