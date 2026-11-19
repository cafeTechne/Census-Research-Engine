# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fixed Round 40 validation of beta and median regression intervals.

    --prepare-targets       400,000-area reference targets (once, before freezing)
    --smoke-draws N         1..20 draws per cell; no files
    --criterion-commit SHA  the full run (1,000 draws per cell)
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
from census import beta_median_core as bm
from census.simulation import make_replicates

SEED = 20270218
DRAWS = 1000
N = 145
CELLS = [('beta', rel, c) for rel in (.9, .7) for c in (.02, .05)]+[('median', rel, None) for rel in (.9, .7)]
TARGETS = 'docs/audits/beta_median_targets.json'
FROZEN = ('scripts/beta_median_validation.py', 'census/beta_median_core.py', 'census/simulation.py',
          'docs/audits/beta_median_validation_criterion.md', TARGETS)
SKEW_SD = .8


def setup(cell):
    kind, rel, c = CELLS[cell]
    rng = np.random.default_rng(SEED+cell)
    sx = rng.lognormal(0, .5, N); sx *= np.sqrt(((1-rel)/rel)/np.mean(sx**2))
    sy = rng.lognormal(0, .5, N)
    return rng, sx, sy


def generate(rng, kind, c, sx, sy, n):
    x = rng.standard_normal(n); xo = x+rng.standard_normal(n)*sx
    if kind == 'beta':
        mu = expit(-1.5+.4*x); y = rng.beta(mu*30, (1-mu)*30)
        sey = c*np.sqrt(mu*(1-mu))*sy/np.sqrt(np.mean(sy**2))
    else:
        noise = np.exp(rng.standard_normal(n)*SKEW_SD); noise -= np.exp(SKEW_SD**2/2)
        y = 1+.5*x+noise
        vy = .25+(np.exp(SKEW_SD**2)-1)*np.exp(SKEW_SD**2)
        sey = sy*np.sqrt((.1/.9*vy)/np.mean(sy**2))
    yo = y+rng.standard_normal(n)*sey
    if kind == 'beta':
        yo = np.clip(yo, 1e-3, 1-1e-3)
    return xo, yo, sey


def prepare_targets():
    path = ROOT/TARGETS
    if path.exists():
        raise ValueError('refusing to replace committed targets')
    rows = []
    for cell, (kind, rel, c) in enumerate(CELLS):
        _, sx, sy = setup(cell)
        rng = np.random.default_rng(np.random.SeedSequence([SEED, cell, 400000]))
        n = 400000; idx = rng.integers(0, N, n)
        xo, yo, _ = generate(rng, kind, c, sx[idx], sy[idx], n)
        X = np.column_stack((np.ones(n), xo))
        b = bm.beta_fit(yo, X)[0][1] if kind == 'beta' else bm.median_fit(yo, X)[0][1]
        rows.append(dict(cell=cell, target=float(b))); print(cell, b, flush=True)
    path.write_text(json.dumps(dict(seed=SEED, reference_areas=400000, rows=rows), indent=2)+'\n')


def run_cell(args):
    cell, draws = args
    kind, rel, c = CELLS[cell]
    target = json.loads((ROOT/TARGETS).read_text())['rows'][cell]['target']
    rng, sx, sy = setup(cell)
    keys = ('B1', 'B2', 'B3') if kind == 'beta' else ('Q1', 'Q2')
    cov = {k: 0 for k in keys}; fails = 0
    start = time.time()
    for draw in range(draws):
        xo, yo, sey = generate(rng, kind, c, sx, sy, N)
        aux = np.random.default_rng(np.random.SeedSequence([SEED, cell, draw, 7]))
        rep = make_replicates(np.column_stack((xo, yo)), np.column_stack((sx, sey)), aux)
        X = np.column_stack((np.ones(N), xo))
        Xr = np.stack([np.column_stack((np.ones(N), rep[:, 0, r])) for r in range(80)])
        Yr = rep[:, 1, :].T
        try:
            if kind == 'beta':
                Yr = np.clip(Yr, 1e-3, 1-1e-3)
                b1, s1 = bm.beta_fit(yo, X); b2, s2 = bm.beta_fit(yo, X, 'hc0')
                vr = bm.replicate_variance(lambda y, x: bm.beta_fit(y, x, 'hc0'), Yr, Xr, b2)
                res = {'B1': bm.interval(b1, s1), 'B2': bm.interval(b2, s2), 'B3': bm.interval(b2, s2, extra_var=vr)}
            else:
                b, s = bm.median_fit(yo, X)
                vr = bm.replicate_variance(bm.median_fit, Yr, Xr, b)
                res = {'Q1': bm.interval(b, s), 'Q2': bm.interval(b, s, extra_var=vr)}
            for k, r in res.items():
                cov[k] += r['lower'] <= target <= r['upper']
        except (ValueError, np.linalg.LinAlgError):
            fails += 1
    row = dict(cell=cell, kind=kind, reliability=rel, outcome_error=c, draws=draws,
               coverage={k: v/draws for k, v in cov.items()}, failures=fails, seconds=time.time()-start)
    print(row, flush=True)
    return row


def run(draws, workers):
    with Pool(workers) as pool:
        rows = pool.map(run_cell, [(c, draws) for c in range(len(CELLS))])
    passed = {k: all(r['coverage'][k] >= .86 for r in rows if k in r['coverage']) for k in ('B1', 'B2', 'B3', 'Q1', 'Q2')}
    return dict(rows=rows, passed=passed, draws_per_cell=draws,
                criterion='90% coverage of the naive-target slope >= .86 in every cell of the family; failures count as non-coverage')


def validate_pins(commit):
    subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'], cwd=ROOT, check=True)
    for rel in FROZEN:
        if subprocess.check_output(['git', 'show', commit+':'+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
            raise ValueError('script/design differs from criterion commit: '+rel)


def write_audit(result, commit):
    out = ROOT/'docs/audits/beta_median_validation'
    result['criterion_commit'] = commit
    result['frozen_sha256'] = {rel: hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() for rel in FROZEN}
    out.with_suffix('.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    lines = ['# Beta and median regression: validation (Round 40)', '', result['criterion']+'.', '',
             f"Criterion commit: `{commit}`. {result['draws_per_cell']:,} draws per cell.", '',
             '| Family | Covariate reliability | Outcome error | Coverage | Failures |', '| :--- | ---: | ---: | :--- | ---: |']
    for r in result['rows']:
        lines.append(f"| {r['kind']} | {r['reliability']} | {r['outcome_error']} | " +
                     ', '.join(f"{k} {v:.4f}" for k, v in r['coverage'].items()) + f" | {r['failures']} |")
    lines += ['', 'Outcomes: `'+json.dumps(result['passed'], sort_keys=True)+'`.']
    out.with_suffix('.md').write_text('\n'.join(lines)+'\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepare-targets', action='store_true'); p.add_argument('--smoke-draws', type=int)
    p.add_argument('--criterion-commit'); p.add_argument('--workers', type=int, default=6)
    a = p.parse_args()
    if a.prepare_targets:
        prepare_targets(); return
    if a.smoke_draws is not None:
        if not 1 <= a.smoke_draws <= 20:
            p.error('smoke draws must be 1..20')
        run(a.smoke_draws, a.workers); return
    if not a.criterion_commit:
        p.error('full run requires --criterion-commit')
    validate_pins(a.criterion_commit)
    if (ROOT/'docs/audits/beta_median_validation.json').exists():
        p.error('refusing to overwrite the full audit')
    write_audit(run(DRAWS, a.workers), a.criterion_commit)


if __name__ == '__main__':
    main()
