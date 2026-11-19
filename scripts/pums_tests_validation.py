# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fixed Round 32 validation of design-based PUMS procedures (PLAN_ROUND_32 section 2).

    --prepare-targets              write the reference-population targets (once, before freezing)
    --smoke-draws N                1..20 draws per cell; writes no files
    --criterion-commit SHA         the full run (2,000 draws per cell)
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
from census import pums_tests as pt

SEED = 20261225
DRAWS = 2000
CELLS = [(rho, cv, m) for rho in (.1, .4) for cv in (.3, 1.) for m in (800, 3000)]
TARGETS = 'docs/audits/pums_tests_targets.json'
FROZEN = ('scripts/pums_tests_validation.py', 'census/pums_tests.py', 'census/pums.py',
          'docs/audits/pums_tests_validation_criterion.md', TARGETS)
GRID = np.linspace(0, 1, 10001)
THRESH_A, THRESH_B = (-.4, .4), (-.6745, 0., .6745)
THRESH_D, THRESH_C, THRESH_R = .5244, 1.0, 1.8808
TESTS = ('T0', 'T1', 'T2', 'T3')


def field(g):
    z = np.sin(2*np.pi*g)+.5*np.cos(6*np.pi*g)
    return z/np.std(np.sin(2*np.pi*GRID)+.5*np.cos(6*np.pi*GRID))


def sigma_for(cv):
    """sigma such that the weights 1/pi have coefficient of variation cv among sampled households."""
    lo, hi = 0., 5.
    for _ in range(80):
        s = (lo+hi)/2; pi = np.exp(s*field(GRID)); dens = pi/pi.sum(); w = 1/pi
        mean = dens@w; c = np.sqrt(dens@(w-mean)**2)/mean
        lo, hi = (s, hi) if c < cv else (lo, s)
    return (lo+hi)/2


def population(rng, g, rho):
    """Households at coordinates g -> person-level attributes."""
    H = len(g); size = 1+rng.poisson(1.5, H); idx = np.repeat(np.arange(H), size); n = len(idx)
    he = rng.standard_normal((6, H)); pe = rng.standard_normal((6, n))
    lat = np.sqrt(rho)*he[:, idx]+np.sqrt(1-rho)*pe
    gp = g[idx]
    A = np.digitize(.8*np.sin(2*np.pi*gp)+lat[0], THRESH_A)
    B = np.digitize(lat[1], THRESH_B)
    D = lat[2] > THRESH_D
    C = .4*A+.5*np.cos(2*np.pi*gp)+lat[3] > THRESH_C
    y0 = np.exp(10.5+.6*lat[4])
    y1 = np.exp(10.5+.15*A+.3*(gp-.5)+.6*lat[4])
    R = lat[5] > THRESH_R
    domain = gp < .125
    return dict(idx=idx, A=A, B=B, D=D, C=C, y0=y0, y1=y1, R=R, domain=domain)


def prepare_targets():
    path = ROOT/TARGETS
    if path.exists():
        raise ValueError('refusing to replace committed targets')
    rng = np.random.default_rng(np.random.SeedSequence([SEED, 2000000]))
    p = population(rng, rng.uniform(0, 1, 2000000), .25)
    a01 = p['A'] <= 1; e = p['A'][a01] == 1; c = p['C'][a01]
    p1, p0 = c[e].mean(), c[~e].mean()
    y = p['y1'][a01]
    targets = dict(diff_prop=float(p1-p0), odds_ratio=float((p1/(1-p1))/(p0/(1-p0))), relative_risk=float(p1/p0),
                   diff_mean=float(y[e].mean()-y[~e].mean()), diff_median=float(np.median(y[e])-np.median(y[~e])),
                   rare_prevalence=float(p['R'][p['domain']].mean()),
                   reference=dict(households=2000000, persons=int(len(p['idx'])), seed=[SEED, 2000000],
                                  note='marginal distributions do not depend on rho, weights or m'))
    path.write_text(json.dumps(targets, indent=2)+'\n')
    print(json.dumps(targets, indent=2))


