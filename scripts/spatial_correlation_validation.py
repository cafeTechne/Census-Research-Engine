# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 59: partial correlations under spatial dependence and an OH/PA re-check of Round 48 (frozen with the
criterion).

P (8 cells): Round 33 cells on MI/NY with Round 48's draw; P1 = partial_neff (replicate term), P0 = Round 33
   independent-area partial interval (comparison); target Round 33's observed partial coefficient.
O (8 cells): the same cells on OH/PA: C1 (Spearman, Kendall: no replicates; Pearson: replicates) and P1; targets
   recomputed for OH/PA (docs/audits/ohpa_correlation_targets.json, --prepare, committed before the run).
A (8 cells): Round 36 cells on OH/PA: A3 (Feldt with the effective n of the total score); targets from the file.
Acceptance: coverage >= .86 in every cell of the problem (P1 over P and O; C1 per method over O; A3 over A).
Failed fits count as non-coverage.

    --prepare               write the OH/PA targets (commit before the run)
    --smoke-draws N         1..50 draws per cell; no files
    --criterion-commit SHA  the full run (2,000 draws per cell)
"""
import argparse
import hashlib
import json
import subprocess
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'scripts'))
import numpy as np  # noqa: E402

from census import index_core as ic  # noqa: E402
from census import rank_methods as rm  # noqa: E402
from census import small_spatial_core as ssc  # noqa: E402
from census.partial_neff_core import partial_neff  # noqa: E402
from census.simulation import make_replicates  # noqa: E402
from spatial_hac_validation import simulation_setup, haversine_matrix  # noqa: E402
import rank_validation as RKV  # noqa: E402
import index_validation as IXV  # noqa: E402

SEED = 20280501
DRAWS = 2000
CHUNK = 100
GEO = {'miny': 'docs/audits/im_acs_beta_star.json', 'ohpa': 'docs/audits/ohpa_geometry.json'}
OHPA_TARGETS = 'docs/audits/ohpa_correlation_targets.json'
CELLS = ([('P', dict(geometry='miny', r33_cell=c)) for c in range(8)]
         + [('O', dict(geometry='ohpa', r33_cell=c)) for c in range(8)]
         + [('A', dict(geometry='ohpa', r36_cell=c)) for c in range(8)])
CORR_METHODS = (('spearman', 1), ('kendall', 1), ('pearson', 2))
FROZEN = ('scripts/spatial_correlation_validation.py', 'census/partial_neff_core.py', 'census/small_spatial_core.py',
          'census/rank_methods.py', 'census/index_core.py', 'census/simulation.py', 'scripts/spatial_hac_validation.py',
          'scripts/rank_validation.py', 'scripts/index_validation.py', 'docs/audits/rank_targets.json',
          'docs/audits/spatial_correlation_validation_criterion.md', OHPA_TARGETS, GEO['miny'], GEO['ohpa'])
ERRORS = (ValueError, FloatingPointError, np.linalg.LinAlgError)


def coords(geo):
    c = json.loads((ROOT/GEO[geo]).read_text())['coordinates']
    return np.asarray(c['lon']), np.asarray(c['lat'])


def rank_setup(cell, geo):
    """rank_validation.setup on the given geometry (same seed and draw order)."""
    rho, rel, dist = RKV.CELLS[cell]
    lon, lat = coords(geo)
    rng, L, _ = simulation_setup('linear', dist, haversine_matrix(lon, lat), RKV.SEED+cell)
    n = len(L)
    se = rng.lognormal(0, .5, (n, 4))
    se *= np.sqrt(RKV.LOGVAR*(1-rel)/rel/np.mean(se**2, axis=0))
    urban = (L@rng.standard_normal(n)+rng.standard_normal(n))/np.sqrt(2)
    groups = np.empty(n, int)
    for k, idx in enumerate(np.array_split(np.argsort(urban, kind='stable'), 4)):
        groups[idx] = k
    se[:, 3] *= np.array(RKV.SE_GROUP)[groups]
    return rng, L, se, groups


def index_setup(cell, geo):
    rel, dist, method = IXV.CELLS[cell]
    lon, lat = coords(geo)
    rng, L, _ = simulation_setup('linear', dist, haversine_matrix(lon, lat), IXV.SEED+cell)
    n = len(L)
    se = rng.lognormal(0, .5, (n, 5)); se *= np.sqrt(((1-rel)/rel)/np.mean(se**2, axis=0))
    return rng, L, se


def prepare():
    path = ROOT/OHPA_TARGETS
    if path.exists():
        raise ValueError('refusing to replace committed targets')
    rank_rows, index_rows = [], []
    for cell, (rho, rel, dist) in enumerate(RKV.CELLS):           # rank_validation.prepare_targets, OH/PA setup
        _, _, se, _ = rank_setup(cell, 'ohpa')
        rng = np.random.default_rng(np.random.SeedSequence([RKV.SEED, cell, 400000]))
        n = 400000
        t = np.exp(.5*RKV._iid(rng, rho, n))
        idx = rng.integers(0, len(se), n)
        e = rng.standard_normal((n, 3))
        o = t[:, :3]+e*se[idx, :3]
        sub = rng.choice(n, 40000, replace=False)
        vals = {m: rm.coefficient(o[sub if m == 'kendall' else slice(None), 0], o[sub if m == 'kendall' else slice(None), 1],
                                  m, o[:, 2] if m == 'partial' else None) for m in RKV.METHODS}
        rank_rows.append(dict(cell=cell, rho=rho, reliability=rel, range_km=dist, observed=vals))
        print('rank', cell, vals, flush=True)
    for cell, (rel, dist, method) in enumerate(IXV.CELLS):        # index_validation.prepare_targets, OH/PA setup
        _, _, se = index_setup(cell, 'ohpa')
        rng = np.random.default_rng(np.random.SeedSequence([IXV.SEED, cell, 400000]))
        n = 400000
        t = IXV.true_ind(rng, None, n)
        idx = rng.integers(0, len(se), n)
        obs = t+rng.standard_normal((n, 5))@np.linalg.cholesky(IXV.CORR).T*se[idx]
        m, s = ic.standardize(obs)
        index_rows.append(dict(cell=cell, alpha_observed=ic.cronbach((obs-m)/s)))
        print('index', cell, index_rows[-1], flush=True)
    path.write_text(json.dumps(dict(geometry='ohpa', rank_seed=RKV.SEED, index_seed=IXV.SEED, reference_areas=400000,
                                    rank_rows=rank_rows, index_rows=index_rows), indent=2)+'\n')


@lru_cache(maxsize=None)
def classes(geo):
    lon, lat = coords(geo)
    return ssc.class_index(haversine_matrix(lon, lat))


def targets(geo):
    if geo == 'miny':
        return json.loads((ROOT/'docs/audits/rank_targets.json').read_text())['rows'], None
    t = json.loads((ROOT/OHPA_TARGETS).read_text())
    return t['rank_rows'], t['index_rows']


def corr_draw(rng, cell_par, L, se, rank_t, cls, kind):
    rho = RKV.CELLS[cell_par['r33_cell']][0]; n = len(L)
    t = RKV.truths(rng, L, rho, n)
    o = t+rng.standard_normal((n, 4))*se
    rep = make_replicates(o, se, rng)
    tg = rank_t[cell_par['r33_cell']]['observed']
    rec = {}
    def judge(key, fn, target):
        try:
            r = fn(); rec[key] = bool(r['lower'] <= target <= r['upper'])
        except ERRORS:
            rec[key] = None
    judge('P1', lambda: partial_neff(o[:, 0], o[:, 1], o[:, 2], cls, rep[:, 0], rep[:, 1], rep[:, 2]), tg['partial'])
    if kind == 'P':
        judge('P0', lambda: rm.correlation_interval(o[:, 0], o[:, 1], 'partial', 2, .90, rep[:, 0], rep[:, 1],
                                                    z=o[:, 2], reps_z=rep[:, 2]), tg['partial'])
    else:
        for m, v in CORR_METHODS:
            judge(f'C1_{m}', lambda: ssc.correlation_neff(o[:, 0], o[:, 1], m, cls, v,
                                                          rep[:, 0] if v == 2 else None, rep[:, 1] if v == 2 else None), tg[m])
    return rec


def alpha_draw(rng, cell, L, se, target, cls):
    n = len(L)
    t = IXV.true_ind(rng, L, n)
    obs = t+rng.standard_normal((n, 5))@np.linalg.cholesky(IXV.CORR).T*se
    m, s = ic.standardize(obs); z = (obs-m)/s
    try:
        r = ssc.alpha_neff(z, cls); return {'A3': bool(r['lower'] <= target <= r['upper'])}
    except ERRORS:
        return {'A3': None}


def job(args):
    cell, start, stop = args
    kind, par = CELLS[cell]
    geo = par['geometry']; cls = classes(geo)
    rank_t, index_t = targets(geo)
    if kind == 'A':
        _, L, se = index_setup(par['r36_cell'], geo)
        tgt = index_t[par['r36_cell']]['alpha_observed']
    else:
        _, L, se, _ = rank_setup(par['r33_cell'], geo)
    recs = []
    with warnings.catch_warnings(), np.errstate(all='ignore'):
        warnings.simplefilter('ignore')
        for d in range(start, stop):
            rng = np.random.default_rng([SEED+cell, d])
            recs.append(alpha_draw(rng, cell, L, se, tgt, cls) if kind == 'A' else corr_draw(rng, par, L, se, rank_t, cls, kind))
    return cell, recs


def run(draws, workers, chunk):
    tasks = [(c, s, min(s+chunk, draws)) for c in range(len(CELLS)) for s in range(0, draws, chunk)]
    recs = {c: [] for c in range(len(CELLS))}; t0 = time.time()
    with ProcessPoolExecutor(workers) as ex:
        for cell, rs in ex.map(job, tasks):
            recs[cell].extend(rs)
            print({'cell': cell, 'seconds': round(time.time()-t0)}, flush=True)
    cells = []
    for c, (kind, par) in enumerate(CELLS):
        rs = recs[c]; keys = rs[0].keys()
        cells.append(dict(problem=kind, **par, draws=len(rs),
                          coverage={k: sum(bool(r[k]) for r in rs if r[k] is not None)/len(rs) for k in keys},
                          failed={k: sum(r[k] is None for r in rs) for k in keys}))
    passed = {'P1': bool(all(r['coverage']['P1'] >= .86 for r in cells if r['problem'] in ('P', 'O'))),
              'P0': bool(all(r['coverage']['P0'] >= .86 for r in cells if r['problem'] == 'P')),
              'A3_ohpa': bool(all(r['coverage']['A3'] >= .86 for r in cells if r['problem'] == 'A'))}
    for m, _ in CORR_METHODS:
        passed[f'C1_{m}_ohpa'] = bool(all(r['coverage'][f'C1_{m}'] >= .86 for r in cells if r['problem'] == 'O'))
    return dict(cells=cells, passed=passed)


def validate_pins(commit):
    subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'], cwd=ROOT, check=True)
    for rel in FROZEN:
        if subprocess.check_output(['git', 'show', commit+':'+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
            raise SystemExit('script/design differs from criterion commit: '+rel)


def write_audit(result, commit):
    out = ROOT/'docs/audits/spatial_correlation_validation'
    result.update(criterion_commit=commit, draws_per_cell=DRAWS, seed=SEED,
                  frozen_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FROZEN})
    out.with_suffix('.json').write_text(json.dumps(result, indent=1)+'\n')
    L = ['# Correlations under spatial dependence: validation (Round 59)', '',
         'P: effective-n partial correlations (P1) vs the independent-area interval (P0), MI/NY. O: Round 48 effective-n '
         'correlations (C1) and P1 on OH/PA. A: Round 48 effective-n alpha (A3) on OH/PA. Targets: Round 33/36 '
         'observed-value references (OH/PA recomputed). Pass: coverage >= .86 in every cell of the problem.', '',
         f'Criterion commit: `{commit}`. {DRAWS:,} draws per cell.', '',
         '| Problem | Geometry | Cell | Coverage | Failed |', '| :--- | :--- | ---: | :--- | :--- |']
    for r in result['cells']:
        cell = r.get('r33_cell', r.get('r36_cell'))
        L.append(f"| {r['problem']} | {r['geometry']} | {cell} | " + ', '.join(f'{k} {v:.4f}' for k, v in r['coverage'].items())
                 + ' | ' + ', '.join(f'{k} {v}' for k, v in r['failed'].items() if v) + ' |')
    L += ['', f"Outcomes: `{json.dumps(result['passed'], sort_keys=True)}`.", '']
    out.with_suffix('.md').write_text('\n'.join(L))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--prepare', action='store_true')
    ap.add_argument('--smoke-draws', type=int)
    ap.add_argument('--criterion-commit')
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--chunk', type=int, default=CHUNK)
    a = ap.parse_args()
    if a.prepare:
        prepare(); return
    if a.smoke_draws is not None:
        if not 1 <= a.smoke_draws <= 50:
            ap.error('smoke draws must be 1..50')
        r = run(a.smoke_draws, a.workers, max(1, min(a.chunk, a.smoke_draws)))
        for c in r['cells']:
            print(c)
        print(r['passed'])
        return
    if not a.criterion_commit:
        ap.error('full run requires --criterion-commit')
    validate_pins(a.criterion_commit)
    write_audit(run(DRAWS, a.workers, a.chunk), a.criterion_commit)


if __name__ == '__main__':
    main()
