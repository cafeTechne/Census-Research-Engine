# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 44: re-run the Round 30 (IM-8, C1) and Round 35 (G1/G2) validation designs on OH/PA counties.

    --prepare               write docs/audits/ohpa_geometry.json (geometry, assignment, C1 targets); commit it
    --smoke-draws N         1..20 draws per cell; no files
    --criterion-commit SHA  the full run (2,000 draws per cell)

The cell generators, reference procedure, seeds and criterion are the Round 30 and Round 35 ones
(imported from their frozen scripts); only the geometry and the state indicator (PA) change.
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
import statsmodels.api as sm
from scipy import stats
from census import spatial_eiv_core as se
from census.im_acs import constant_columns, cluster_coefficients, summarize
from census.simulation import make_replicates
from spatial_hac_validation import simulation_setup, simulation_draw, haversine_matrix
import im_acs_validation as r30
import spatial_eiv_validation as r35

GEOMETRY = 'docs/audits/ohpa_geometry.json'
DRAWS = 2000
STATES = ('39', '42')
FROZEN = ('scripts/ohpa_spatial_revalidation.py', 'scripts/im_acs_validation.py', 'scripts/spatial_eiv_validation.py',
          'census/im_acs.py', 'census/spatial_eiv_core.py', 'census/simulation.py', 'scripts/spatial_hac_validation.py',
          'docs/audits/ohpa_revalidation_criterion.md', GEOMETRY)
JOBS = [('C1', c) for c in range(len(r30.CELLS))]+[('G', c) for c in range(len(r35.CELLS))]


def prepare():
    path = ROOT/GEOMETRY
    if path.exists():
        raise ValueError('refusing to replace the committed geometry')
    import pandas as pd
    from census.boundaries import get_boundaries
    from census.spatial_clusters import cluster_points
    from census.spatial_hac import unit_coordinates
    with patch('requests.sessions.Session.request', side_effect=RuntimeError('Round 44 uses cached boundaries only')):
        ids = sorted(g for st in STATES for g in get_boundaries('county', 2020, st).GEOID.astype(str))
        if len(ids) != 155:
            raise ValueError(f'expected 155 cached OH/PA counties, got {len(ids)}')
        coords, provenance = unit_coordinates(ids, 'county', 2020)
    coords = coords.reset_index(drop=True)
    labels = np.empty(len(coords), int)
    for s, st in enumerate(STATES):                     # state-respecting: 4 clusters within each state
        idx = np.flatnonzero(coords.GEOID.str.startswith(st).to_numpy())
        labels[idx] = cluster_points(coords.iloc[idx].reset_index(drop=True), 4)+4*s
    state = coords.GEOID.str.startswith('42').to_numpy(float)
    assert all(len(set(state[labels == g])) == 1 for g in range(8)) and np.bincount(labels).min() >= 5
    records = []
    for cell, (model, distance, reliability) in enumerate(r30.CELLS):   # the Round 30 reference procedure
        _, _, trials, exposure, sev = r30.setup(cell, coords)
        rng = np.random.default_rng(np.random.SeedSequence([r30.SEED, cell, 400000, 7]))
        n = 400000
        index = rng.integers(0, len(coords), n)
        z = rng.standard_normal((n, 2)); true = np.column_stack((z[:, 0], .5*z[:, 0]+np.sqrt(.75)*z[:, 1]))
        e = rng.standard_normal((n, 2)); u = np.column_stack((e[:, 0], .3*e[:, 0]+np.sqrt(.91)*e[:, 1]))*sev[index]
        observed = true+u; st_ = state[index]
        tr = None if trials is None else trials[index]; ex = None if exposure is None else exposure[index]
        y = r30.outcome(model, true, st_, rng.standard_normal(n), rng, tr, ex)
        X = np.column_stack((np.ones(n), observed, st_))
        if model == 'linear':
            beta = np.linalg.lstsq(X, y, rcond=None)[0][1]
            sigma = np.array([[1, .5], [.5, 1.]])
            ec = np.array([[np.mean(sev[:, 0]**2), .3*np.mean(sev[:, 0]*sev[:, 1])],
                           [.3*np.mean(sev[:, 0]*sev[:, 1]), np.mean(sev[:, 1]**2)]])
            closed = np.linalg.solve(sigma+ec, sigma@np.array([.5, .5]))[0]
            if abs(beta-closed) > .005:
                raise ValueError('reference linear target differs from closed form by >.005')
        else:
            kw = ({'family': sm.families.Binomial(), 'var_weights': tr} if model == 'binomial' else
                  {'family': sm.families.Poisson(), 'offset': np.log(ex)})
            fit = sm.GLM(y, X, **kw).fit()
            if not fit.converged:
                raise ValueError('reference GLM did not converge')
            beta = fit.params[1]; closed = None
        records.append(dict(cell=cell, model=model, range_km=distance, reliability=reliability, beta_star=float(beta),
                            closed_form=None if closed is None else float(closed), reference_n=n))
        print('reference', cell, model, distance, reliability, float(beta), flush=True)
    value = dict(seed=r30.SEED, rows=records, coordinates=coords[['GEOID', 'lon', 'lat']].to_dict('list'),
                 assignment=dict(zip(coords.GEOID.astype(str), map(int, labels))),
                 geometry='cached 2020 cartographic county boundaries (OH 39, PA 42), unit_coordinates representative '
                          'points; cluster_points k=4 within each state (seed 20261126); state indicator PA',
                 boundary_provenance=json.loads(json.dumps(provenance, default=str)))
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def geometry():
    g = json.loads((ROOT/GEOMETRY).read_text())
    ids = g['coordinates']['GEOID']
    return g, np.array([g['assignment'][i] for i in ids]), np.array([float(i.startswith('42')) for i in ids])


