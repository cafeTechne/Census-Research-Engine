# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fixed Round 46 validation: GLM regression calibration (R) and spatial EIV with 3-4 error-prone covariates (M).

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
import pandas as pd
from scipy import stats
from scipy.special import expit
from census import spatial_eiv_core as se
from census.count_models import fit_count_model
from census.models import fit_replicate, regression_calibration
from census.simulation import make_replicates
from spatial_hac_validation import simulation_setup, simulation_draw, haversine_matrix

SEED = 20270401
DRAWS = 2000
N = 145
GEOMETRY = 'docs/audits/im_acs_beta_star.json'
CELLS = ([('R', dict(model=m, reliability=r, error_corr=c)) for m in ('binomial', 'poisson', 'negbin')
          for r in (.9, .7) for c in (0., .3)]
         + [('M', dict(p=p, reliability=r, range_km=d)) for p in (3, 4) for r in (.9, .7) for d in (0, 100)])
FROZEN = ('scripts/glm_correction_validation.py', 'census/models.py', 'census/count_models.py',
          'census/manova_counts_core.py', 'census/spatial_eiv_core.py', 'census/simulation.py',
          'scripts/spatial_hac_validation.py', 'docs/audits/glm_correction_validation_criterion.md', GEOMETRY)


def r_cell(cell, draws):
    _, par = CELLS[cell]
    model, rel, rho = par['model'], par['reliability'], par['error_corr']
    rng = np.random.default_rng(SEED+cell)
    sev = rng.lognormal(0, .5, (N, 2)); sev *= np.sqrt(((1-rel)/rel)/np.mean(sev**2, axis=0))
    trials = np.maximum(50, np.rint(rng.lognormal(np.log(3900), 1, N))) if model == 'binomial' else None
    E = np.maximum(1, np.rint(rng.lognormal(np.log(30), 1, N))) if model != 'binomial' else None
    Cx = np.linalg.cholesky(np.array([[1, .5], [.5, 1.]])); Cu = np.array([[1, rho], [rho, 1.]])
    cov = {'R0': 0, 'R1': 0}; fails = {'R0': 0, 'R1': 0}; est = {'R0': [], 'R1': []}
    ids = [f"{i:05d}" for i in range(N)]
    for draw in range(draws):
        x = rng.standard_normal((N, 2))@Cx.T
        u = (rng.standard_normal((N, 2))@np.linalg.cholesky(Cu).T)*sev
        w = x+u
        aux = np.random.default_rng(np.random.SeedSequence([SEED, cell, draw, 7]))
        rep = make_replicates(w, sev, aux, corr=Cu)
        se_hat = np.sqrt(.05*np.sum((rep-w[:, :, None])**2, axis=2))
        if model == 'binomial':
            y = rng.binomial(trials.astype(int), expit(-2.6+.3*x[:, 0]+.3*x[:, 1]+.15*rng.standard_normal(N)))/trials
        elif model == 'poisson':
            y = rng.poisson(E*np.exp(.3*x[:, 0]+.3*x[:, 1]+.15*rng.standard_normal(N))).astype(float)
        else:
            y = rng.poisson(E*np.exp(.3*x[:, 0]+.3*x[:, 1])*rng.gamma(4., .25, N)).astype(float)
        f = pd.DataFrame(dict(GEOID=ids, Year=2022, y=y, w1=w[:, 0], w2=w[:, 1], w1_se=se_hat[:, 0], w2_se=se_hat[:, 1]))
        extra = {}
        if model == 'binomial':
            f['T'] = trials; extra = dict(trials='T')
        else:
            f['E'] = E; extra = dict(exposure='E')
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            for key in ('R0', 'R1'):
                try:
                    if key == 'R1':
                        r = regression_calibration('y ~ w1 + w2', f, ['w1', 'w2'], model=model, seed=draw, **extra)
                        row = r.coefficients.set_index('term').loc['w1']; lo, hi, b = row.ci_lower, row.ci_upper, row.estimate
                    elif model == 'negbin':
                        t = fit_count_model('y ~ w1 + w2', f, 'E')['table'].set_index('term').loc['w1']
                        lo, hi, b = t.lower, t.upper, t.estimate
                    else:
                        r = fit_replicate('y ~ w1 + w2', f, model=model, scale='robust', target='population', **extra)
                        row = r.coefficients.set_index('term').loc['w1']; lo, hi, b = row.ci_lower, row.ci_upper, row.estimate
                    if not np.isfinite([lo, hi]).all():
                        raise ValueError('nonfinite interval')
                    cov[key] += lo <= .3 <= hi; est[key].append(b)
                except (ValueError, np.linalg.LinAlgError, RuntimeError, KeyError):
                    fails[key] += 1
    return dict(coverage={k: v/draws for k, v in cov.items()}, failed=fails,
                bias={k: float(np.mean(v)-.3) if v else None for k, v in est.items()})


def geometry():
    g = json.loads((ROOT/GEOMETRY).read_text())
    c = g['coordinates']; ids = c['GEOID']
    return (np.asarray(c['lon']), np.asarray(c['lat']), np.array([g['assignment'][i] for i in ids]),
            np.array([float(i.startswith('36')) for i in ids]))