def draw_sample(rng, sigma, rho, m):
    u = rng.uniform(0, 1, m)
    pi = np.exp(sigma*field(GRID)); cdf = np.cumsum(pi); cdf /= cdf[-1]
    g = np.sort(np.interp(u, cdf, GRID))                       # sampled households in geography order
    w = 1/np.exp(sigma*field(g))
    p = population(rng, g, rho)
    W = (w[:, None]*np.column_stack((np.ones(m), pt.sdr_factors(m))))[p['idx']]
    return p, W


def evaluate(p, W, targets):
    out = {}
    def guard(name, fn):
        try:
            out[name] = fn()
        except (ValueError, np.linalg.LinAlgError, FloatingPointError, ZeroDivisionError):
            out[name] = None
    guard('ind2', lambda: pt.independence((p['A'] == 0).astype(int), p['D'].astype(int), W))
    guard('ind34', lambda: pt.independence(p['A'], p['B'], W))
    guard('means3', lambda: pt.means_test(p['y0'], p['A'], W))
    a01 = p['A'] <= 1
    guard('means2', lambda: pt.means_test(p['y0'][a01], p['A'][a01], W[a01]))
    guard('I1', lambda: pt.difference_of_proportions(p['C'][a01], p['A'][a01], W[a01]))
    guard('I23', lambda: pt.two_by_two(p['A'][a01] == 1, p['C'][a01], W[a01]))
    guard('I4', lambda: pt.difference_of_means(p['y1'][a01], p['A'][a01], W[a01]))
    guard('I5', lambda: pt.difference_of_medians(p['y1'][a01], p['A'][a01], W[a01]))
    d = p['domain']
    guard('P1', lambda: pt.proportion_interval(p['R'][d], W[d], 'wald'))
    guard('P2', lambda: pt.proportion_interval(p['R'][d], W[d], 'korn_graubard'))
    rej, cov = {}, {}
    for key, tab in (('ind2', '2x2'), ('ind34', '3x4')):
        for t in TESTS:
            rej[f'{t}/{tab}'] = out[key] is None or out[key][t]['p'] < .10
    rej['M3/3group'] = out['means3'] is None or out['means3']['M3']['p'] < .10
    for t in ('M1', 'M2'):
        rej[f'{t}/2group'] = out['means2'] is None or out['means2'][t]['p'] < .10
    within = lambda r, target: r is not None and r['lower'] <= target <= r['upper']
    cov['I1'] = within(out['I1'], targets['diff_prop'])
    cov['I2'] = out['I23'] is not None and within(out['I23']['odds_ratio'], targets['odds_ratio'])
    cov['I3'] = out['I23'] is not None and within(out['I23']['relative_risk'], targets['relative_risk'])
    cov['I4'] = within(out['I4'], targets['diff_mean'])
    cov['I5'] = within(out['I5'], targets['diff_median'])
    cov['P1'] = within(out['P1'], targets['rare_prevalence'])
    cov['P2'] = within(out['P2'], targets['rare_prevalence'])
    fails = [k for k, v in out.items() if v is None]
    info = dict(deff2=out['ind2']['deff_mean'] if out['ind2'] else None,
                deff34=out['ind34']['deff_mean'] if out['ind34'] else None)
    return rej, cov, fails, info


def run_cell(args):
    cell, draws = args
    rho, cv, m = CELLS[cell]
    targets = json.loads((ROOT/TARGETS).read_text())
    rng = np.random.default_rng(SEED+cell); sigma = sigma_for(cv)
    rej, cov, fails, deff = {}, {}, {}, {'deff2': [], 'deff34': []}
    start = time.time()
    for _ in range(draws):
        p, W = draw_sample(rng, sigma, rho, m)
        r, c, f, info = evaluate(p, W, targets)
        for k, v in r.items(): rej[k] = rej.get(k, 0)+int(v)
        for k, v in c.items(): cov[k] = cov.get(k, 0)+int(v)
        for k in f: fails[k] = fails.get(k, 0)+1
        for k, v in info.items():
            if v is not None: deff[k].append(v)
    row = dict(cell=cell, rho=rho, weight_cv=cv, households=m, draws=draws, sigma=sigma,
               size_10={k: v/draws for k, v in rej.items()}, coverage_90={k: v/draws for k, v in cov.items()},
               failures=fails, mean_deff={k: float(np.mean(v)) if v else None for k, v in deff.items()},
               seconds=time.time()-start)
    print(f"cell {cell} rho={rho} cv={cv} m={m} " + ' '.join(f"{k}={v:.3f}" for k, v in row['size_10'].items())
          + ' | ' + ' '.join(f"{k}={v:.3f}" for k, v in row['coverage_90'].items()) + f" {row['seconds']:.0f}s", flush=True)
    return row