def c1_cell(cell, draws):
    """Round 30 C1 loop (im_acs_validation.run) for one cell; C2 (failed in Round 30) is not re-run."""
    g, labels, state = geometry(); coords = g['coordinates']
    model, distance, reliability = r30.CELLS[cell]
    rng, L, trials, exposure, sev = r30.setup(cell, coords)
    target = g['rows'][cell]['beta_star']; true_beta = .5 if model == 'linear' else .3
    v = dict(cover=0, true_cover=0, failed=0, widths=[], null_reject=0, null_failed=0)
    for draw in range(draws):
        base, old_y = simulation_draw('linear', L, None, rng)
        x1 = base[:, 1]; error = old_y-1-.5*x1
        true = np.column_stack((x1, .5*x1+np.sqrt(.75)*(L@rng.standard_normal(len(L)))))
        z = rng.standard_normal((len(L), 2))
        u = np.column_stack((z[:, 0], .3*z[:, 0]+np.sqrt(.91)*z[:, 1]))*sev
        observed = true+u
        y = r30.outcome(model, true, state, error, rng, trials, exposure)
        aux = np.random.default_rng(np.random.SeedSequence([r30.SEED, cell, draw, 7]))
        make_replicates(observed, sev, aux, corr=np.array([[1., .3], [.3, 1.]]))   # keeps the aux stream as in Round 30
        X = np.column_stack((np.ones(len(L)), observed, state))
        keep, _ = constant_columns(X, labels, ['Intercept', 'x1', 'x2', 'PA'])
        try:
            b = cluster_coefficients(X[:, keep], y, labels, model, trials=trials, exposure=exposure, covariance=None)
            s = summarize(b); lo, hi = s['lower'][1], s['upper'][1]
            if not np.isfinite([lo, hi]).all():
                raise ValueError('nonfinite interval')
            v['cover'] += int(lo <= target <= hi); v['true_cover'] += int(lo <= true_beta <= hi); v['widths'].append(float(hi-lo))
        except (ValueError, RuntimeError, np.linalg.LinAlgError, FloatingPointError):
            v['failed'] += 1
        null_y = r30.outcome(model, true, state, error, aux, trials, exposure, null=True, single=True)
        try:
            s = summarize(cluster_coefficients(X[:, [0, 1]], null_y, labels, model, trials=trials, exposure=exposure,
                                               covariance=None))
            v['null_reject'] += int(stats.t.sf(s['estimate'][1]/s['se'][1], 7) < .05)
        except (ValueError, RuntimeError, np.linalg.LinAlgError, FloatingPointError):
            v['null_failed'] += 1
    cov = v['cover']/draws
    return dict(design='C1', cell=cell, model=model, range_km=distance, reliability=reliability, draws=draws, target=target,
                coverage=cov, mc_se=float(np.sqrt(cov*(1-cov)/draws)), coverage_true_beta=v['true_cover']/draws,
                failed_draws=v['failed'], mean_width=float(np.mean(v['widths'])) if v['widths'] else None,
                null_one_sided_size=v['null_reject']/draws, null_failed_draws=v['null_failed'])


