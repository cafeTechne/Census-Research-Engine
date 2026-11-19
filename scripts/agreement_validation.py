# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fixed Round 37 validation of agreement procedures.

    --prepare-targets       reference targets per cell (400,000 areas; once, before freezing)
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
from census import agreement_core as ag
from spatial_hac_validation import simulation_setup, haversine_matrix

SEED = 20270128
DRAWS = 2000
CELLS = [(rel_a, b_err, dist) for rel_a in (.9, .7) for b_err in (False, True) for dist in (0, 100)]
TARGETS = 'docs/audits/agreement_targets.json'
GEOMETRY = 'docs/audits/im_acs_beta_star.json'
FROZEN = ('scripts/agreement_validation.py', 'census/agreement_core.py', 'scripts/spatial_hac_validation.py',
          'docs/audits/agreement_validation_criterion.md', TARGETS, GEOMETRY)
KEYS = ('B0', 'B1_lower', 'B1_upper', 'B2_lower', 'B2_upper', 'C1', 'C2', 'K1')


def setup(cell):
    rel_a, b_err, dist = CELLS[cell]
    g = json.loads((ROOT/GEOMETRY).read_text())['coordinates']
    rng, L, _ = simulation_setup('linear', dist, haversine_matrix(np.asarray(g['lon']), np.asarray(g['lat'])), SEED+cell)
    n = len(L)
    a = rng.lognormal(0, .5, n); a *= np.sqrt(((1-rel_a)/rel_a)/np.mean(a**2))
    b = rng.lognormal(0, .5, n); b *= np.sqrt((1.05**2*(1-.8)/.8)/np.mean(b**2))
    return rng, L, a, (b if b_err else np.zeros(n))


DELTA_SD = .5   # genuine (error-free) disagreement between the two sources


def sources(rng, t, a, b):
    """Returns observed x, y and the error-free value of B (B differs from A by a bias, a slope and delta)."""
    delta = rng.standard_normal(len(t))*DELTA_SD
    b_true = .2+1.05*t+delta
    x = t+rng.standard_normal(len(t))*a
    y = b_true+rng.standard_normal(len(t))*b
    return x, y, b_true


def prepare_targets():
    path = ROOT/TARGETS
    if path.exists():
        raise ValueError('refusing to replace committed targets')
    rows = []
    for cell in range(len(CELLS)):
        _, _, a, b = setup(cell)
        rng = np.random.default_rng(np.random.SeedSequence([SEED, cell, 400000]))
        n = 400000; idx = rng.integers(0, len(a), n)
        t = rng.standard_normal(n); x, y, bt = sources(rng, t, a[idx], b[idx])
        d, dt = y-x, bt-t
        sub = rng.choice(n, 40000, replace=False)
        rows.append(dict(cell=cell, B0=float(d.mean()), B1_lower=float(d.mean()-ag.ZL*d.std()), B1_upper=float(d.mean()+ag.ZL*d.std()),
                         B2_lower=float(dt.mean()-ag.ZL*dt.std()), B2_upper=float(dt.mean()+ag.ZL*dt.std()),
                         C1=ag._ccc_parts(x, y)[0], C2=ag._ccc_parts(t, bt)[0],
                         K1=ag.kappa_quintiles(x[sub], y[sub])['estimate']))
    path.write_text(json.dumps(dict(seed=SEED, reference_areas=400000, kappa_subsample=40000, rows=rows), indent=2)+'\n')
    print(rows)


