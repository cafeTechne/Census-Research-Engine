# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fixed Round 48 validation: short interrupted series (I), correlations (C) and Feldt alpha (A) under spatial
dependence, random-effects pooling for k = 5-10 (H), Bland-Altman limits (B).

    --smoke-draws N         1..20 draws per cell; no files
    --criterion-commit SHA  the full run (2,000 draws per cell)
"""
import argparse
import hashlib
import json
import subprocess
import sys
import time
import warnings
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'scripts'))
import numpy as np
from census import evidence_core as ev
from census import index_core as ic
from census import mci_core as mi
from census import small_spatial_core as sc
from census.simulation import make_replicates
from spatial_hac_validation import haversine_matrix
import agreement_validation as AGV
import index_validation as IXV
import rank_validation as RKV

SEED = 20270601
DRAWS = 2000
CHUNK = 250
GEOMETRY = 'docs/audits/im_acs_beta_star.json'
CELLS = ([('I', dict(n=n, phi=phi)) for n in (15, 20, 30) for phi in (.3, .6)]
         + [('C', dict(r33_cell=c)) for c in range(8)]
         + [('A', dict(r36_cell=c)) for c in range(8)]
         + [('H', dict(k=k, tau_ratio=t)) for k in (5, 7, 10) for t in (.5, 2.)]
         + [('B', dict(r37_cell=c)) for c in (0, 2, 4, 6)])
FROZEN = ('scripts/small_spatial_validation.py', 'census/small_spatial_core.py', 'census/evidence_core.py',
          'census/rank_methods.py', 'census/mci_core.py', 'census/index_core.py', 'docs/audits/small_spatial_validation_criterion.md',
          'scripts/rank_validation.py', 'scripts/index_validation.py', 'scripts/agreement_validation.py',
          'scripts/spatial_hac_validation.py', 'docs/audits/rank_targets.json', 'docs/audits/index_targets.json',
          'docs/audits/agreement_targets.json', GEOMETRY)
CORR_METHODS = (('spearman', 1), ('kendall', 1), ('pearson', 2))


def geometry():
    g = json.loads((ROOT/GEOMETRY).read_text()); c = g['coordinates']
    D = haversine_matrix(np.asarray(c['lon']), np.asarray(c['lat']))
    return sc.class_index(D), np.array([g['assignment'][i] for i in c['GEOID']])


def draw_i(rng, par, ctx):
    n, phi = par['n'], par['phi']; start = n//2+1
    X = mi.its_design(n, start)
    e = rng.standard_normal(n); u = np.empty(n); u[0] = e[0]/np.sqrt(1-phi**2)
    for t in range(1, n):
        u[t] = phi*u[t-1]+e[t]
    y = X @ np.array([0., 0., 1., .2])+u
    rec = {}
    for key in ('I0', 'I1', 'I2'):
        try:
            res = (mi.interrupted(y, X, 'ar1') if key == 'I0' else sc.its_reml(y, X)[0] if key == 'I1'
                   else sc.its_bootstrap_t(y, X, rng)[0])
            rec[key] = [bool(r['lower'] <= tv <= r['upper']) for r, tv in zip(res, (1., .2))]
        except (ValueError, np.linalg.LinAlgError):
            rec[key] = None
    return rec


def draw_c(rng, par, ctx):
    cell = par['r33_cell']; rho = RKV.CELLS[cell][0]
    L, se = ctx['rank'][cell]; n = len(L)
    t = RKV.truths(rng, L, rho, n)
    o = t+rng.standard_normal((n, 4))*se
    rep = make_replicates(o, se, rng)
    tg = ctx['rank_targets'][cell]['observed']
    rec = {}
    for m, v in CORR_METHODS:
        for key, fn in (('C1', lambda: sc.correlation_neff(o[:, 0], o[:, 1], m, ctx['cls'], v, rep[:, 0], rep[:, 1])),
                        ('C2', lambda: sc.correlation_im(o[:, 0], o[:, 1], m, ctx['labels']))):
            try:
                r = fn(); rec[f'{key}_{m}'] = bool(r['lower'] <= tg[m] <= r['upper'])
            except (ValueError, FloatingPointError):
                rec[f'{key}_{m}'] = None
    return rec


def draw_a(rng, par, ctx):
    cell = par['r36_cell']
    L, se = ctx['index'][cell]; n = len(L)
    t = IXV.true_ind(rng, L, n)
    obs = t+rng.standard_normal((n, 5))@np.linalg.cholesky(IXV.CORR).T*se
    m, s = ic.standardize(obs); z = (obs-m)/s                      # as in Round 36
    tg = ctx['index_targets'][cell]['alpha_observed']
    rec = {}
    for key, fn in (('A3', lambda: sc.alpha_neff(z, ctx['cls'])), ('A4', lambda: sc.alpha_im(z, ctx['labels']))):
        try:
            r = fn(); rec[key] = bool(r['lower'] <= tg <= r['upper'])
        except (ValueError, FloatingPointError):
            rec[key] = None
    return rec


def draw_h(rng, par, ctx):
    s, tau2 = ctx['h'][(par['k'], par['tau_ratio'])]
    theta = rng.normal(0, np.sqrt(tau2), len(s))+rng.normal(0, s)
    sh = s*np.sqrt(rng.chisquare(80, len(s))/80)
    rec = {}
    for key, fn in (('H1', lambda: ev.pooled(theta, sh, 'hksj')), ('H2', lambda: sc.hksj_truncated(theta, sh))):
        try:
            r = fn(); rec[key] = bool(r['lower'] <= 0 <= r['upper'])
        except (ValueError, FloatingPointError):
            rec[key] = None
    return rec


def draw_b(rng, par, ctx):
    cell = par['r37_cell']; b_err = AGV.CELLS[cell][1]
    L, a, b = ctx['agree'][cell]; n = len(L)
    t = L @ rng.standard_normal(n)
    x, y, _ = AGV.sources(rng, t, a, b)
    tg = ctx['agree_targets'][cell]
    rec = {}
    for key, fn, pre in (('B1r', lambda: sc.limits_robust(x, y), 'B1'),
                         ('B2r', lambda: sc.limits_robust(x, y, a, b if b_err else None), 'B2')):
        try:
            r = fn()
            rec[key] = [bool(r['lower_ci'][0] <= tg[f'{pre}_lower'] <= r['lower_ci'][1]),
                        bool(r['upper_ci'][0] <= tg[f'{pre}_upper'] <= r['upper_ci'][1])]
        except (ValueError, FloatingPointError):
            rec[key] = None
    return rec


DRAW = dict(I=draw_i, C=draw_c, A=draw_a, H=draw_h, B=draw_b)
_CTX = {}


def context():
    if not _CTX:
        cls, labels = geometry()
        h = {}
        for i, (k, t) in enumerate((k, t) for k in (5, 7, 10) for t in (.5, 2.)):
            r = np.random.default_rng(SEED+1000+i); s = r.lognormal(0, .5, k)
            h[(k, t)] = (s, t*float(np.mean(s**2)))
        _CTX.update(
            cls=cls, labels=labels, h=h,
            rank={c: (lambda o: (o[1], o[2]))(RKV.setup(c)) for c in range(8)},
            index={c: (lambda o: (o[1], o[2]))(IXV.setup(c)) for c in range(8)},
            agree={c: (lambda o: (o[1], o[2], o[3]))(AGV.setup(c)) for c in (0, 2, 4, 6)},
            rank_targets=json.loads((ROOT/RKV.TARGETS).read_text())['rows'],
            index_targets=json.loads((ROOT/IXV.TARGETS).read_text())['rows'],
            agree_targets=json.loads((ROOT/AGV.TARGETS).read_text())['rows'])
    return _CTX


def job(args):
    cell, start, stop = args
    kind, par = CELLS[cell]; ctx = context()
    with warnings.catch_warnings(), np.errstate(all='ignore'):
        warnings.simplefilter('ignore')
        return cell, [DRAW[kind](np.random.default_rng([SEED+cell, d]), par, ctx) for d in range(start, stop)]


def summarise(recs):
    cov, failed = {}, {}
    for key in recs[0]:
        vals = [r[key] for r in recs]
        failed[key] = sum(v is None for v in vals)
        if any(isinstance(v, list) for v in vals):
            for j, part in enumerate(('a', 'b')):
                cov[f'{key}_{part}'] = sum(v[j] for v in vals if v is not None)/len(vals)
        else:
            cov[key] = sum(bool(v) for v in vals if v is not None)/len(vals)
    return dict(coverage=cov, failed=failed)


def run(draws, workers):
    jobs = [(c, s, min(s+CHUNK, draws)) for c in range(len(CELLS)) for s in range(0, draws, CHUNK)]
    jobs.sort(key=lambda j: CELLS[j[0]][0] != 'I')          # long bootstrap cells first
    recs = {c: [] for c in range(len(CELLS))}
    start = time.time()
    with Pool(workers) as pool:
        for cell, rs in pool.imap_unordered(job, jobs):
            recs[cell].extend(rs)
            print(dict(cell=cell, done=len(recs[cell]), seconds=round(time.time()-start)), flush=True)
    rows = [dict(cell=c, kind=CELLS[c][0], parameters=CELLS[c][1], draws=len(recs[c]), **summarise(recs[c]))
            for c in range(len(CELLS))]
    ok = lambda r, prefix: all(v >= .86 for k, v in r['coverage'].items() if k.startswith(prefix))
    by = lambda kind: [r for r in rows if r['kind'] == kind]
    passed = {}
    for key in ('I1', 'I2'):
        n0 = None
        for n in (30, 20, 15):
            if all(ok(r, key+'_') for r in by('I') if r['parameters']['n'] >= n):
                n0 = n
            else:
                break
        passed[f'{key}_min_n'] = n0
    for key in ('C1', 'C2'):
        for m, _ in CORR_METHODS:
            passed[f'{key}_{m}'] = all(r['coverage'][f'{key}_{m}'] >= .86 for r in by('C'))
    for key in ('A3', 'A4'):
        passed[key] = all(r['coverage'][key] >= .86 for r in by('A'))
    for key in ('H1', 'H2'):
        passed[key] = all(r['coverage'][key] >= .86 for r in by('H'))
    for key in ('B1r', 'B2r'):
        passed[key] = all(ok(r, key+'_') for r in by('B'))
    return dict(rows=rows, passed=passed, draws_per_cell=draws,
                criterion='90% coverage >= .86 in every cell of the problem (failed fits count as non-coverage); I: '
                          'smallest n with both changes >= .86 there and at every larger n, both phi; C per method; '
                          'B both limits; I0 is the Round 42 GLSAR comparison')


def validate_pins(commit):
    subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'], cwd=ROOT, check=True)
    for rel in FROZEN:
        if subprocess.check_output(['git', 'show', commit+':'+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
            raise ValueError('script/design differs from criterion commit: '+rel)


def write_audit(result, commit):
    out = ROOT/'docs/audits/small_spatial_validation'
    result['criterion_commit'] = commit
    result['frozen_sha256'] = {rel: hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() for rel in FROZEN}
    out.with_suffix('.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    lines = ['# Small samples and spatial dependence: validation (Round 48)', '', result['criterion']+'.', '',
             f"Criterion commit: `{commit}`. {result['draws_per_cell']:,} draws per cell. Suffix _a/_b: level/slope "
             "change (I) or lower/upper limit (B).", '',
             '| Problem | Setting | Coverage | Failed |', '| :--- | :--- | :--- | :--- |']
    for r in result['rows']:
        p = dict(r['parameters'])
        if r['kind'] == 'C':
            p.update(zip(('rho', 'reliability', 'range_km'), RKV.CELLS[p['r33_cell']]))
        elif r['kind'] == 'A':
            p.update(zip(('reliability', 'range_km', 'weights'), IXV.CELLS[p['r36_cell']]))
        elif r['kind'] == 'B':
            p.update(zip(('reliability_a', 'b_error', 'range_km'), AGV.CELLS[p['r37_cell']]))
        lines.append(f"| {r['kind']} | {', '.join(f'{k} {v}' for k, v in p.items())} | "
                     + ', '.join(f'{k} {v:.4f}' for k, v in r['coverage'].items()) + ' | '
                     + ', '.join(f'{k} {v}' for k, v in r['failed'].items()) + ' |')
    lines += ['', 'Outcomes: `'+json.dumps(result['passed'], sort_keys=True)+'`.']
    out.with_suffix('.md').write_text('\n'.join(lines)+'\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--smoke-draws', type=int); p.add_argument('--criterion-commit'); p.add_argument('--workers', type=int, default=6)
    a = p.parse_args()
    if a.smoke_draws is not None:
        if not 1 <= a.smoke_draws <= 20:
            p.error('smoke draws must be 1..20')
        res = run(a.smoke_draws, a.workers)
        for r in res['rows']:
            print(r['kind'], r['parameters'], r['coverage'], r['failed'])
        print(res['passed']); return
    if not a.criterion_commit:
        p.error('full run requires --criterion-commit')
    validate_pins(a.criterion_commit)
    if (ROOT/'docs/audits/small_spatial_validation.json').exists():
        p.error('refusing to overwrite the full audit')
    write_audit(run(DRAWS, a.workers), a.criterion_commit)


if __name__ == '__main__':
    main()
