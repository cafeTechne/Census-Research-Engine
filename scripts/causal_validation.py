# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fixed Round 41 validation: treatment effects, 2SLS with a second measurement, mediation.

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
sys.path.insert(0, str(ROOT))
import numpy as np
from scipy.special import expit
from census import causal_core as cc

SEED = 20270225
DRAWS = 2000
N = 145
CELLS = ([('treatment', rel, None) for rel in (1., .9, .7)] + [('iv', r1, r2) for r1 in (.9, .7) for r2 in (.9, .7)]
         + [('mediation', rel, None) for rel in (1., .8)])
FROZEN = ('scripts/causal_validation.py', 'census/causal_core.py', 'docs/audits/causal_validation_criterion.md')


def noise(rng, rel, n, var=1.):
    return 0. if rel >= 1 else rng.standard_normal(n)*np.sqrt(var*(1-rel)/rel)


def run_cell(args):
    cell, draws = args
    kind, r1, r2 = CELLS[cell]
    rng = np.random.default_rng(SEED+cell)
    keys = {'treatment': ('T1', 'T2', 'T3'), 'iv': ('I0', 'I1'), 'mediation': ('S1', 'S2')}[kind]
    cov = {k: 0 for k in keys}; fails = {k: 0 for k in keys}; est = {k: [] for k in keys}
    target = .2 if kind == 'mediation' else .5
    start = time.time()
    for draw in range(draws):
        if kind == 'treatment':
            z = rng.standard_normal((N, 2)); z[:, 1] = .3*z[:, 0]+np.sqrt(.91)*z[:, 1]
            T = rng.binomial(1, expit(.5*z[:, 0]-.5*z[:, 1]))
            y = 1+.5*T+.5*z[:, 0]+.5*z[:, 1]+rng.standard_normal(N)
            zo = z+np.column_stack([noise(rng, r1, N), noise(rng, r1, N)]) if r1 < 1 else z
            fns = {'T1': lambda: cc.treatment_effect(y, T, zo, 'ipw'), 'T2': lambda: cc.treatment_effect(y, T, zo, 'aipw'),
                   'T3': lambda: cc.treatment_effect(y, T, zo, 'ra')}
        elif kind == 'iv':
            x = rng.standard_normal(N); x1 = x+noise(rng, r1, N); x2 = x+noise(rng, r2, N)
            y = 1+.5*x+rng.standard_normal(N)
            fns = {'I0': lambda: cc.ols_slope(y, x1), 'I1': lambda: cc.iv_2sls(y, x1, x2)}
        else:
            X = rng.standard_normal(N); M = .4*X+rng.standard_normal(N); y = .3*X+.5*M+rng.standard_normal(N)
            Mo = M+noise(rng, r1, N, var=1.16)
            boot = np.random.default_rng(np.random.SeedSequence([SEED, cell, draw, 5]))
            fns = {'S1': lambda: cc.mediation(X, Mo, y, 'sobel'), 'S2': lambda: cc.mediation(X, Mo, y, 'bootstrap', boot)}
        for k, fn in fns.items():
            try:
                r = fn(); cov[k] += r['lower'] <= target <= r['upper']; est[k].append(r['estimate'])
            except (ValueError, np.linalg.LinAlgError):
                fails[k] += 1
    row = dict(cell=cell, kind=kind, reliability=r1, instrument_reliability=r2, draws=draws, target=target,
               coverage={k: v/draws for k, v in cov.items()}, bias={k: float(np.mean(v)-target) if v else None for k, v in est.items()},
               failures=fails, seconds=time.time()-start)
    print(row, flush=True)
    return row


def run(draws, workers):
    with Pool(workers) as pool:
        rows = pool.map(run_cell, [(c, draws) for c in range(len(CELLS))])
    judged = lambda r, kind: r['kind'] == kind and (kind == 'iv' or (kind == 'treatment' and r['reliability'] >= .9)
                                                    or (kind == 'mediation' and r['reliability'] == 1.))
    passed = {k: all(r['coverage'][k] >= .86 for r in rows if judged(r, kind))
              for kind, ks in (('treatment', ('T1', 'T2', 'T3')), ('iv', ('I1',)), ('mediation', ('S1', 'S2'))) for k in ks}
    return dict(rows=rows, passed=passed, draws_per_cell=draws,
                criterion='90% coverage >= .86: treatment in reliability 1.0 and 0.9 cells; 2SLS in all IV cells; '
                          'mediation in the exact-mediator cell; failures count as non-coverage; other cells informational')


def validate_pins(commit):
    subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'], cwd=ROOT, check=True)
    for rel in FROZEN:
        if subprocess.check_output(['git', 'show', commit+':'+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
            raise ValueError('script/design differs from criterion commit: '+rel)


def write_audit(result, commit):
    out = ROOT/'docs/audits/causal_validation'
    result['criterion_commit'] = commit
    result['frozen_sha256'] = {rel: hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() for rel in FROZEN}
    out.with_suffix('.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    lines = ['# Treatment effects, instrumental variables and mediation: validation (Round 41)', '', result['criterion']+'.', '',
             f"Criterion commit: `{commit}`. {result['draws_per_cell']:,} draws per cell.", '',
             '| Kind | Reliability | Instrument reliability | Coverage | Bias |', '| :--- | ---: | ---: | :--- | :--- |']
    for r in result['rows']:
        lines.append(f"| {r['kind']} | {r['reliability']} | {r['instrument_reliability'] or ''} | "
                     + ', '.join(f"{k} {v:.4f}" for k, v in r['coverage'].items()) + ' | '
                     + ', '.join(f"{k} {v:+.3f}" for k, v in r['bias'].items() if v is not None) + ' |')
    lines += ['', 'Outcomes: `'+json.dumps(result['passed'], sort_keys=True)+'`.']
    out.with_suffix('.md').write_text('\n'.join(lines)+'\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--smoke-draws', type=int); p.add_argument('--criterion-commit'); p.add_argument('--workers', type=int, default=9)
    a = p.parse_args()
    if a.smoke_draws is not None:
        if not 1 <= a.smoke_draws <= 20:
            p.error('smoke draws must be 1..20')
        run(a.smoke_draws, a.workers); return
    if not a.criterion_commit:
        p.error('full run requires --criterion-commit')
    validate_pins(a.criterion_commit)
    if (ROOT/'docs/audits/causal_validation.json').exists():
        p.error('refusing to overwrite the full audit')
    write_audit(run(DRAWS, a.workers), a.criterion_commit)


if __name__ == '__main__':
    main()