def run_cell(args):
    cell, draws = args
    rel_a, b_err, dist = CELLS[cell]
    tg = json.loads((ROOT/TARGETS).read_text())['rows'][cell]
    rng, L, a, b = setup(cell)
    n = len(L)
    cov = {k: 0 for k in KEYS}; fails = {}
    start = time.time()
    for _ in range(draws):
        t = L@rng.standard_normal(n)
        x, y, _ = sources(rng, t, a, b)
        def chk(key, fn, lo_hi):
            try:
                cov[key] += lo_hi(fn())
            except (ValueError, FloatingPointError):
                fails[key] = fails.get(key, 0)+1
        chk('B0', lambda: ag.bias(x, y), lambda r: r['lower'] <= tg['B0'] <= r['upper'])
        r1 = ag.limits_observed(x, y)
        cov['B1_lower'] += r1['lower_ci'][0] <= tg['B1_lower'] <= r1['lower_ci'][1]
        cov['B1_upper'] += r1['upper_ci'][0] <= tg['B1_upper'] <= r1['upper_ci'][1]
        try:
            r2 = ag.limits_true(x, y, a, b if b_err else None)
            cov['B2_lower'] += r2['lower_ci'][0] <= tg['B2_lower'] <= r2['lower_ci'][1]
            cov['B2_upper'] += r2['upper_ci'][0] <= tg['B2_upper'] <= r2['upper_ci'][1]
        except ValueError:
            fails['B2'] = fails.get('B2', 0)+1
        chk('C1', lambda: ag.ccc(x, y), lambda r: r['lower'] <= tg['C1'] <= r['upper'])
        chk('C2', lambda: ag.ccc(x, y, a, b if b_err else None), lambda r: r['lower'] <= tg['C2'] <= r['upper'])
        chk('K1', lambda: ag.kappa_quintiles(x, y), lambda r: r['lower'] <= tg['K1'] <= r['upper'])
    row = dict(cell=cell, reliability_a=rel_a, b_error=b_err, range_km=dist, draws=draws,
               coverage={k: v/draws for k, v in cov.items()}, failures=fails, seconds=time.time()-start)
    print(f"cell {cell} relA={rel_a} bErr={b_err} dist={dist} " + ' '.join(f"{k}={v:.3f}" for k, v in row['coverage'].items()), flush=True)
    return row


def run(draws, workers):
    with Pool(workers) as pool:
        rows = pool.map(run_cell, [(c, draws) for c in range(len(CELLS))])
    indep = [r for r in rows if r['range_km'] == 0]
    passed = {k: all(r['coverage'][k] >= .86 for r in indep) for k in ('B0', 'C1', 'C2', 'K1')}
    passed['B1'] = all(r['coverage'][k] >= .86 for r in indep for k in ('B1_lower', 'B1_upper'))
    passed['B2'] = all(r['coverage'][k] >= .86 for r in indep for k in ('B2_lower', 'B2_upper'))
    return dict(rows=rows, passed=passed, draws_per_cell=draws,
                criterion='90% coverage >= .86 in every independent cell, per procedure (both limits for B1, B2); '
                          'failures count as non-coverage; spatial cells informational')


def validate_pins(commit):
    subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'], cwd=ROOT, check=True)
    for rel in FROZEN:
        if subprocess.check_output(['git', 'show', commit+':'+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
            raise ValueError('script/design differs from criterion commit: '+rel)


def write_audit(result, commit):
    out = ROOT/'docs/audits/agreement_validation'
    result['criterion_commit'] = commit
    result['frozen_sha256'] = {rel: hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() for rel in FROZEN}
    out.with_suffix('.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    lines = ['# Agreement between sources: validation (Round 37)', '', result['criterion']+'.', '',
             f"Criterion commit: `{commit}`. {result['draws_per_cell']:,} draws per cell.", '',
             '| A reliability | B error | Range km | ' + ' | '.join(KEYS) + ' |', '| ' + ' | '.join(['---:']*3+['---:']*len(KEYS)) + ' |']
    for r in result['rows']:
        lines.append(f"| {r['reliability_a']} | {r['b_error']} | {r['range_km']} | " + ' | '.join(f"{r['coverage'][k]:.4f}" for k in KEYS) + ' |')
    lines += ['', 'Outcomes: `'+json.dumps(result['passed'], sort_keys=True)+'`.']
    out.with_suffix('.md').write_text('\n'.join(lines)+'\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepare-targets', action='store_true'); p.add_argument('--smoke-draws', type=int)
    p.add_argument('--criterion-commit'); p.add_argument('--workers', type=int, default=8)
    a = p.parse_args()
    with patch('requests.sessions.Session.request', side_effect=RuntimeError('Round 37: HTTP blocked')):
        if a.prepare_targets:
            prepare_targets(); return
        if a.smoke_draws is not None:
            if not 1 <= a.smoke_draws <= 20:
                p.error('smoke draws must be 1..20')
            run(a.smoke_draws, a.workers); return
        if not a.criterion_commit:
            p.error('full run requires --criterion-commit')
        validate_pins(a.criterion_commit)
        if (ROOT/'docs/audits/agreement_validation.json').exists():
            p.error('refusing to overwrite the full audit')
        write_audit(run(DRAWS, a.workers), a.criterion_commit)


if __name__ == '__main__':
    main()
