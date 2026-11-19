# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fixed Round 42 validation: multiple imputation, censored Poisson, interrupted time series.

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
from census import mci_core as mi

SEED = 20270304
DRAWS = 2000
N = 145
CELLS = [('missing', 'MAR'), ('missing', 'MCAR'), ('censored', 10), ('censored', 30), ('its', .3), ('its', .6)]
FROZEN = ('scripts/missing_censored_its_validation.py', 'census/mci_core.py', 'docs/audits/missing_censored_its_validation_criterion.md')


def run_cell(args):
    cell, draws = args
    kind, par = CELLS[cell]
    rng = np.random.default_rng(SEED+cell)
    cov = {}; fails = {}
    def add(key, r, target):
        cov[key] = cov.get(key, 0)+(r['lower'] <= target <= r['upper'])
    start = time.time()
    if kind == 'censored':
        E = np.maximum(1, np.rint(rng.lognormal(np.log(par), 1, N)))
    for draw in range(draws):
        try:
            if kind == 'missing':
                x = rng.standard_normal(N); w = .5*x+np.sqrt(.75)*rng.standard_normal(N)
                y = 1+.5*x+.5*w+rng.standard_normal(N)
                p = expit(-1.6+.9*(y-y.mean())) if par == 'MAR' else np.full(N, .2)   # MAR on the observed outcome
                wm = np.where(rng.random(N) < p, np.nan, w)
                X = np.column_stack((np.ones(N), x, wm))
                add('D0', mi.complete_case(y, X), .5)
                aux = np.random.default_rng(np.random.SeedSequence([SEED, cell, draw, 3]))
                add('D1', mi.multiple_imputation(y, X, 2, aux), .5)
            elif kind == 'censored':
                x = rng.standard_normal(N)
                lam = E*np.exp(.3*x)*rng.gamma(4, .25, N)
                y = rng.poisson(lam).astype(float); cens = (y >= 1) & (y <= 9)
                X = np.column_stack((np.ones(N), x))
                add('C0', mi.poisson_complete_case(y, X, E, cens), .3)
                add('C1', mi.censored_poisson(y, X, E, cens), .3)
            else:
                T = 20; e = np.zeros(T); z = rng.standard_normal(T)
                e[0] = z[0]/np.sqrt(1-par**2)
                for t in range(1, T):
                    e[t] = par*e[t-1]+z[t]
                X = mi.its_design(T, 11)
                y = X @ np.array([10, .1, 1., .2])+e
                for name, meth in (('A0', 'ols'), ('A1', 'hac'), ('A2', 'ar1')):
                    lv, sl = mi.interrupted(y, X, meth)
                    add(name+'_level', lv, 1.); add(name+'_slope', sl, .2)
        except (ValueError, np.linalg.LinAlgError, FloatingPointError):
            fails[draw] = 1
    row = dict(cell=cell, kind=kind, parameter=par, draws=draws, coverage={k: v/draws for k, v in sorted(cov.items())},
               failed_draws=len(fails), seconds=time.time()-start)
    print(row, flush=True)
    return row


def run(draws, workers):
    with Pool(workers) as pool:
        rows = pool.map(run_cell, [(c, draws) for c in range(len(CELLS))])
    passed = {}
    for key, kind in (('D1', 'missing'), ('C1', 'censored'), ('A1', 'its'), ('A2', 'its')):
        sel = [r for r in rows if r['kind'] == kind]
        ks = [k for k in sel[0]['coverage'] if k.startswith(key)]
        passed[key] = all(r['coverage'][k] >= .86 for r in sel for k in ks)
    return dict(rows=rows, passed=passed, draws_per_cell=draws,
                criterion='90% coverage >= .86 in every cell of the problem (ITS: level and slope change); failures count '
                          'as non-coverage; D0, C0, A0 are comparisons')


def validate_pins(commit):
    subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'], cwd=ROOT, check=True)
    for rel in FROZEN:
        if subprocess.check_output(['git', 'show', commit+':'+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
            raise ValueError('script/design differs from criterion commit: '+rel)


def write_audit(result, commit):
    out = ROOT/'docs/audits/missing_censored_its_validation'
    result['criterion_commit'] = commit
    result['frozen_sha256'] = {rel: hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() for rel in FROZEN}
    out.with_suffix('.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    lines = ['# Missing data, censored counts and interrupted time series: validation (Round 42)', '', result['criterion']+'.', '',
             f"Criterion commit: `{commit}`. {result['draws_per_cell']:,} draws per cell.", '',
             '| Problem | Setting | Coverage | Failed draws |', '| :--- | :--- | :--- | ---: |']
    for r in result['rows']:
        lines.append(f"| {r['kind']} | {r['parameter']} | " + ', '.join(f"{k} {v:.4f}" for k, v in r['coverage'].items())
                     + f" | {r['failed_draws']} |")
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
    if (ROOT/'docs/audits/missing_censored_its_validation.json').exists():
        p.error('refusing to overwrite the full audit')
    write_audit(run(DRAWS, a.workers), a.criterion_commit)


if __name__ == '__main__':
    main()