def m_cell(cell, draws):
    _, par = CELLS[cell]
    p, rel, dist = par['p'], par['reliability'], par['range_km']
    lon, lat, labels, state = geometry()
    rng, L, _ = simulation_setup('linear', dist, haversine_matrix(lon, lat), SEED+cell)
    n = len(L)
    sx = rng.lognormal(0, .5, (n, p)); sx *= np.sqrt(((1-rel)/rel)/np.mean(sx**2, axis=0))
    sy = rng.lognormal(0, .5, n); sy *= np.sqrt(.2/np.mean(sy**2))
    W = se.knn_weights(lon, lat, 6); eig = np.linalg.eigvals(W)
    out = {k: dict(cover=0, failed=0, est=[]) for k in ('G1', 'G2')}
    for draw in range(draws):
        base, old_y = simulation_draw('linear', L, None, rng)
        x1 = base[:, 1]; err = old_y-1-.5*x1
        true = np.column_stack([x1]+[.5*x1+np.sqrt(.75)*(L@rng.standard_normal(n)) for _ in range(p-1)])
        u = rng.standard_normal((n, p))*sx; ey = rng.standard_normal(n)*sy
        obs = true+u
        y = 1+.5*true.sum(axis=1)+.3*state+err+ey
        aux = np.random.default_rng(np.random.SeedSequence([SEED, cell, draw, 7]))
        rep = make_replicates(np.column_stack((obs, y)), np.column_stack((sx, sy)), aux)
        dev = rep-np.column_stack((obs, y))[:, :, None]
        Dx = np.transpose(dev[:, :p, :], (2, 0, 1)); e = dev[:, p, :].T
        X = np.column_stack((np.ones(n), obs, state))
        D = np.concatenate((np.zeros((80, n, 1)), Dx, np.zeros((80, n, 1))), axis=2)
        for key in out:
            try:
                if key == 'G2':
                    b, V, lam = se.g2(X, y, D, e, W, eig)
                    crit = stats.t.ppf(.95, n-X.shape[1]); s = np.sqrt(V[1, 1]); lo, hi, est = b[1]-crit*s, b[1]+crit*s, b[1]
                else:
                    r = se.im_summary(se.g1(obs, y, Dx, e, labels)); lo, hi, est = r['lower'][0], r['upper'][0], r['estimate'][0]
                if not np.isfinite([lo, hi]).all():
                    raise ValueError('nonfinite interval')
                out[key]['cover'] += lo <= .5 <= hi; out[key]['est'].append(est)
            except (ValueError, np.linalg.LinAlgError):
                out[key]['failed'] += 1
    return dict(coverage={k: v['cover']/draws for k, v in out.items()}, failed={k: v['failed'] for k, v in out.items()},
                bias={k: float(np.mean(v['est'])-.5) if v['est'] else None for k, v in out.items()})


def job(args):
    cell, draws = args
    start = time.time()
    kind, par = CELLS[cell]
    row = dict(cell=cell, kind=kind, parameters=par, draws=draws, **(r_cell if kind == 'R' else m_cell)(cell, draws))
    row['seconds'] = time.time()-start
    print(row, flush=True)
    return row


def run(draws, workers):
    order = sorted(range(len(CELLS)), key=lambda c: CELLS[c][0] != 'R')      # long R cells first
    with Pool(workers) as pool:
        rows = sorted(pool.map(job, [(c, draws) for c in order]), key=lambda r: r['cell'])
    passed = {f'R1_{m}': all(r['coverage']['R1'] >= .86 for r in rows if r['kind'] == 'R' and r['parameters']['model'] == m)
              for m in ('binomial', 'poisson', 'negbin')}
    for p in (3, 4):
        for k in ('G1', 'G2'):
            passed[f'{k}_p{p}'] = all(r['coverage'][k] >= .86 for r in rows if r['kind'] == 'M' and r['parameters']['p'] == p)
    return dict(rows=rows, passed=passed, draws_per_cell=draws,
                criterion='90% coverage of the true slope >= .86 in every cell, per procedure (R1 per model; G1/G2 per p); '
                          'failed fits count as non-coverage; R0 is a comparison')


def validate_pins(commit):
    subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'], cwd=ROOT, check=True)
    for rel in FROZEN:
        if subprocess.check_output(['git', 'show', commit+':'+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
            raise ValueError('script/design differs from criterion commit: '+rel)


def write_audit(result, commit):
    out = ROOT/'docs/audits/glm_correction_validation'
    result['criterion_commit'] = commit
    result['frozen_sha256'] = {rel: hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() for rel in FROZEN}
    out.with_suffix('.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    lines = ['# GLM measurement-error correction and EIV with more covariates: validation (Round 46)', '',
             result['criterion']+'.', '', f"Criterion commit: `{commit}`. {result['draws_per_cell']:,} draws per cell.", '',
             '| Problem | Setting | Coverage | Bias | Failed |', '| :--- | :--- | :--- | :--- | :--- |']
    for r in result['rows']:
        lines.append(f"| {r['kind']} | {', '.join(f'{k} {v}' for k, v in r['parameters'].items())} | "
                     + ', '.join(f"{k} {v:.4f}" for k, v in r['coverage'].items()) + ' | '
                     + ', '.join(f"{k} {v:+.4f}" if v is not None else f"{k} -" for k, v in r['bias'].items()) + ' | '
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
    if (ROOT/'docs/audits/glm_correction_validation.json').exists():
        p.error('refusing to overwrite the full audit')
    write_audit(run(DRAWS, a.workers), a.criterion_commit)


if __name__ == '__main__':
    main()