def g_cell(cell, draws):
    """Round 35 loop (spatial_eiv_validation.run_cell) for one cell on the OH/PA geometry."""
    g, labels, state = geometry(); c = g['coordinates']
    lon, lat = np.asarray(c['lon']), np.asarray(c['lat'])
    rel, dist, rho_e = r35.CELLS[cell]
    rng, L, _ = simulation_setup('linear', dist, haversine_matrix(lon, lat), r35.SEED+cell)
    n = len(L)
    sx = rng.lognormal(0, .5, (n, 2)); sx *= np.sqrt(((1-rel)/rel)/np.mean(sx**2, axis=0))
    sy = rng.lognormal(0, .5, n); sy *= np.sqrt(.2/np.mean(sy**2))
    W = se.knn_weights(lon, lat, 6); eig = np.linalg.eigvals(W)
    corr = np.array([[1, .3, rho_e], [.3, 1, 0], [rho_e, 0, 1.]])
    out = {k: dict(cover=0, failed=0, est=[], width=[]) for k in ('G1', 'G2', 'C1_naive')}
    lams = []
    for draw in range(draws):
        base, old_y = simulation_draw('linear', L, None, rng)
        x1 = base[:, 1]; err = old_y-1-.5*x1
        true = np.column_stack((x1, .5*x1+np.sqrt(.75)*(L@rng.standard_normal(n))))
        z = rng.standard_normal((n, 3))@np.linalg.cholesky(corr).T
        u = z[:, :2]*sx; ey = z[:, 2]*sy
        obs = true+u
        y = 1+r35.BETA*true[:, 0]+r35.BETA*true[:, 1]+.3*state+err+ey
        aux = np.random.default_rng(np.random.SeedSequence([r35.SEED, cell, draw, 7]))
        rep = make_replicates(np.column_stack((obs, y)), np.column_stack((sx, sy)), aux, corr=corr)
        dev = rep-np.column_stack((obs, y))[:, :, None]
        Dx = np.transpose(dev[:, :2, :], (2, 0, 1)); e = dev[:, 2, :].T
        X = np.column_stack((np.ones(n), obs, state))
        D = np.concatenate((np.zeros((80, n, 1)), Dx, np.zeros((80, n, 1))), axis=2)
        for key in out:
            try:
                if key == 'G2':
                    b, V, lam = se.g2(X, y, D, e, W, eig); lams.append(lam)
                    crit = stats.t.ppf(.95, n-X.shape[1]); s = np.sqrt(V[1, 1])
                    lo, hi, est = b[1]-crit*s, b[1]+crit*s, b[1]
                elif key == 'G1':
                    r = se.im_summary(se.g1(obs, y, Dx, e, labels)); lo, hi, est = r['lower'][0], r['upper'][0], r['estimate'][0]
                else:
                    r = se.im_summary(se.g1(obs, y, np.zeros_like(Dx), np.zeros_like(e), labels))
                    lo, hi, est = r['lower'][0], r['upper'][0], r['estimate'][0]
                if not np.isfinite([lo, hi]).all():
                    raise ValueError('nonfinite interval')
                out[key]['cover'] += lo <= r35.BETA <= hi; out[key]['est'].append(est); out[key]['width'].append(hi-lo)
            except (ValueError, np.linalg.LinAlgError):
                out[key]['failed'] += 1
    return dict(design='G', cell=cell, reliability=rel, range_km=dist, error_corr=rho_e, draws=draws,
                coverage={k: v['cover']/draws for k, v in out.items()}, failed={k: v['failed'] for k, v in out.items()},
                bias={k: float(np.mean(v['est'])-r35.BETA) if v['est'] else None for k, v in out.items()},
                width={k: float(np.mean(v['width'])) if v['width'] else None for k, v in out.items()},
                mean_lambda=float(np.mean(lams)) if lams else None)