def run(draws, workers):
    with Pool(workers) as pool:
        rows = pool.map(run_cell, [(c, draws) for c in range(len(CELLS))])
    tests = sorted(rows[0]['size_10']); intervals = sorted(rows[0]['coverage_90'])
    passed = {k: all(.07 <= r['size_10'][k] <= .13 for r in rows) for k in tests}
    passed.update({k: all(r['coverage_90'][k] >= .86 for r in rows) for k in intervals})
    return dict(rows=rows, passed=passed, draws_per_cell=draws,
                criterion='tests: nominal-.10 size in [.07,.13] in every cell; intervals: 90% coverage >= .86 in every '
                          'cell; failed computations count as rejections / non-coverage')


def validate_pins(commit):
    subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'], cwd=ROOT, check=True)
    for rel in FROZEN:
        if subprocess.check_output(['git', 'show', commit+':'+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
            raise ValueError('script/design differs from criterion commit: '+rel)


def write_audit(result, commit):
    out = ROOT/'docs/audits/pums_tests_validation'
    result['criterion_commit'] = commit
    result['frozen_sha256'] = {rel: hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() for rel in FROZEN}
    out.with_suffix('.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    rows = result['rows']; tests = sorted(rows[0]['size_10']); intervals = sorted(rows[0]['coverage_90'])
    head = '| ρ | weight CV | households | ' + ' | '.join(tests) + ' |'
    lines = ['# PUMS design-based procedures: validation (Round 32)', '', result['criterion']+'.', '',
             f"Criterion commit: `{commit}`. {result['draws_per_cell']:,} draws per cell; nothing retuned.", '',
             '## Tests: size at nominal .10', '', head, '| ' + ' | '.join([':---']*3+['---:']*len(tests)) + ' |']
    for r in rows:
        lines.append(f"| {r['rho']} | {r['weight_cv']} | {r['households']} | " + ' | '.join(f"{r['size_10'][k]:.4f}" for k in tests) + ' |')
    lines += ['', '## Intervals: 90% coverage', '', '| ρ | weight CV | households | ' + ' | '.join(intervals) + ' |',
              '| ' + ' | '.join([':---']*3+['---:']*len(intervals)) + ' |']
    for r in rows:
        lines.append(f"| {r['rho']} | {r['weight_cv']} | {r['households']} | " + ' | '.join(f"{r['coverage_90'][k]:.4f}" for k in intervals) + ' |')
    lines += ['', 'Mean design effects (δ̄) and failure counts are in the JSON.', '',
              'Outcomes: `'+json.dumps(result['passed'], sort_keys=True)+'`.', '',
              'T0 (Pearson, ignores the design) is a comparison row. Targets come from a committed 2,000,000-household '
              'reference population (`pums_tests_targets.json`).']
    out.with_suffix('.md').write_text('\n'.join(lines)+'\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepare-targets', action='store_true'); p.add_argument('--smoke-draws', type=int)
    p.add_argument('--criterion-commit'); p.add_argument('--workers', type=int, default=8)
    args = p.parse_args()
    with patch('requests.sessions.Session.request', side_effect=RuntimeError('Round 32: HTTP blocked')):
        if args.prepare_targets:
            prepare_targets(); return
        if args.smoke_draws is not None:
            if not 1 <= args.smoke_draws <= 20:
                p.error('smoke draws must be 1..20; no audits written')
            run(args.smoke_draws, args.workers); return
        if not args.criterion_commit:
            p.error('full run requires --criterion-commit')
        validate_pins(args.criterion_commit)
        out = ROOT/'docs/audits/pums_tests_validation'
        if out.with_suffix('.json').exists() or out.with_suffix('.md').exists():
            p.error('refusing to rerun/overwrite the full audit')
        write_audit(run(DRAWS, args.workers), args.criterion_commit)


if __name__ == '__main__':
    main()