def job(args):
    kind, cell, draws = args
    start = time.time()
    row = c1_cell(cell, draws) if kind == 'C1' else g_cell(cell, draws)
    row['seconds'] = time.time()-start
    print({k: row[k] for k in row if k in ('design', 'cell', 'model', 'coverage', 'failed_draws', 'failed', 'seconds')}, flush=True)
    return row


def run(draws, workers):
    with Pool(workers) as pool:
        rows = pool.map(job, [(k, c, draws) for k, c in JOBS])
    c1 = [r for r in rows if r['design'] == 'C1']; g = [r for r in rows if r['design'] == 'G']
    passed = {'C1': {m: all(r['coverage'] >= .86 for r in c1 if r['model'] == m) for m in ('linear', 'binomial', 'poisson')},
              'G1': all(r['coverage']['G1'] >= .86 for r in g), 'G2': all(r['coverage']['G2'] >= .86 for r in g)}
    return dict(rows=rows, passed=passed, draws_per_cell=draws,
                criterion='as Rounds 30 and 35: 90% coverage >= .86 in every cell, per candidate (C1 per model); '
                          'failed fits count as non-coverage; C1 target is the recomputed observed-estimate beta*, '
                          'G1/G2 target the true slope 0.5; C1_naive and null sizes informational')


def validate_pins(commit):
    subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'], cwd=ROOT, check=True)
    for rel in FROZEN:
        if subprocess.check_output(['git', 'show', commit+':'+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
            raise ValueError('script/design differs from criterion commit: '+rel)


def write_audit(result, commit):
    out = ROOT/'docs/audits/ohpa_revalidation'
    result['criterion_commit'] = commit
    result['frozen_sha256'] = {rel: hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() for rel in FROZEN}
    out.with_suffix('.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    lines = ['# OH/PA re-check of the Round 30 and Round 35 spatial validations (Round 44)', '', result['criterion']+'.', '',
             f"Criterion commit: `{commit}`. {result['draws_per_cell']:,} draws per cell; 155 OH/PA counties, "
             "state-respecting eight-cluster assignment.", '',
             '## C1 (IM-8, observed-estimate target)', '',
             '| Model | Range km | Reliability | beta* | Coverage | Failed | Null size (.05) |', '| :--- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for r in result['rows']:
        if r['design'] == 'C1':
            lines.append(f"| {r['model']} | {r['range_km']} | {r['reliability']} | {r['target']:.4f} | {r['coverage']:.4f} | "
                         f"{r['failed_draws']} | {r['null_one_sided_size']:.4f} |")
    lines += ['', '## G1/G2 (corrected slopes, target 0.5)', '',
              '| Reliability | Range km | Error corr | G1 | G2 | C1_naive | Failed (G1/G2) | Mean lambda |',
              '| ---: | ---: | ---: | ---: | ---: | ---: | :--- | ---: |']
    for r in result['rows']:
        if r['design'] == 'G':
            c = r['coverage']
            lines.append(f"| {r['reliability']} | {r['range_km']} | {r['error_corr']} | {c['G1']:.4f} | {c['G2']:.4f} | "
                         f"{c['C1_naive']:.4f} | {r['failed']['G1']}/{r['failed']['G2']} | {r['mean_lambda']:.3f} |")
    lines += ['', 'Outcomes: `'+json.dumps(result['passed'], sort_keys=True)+'`.']
    out.with_suffix('.md').write_text('\n'.join(lines)+'\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepare', action='store_true'); p.add_argument('--smoke-draws', type=int)
    p.add_argument('--criterion-commit'); p.add_argument('--workers', type=int, default=6)
    a = p.parse_args()
    if a.prepare:
        prepare(); return
    if a.smoke_draws is not None:
        if not 1 <= a.smoke_draws <= 20:
            p.error('smoke draws must be 1..20')
        run(a.smoke_draws, a.workers); return
    if not a.criterion_commit:
        p.error('full run requires --criterion-commit')
    validate_pins(a.criterion_commit)
    if (ROOT/'docs/audits/ohpa_revalidation.json').exists():
        p.error('refusing to overwrite the full audit')
    write_audit(run(DRAWS, a.workers), a.criterion_commit)


if __name__ == '__main__':
    main()
