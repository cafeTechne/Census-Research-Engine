# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fixed Round 53 validation: RC jackknife SEs (J), RC with IM-8 count slopes (S), G1/G2 with 5-6 error-prone
covariates (M). Frozen with the criterion.

J: Round 46's R generator (145 independent areas; x1, x2 ~ N(0, 1) corr .5; lognormal error SEs scaled to the
   reliability; replicate-estimated SEs; binomial (trials median 3,900, logit -2.6 + .3x1 + .3x2 + .15e),
   Poisson (E median 30, log-rate .3x1 + .3x2 + .15e) or NB2 (Gamma(4) noise)). J1 = engine
   regression_calibration(se_method="jackknife"). Target .3.
S: MI/NY geometry, fixed IM-8 assignment; x1 = L z1, x2 = .5 x1 + sqrt(.75) L z2 (Round 22 field; range 0 or
   100 km); error SEs as J; E lognormal median 30; log-rate .3x1 + .3x2 + .3 NY + .15 L z3, NB2 times Gamma(4).
   S1 = rc_im (pooled calibration + Round 45 IM-8 counts); S0 = im_counts on the observed W (comparison).
   Target .3.
M: Round 46's M generator with p in {5, 6}; G1 and G2 (frozen spatial_eiv_core). Target .5.

Acceptance: coverage >= .86 in every cell of the problem, per procedure and model (or p). Failed fits count
as non-coverage.

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
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'scripts'))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402
from scipy.special import expit  # noqa: E402

from census import spatial_eiv_core as se  # noqa: E402
from census.count_repairs_core import im_counts  # noqa: E402
from census.models import regression_calibration  # noqa: E402
from census.rc_spatial_core import rc_im  # noqa: E402
from census.simulation import make_replicates  # noqa: E402
from spatial_hac_validation import simulation_setup, simulation_draw, haversine_matrix  # noqa: E402

SEED = 20271101
DRAWS = 2000
CHUNK = 100
N = 145
GEOMETRY = 'docs/audits/im_acs_beta_star.json'
CELLS = ([('J', dict(model=m, reliability=r, error_corr=c)) for m in ('binomial', 'poisson', 'negbin')
          for r in (.9, .7) for c in (0., .3)]
         + [('S', dict(model=m, reliability=r, range_km=d)) for m in ('poisson', 'negbin') for r in (.9, .7)
            for d in (0, 100)]
         + [('M', dict(p=p, reliability=r, range_km=d)) for p in (5, 6) for r in (.9, .7) for d in (0, 100)])
FROZEN = ('scripts/glm_correction2_validation.py', 'census/models.py', 'census/rc_spatial_core.py',
          'census/count_repairs_core.py', 'census/spatial_eiv_core.py', 'census/simulation.py',
          'scripts/spatial_hac_validation.py', 'docs/audits/glm_correction2_validation_criterion.md', GEOMETRY)
ERRORS = (ValueError, np.linalg.LinAlgError, RuntimeError, KeyError, FloatingPointError)


def geometry():
    g = json.loads((ROOT/GEOMETRY).read_text())
    c = g['coordinates']; ids = c['GEOID']
    return (np.asarray(c['lon']), np.asarray(c['lat']), np.array([g['assignment'][i] for i in ids]),
            np.array([float(i.startswith('36')) for i in ids]))


def error_sds(rng, n, k, rel):
    s = rng.lognormal(0, .5, (n, k))
    return s*np.sqrt(((1-rel)/rel)/np.mean(s**2, axis=0))


def j_draws(cell, start, stop):
    _, par = CELLS[cell]
    model, rel, rho = par['model'], par['reliability'], par['error_corr']
    fixed = np.random.default_rng(SEED+cell)
    sev = error_sds(fixed, N, 2, rel)
    trials = np.maximum(50, np.rint(fixed.lognormal(np.log(3900), 1, N))) if model == 'binomial' else None
    E = np.maximum(1, np.rint(fixed.lognormal(np.log(30), 1, N))) if model != 'binomial' else None
    Cx = np.linalg.cholesky(np.array([[1, .5], [.5, 1.]])); Cu = np.array([[1, rho], [rho, 1.]])
    ids = [f"{i:05d}" for i in range(N)]
    out = dict(J1=[0, 0, []])   # cover, failed, estimates
    for draw in range(start, stop):
        rng = np.random.default_rng([SEED+cell, draw])
        x = rng.standard_normal((N, 2))@Cx.T
        w = x+(rng.standard_normal((N, 2))@np.linalg.cholesky(Cu).T)*sev
        rep = make_replicates(w, sev, rng, corr=Cu)
        se_hat = np.sqrt(.05*np.sum((rep-w[:, :, None])**2, axis=2))
        if model == 'binomial':
            y = rng.binomial(trials.astype(int), expit(-2.6+.3*x[:, 0]+.3*x[:, 1]+.15*rng.standard_normal(N)))/trials
        elif model == 'poisson':
            y = rng.poisson(E*np.exp(.3*x[:, 0]+.3*x[:, 1]+.15*rng.standard_normal(N))).astype(float)
        else:
            y = rng.poisson(E*np.exp(.3*x[:, 0]+.3*x[:, 1])*rng.gamma(4., .25, N)).astype(float)
        f = pd.DataFrame(dict(GEOID=ids, Year=2022, y=y, w1=w[:, 0], w2=w[:, 1], w1_se=se_hat[:, 0], w2_se=se_hat[:, 1]))
        extra = dict(trials='T') if model == 'binomial' else dict(exposure='E')
        f['T' if model == 'binomial' else 'E'] = trials if model == 'binomial' else E
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                r = regression_calibration('y ~ w1 + w2', f, ['w1', 'w2'], model=model, se_method='jackknife', **extra)
            row = r.coefficients.set_index('term').loc['w1']
            if not np.isfinite([row.ci_lower, row.ci_upper]).all():
                raise ValueError('nonfinite interval')
            out['J1'][0] += row.ci_lower <= .3 <= row.ci_upper; out['J1'][2].append(float(row.estimate))
        except ERRORS:
            out['J1'][1] += 1
    return out


def s_draws(cell, start, stop):
    _, par = CELLS[cell]
    model, rel, dist = par['model'], par['reliability'], par['range_km']
    lon, lat, labels, state = geometry()
    fixed, L, _ = simulation_setup('linear', dist, haversine_matrix(lon, lat), SEED+cell)
    n = len(L)
    sev = error_sds(fixed, n, 2, rel)
    E = np.maximum(1, np.rint(fixed.lognormal(np.log(30), 1, n)))
    out = dict(S1=[0, 0, []], S0=[0, 0, []])
    for draw in range(start, stop):
        rng = np.random.default_rng([SEED+cell, draw])
        x1 = L@rng.standard_normal(n); x2 = .5*x1+np.sqrt(.75)*(L@rng.standard_normal(n))
        x = np.column_stack((x1, x2))
        w = x+rng.standard_normal((n, 2))*sev
        rep = make_replicates(w, sev, rng)
        se_hat = np.sqrt(.05*np.sum((rep-w[:, :, None])**2, axis=2))
        mu = E*np.exp(.3*x1+.3*x2+.3*state+.15*(L@rng.standard_normal(n)))
        if model == 'negbin':
            mu = mu*rng.gamma(4., .25, n)
        y = rng.poisson(mu).astype(float)
        for key in out:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore')
                    if key == 'S1':
                        r = rc_im(y, w, se_hat, state[:, None], E, labels, model)
                    else:
                        r = im_counts(y, np.column_stack((np.ones(n), w, state)), E, labels, model)
                lo, hi, b = r['lower'], r['upper'], r['estimate']
                if not np.isfinite([lo, hi]).all():
                    raise ValueError('nonfinite interval')
                out[key][0] += lo <= .3 <= hi; out[key][2].append(float(b))
            except ERRORS:
                out[key][1] += 1
    return out


def m_draws(cell, start, stop):
    _, par = CELLS[cell]
    p, rel, dist = par['p'], par['reliability'], par['range_km']
    lon, lat, labels, state = geometry()
    fixed, L, _ = simulation_setup('linear', dist, haversine_matrix(lon, lat), SEED+cell)
    n = len(L)
    sx = error_sds(fixed, n, p, rel)
    sy = fixed.lognormal(0, .5, n); sy *= np.sqrt(.2/np.mean(sy**2))
    W = se.knn_weights(lon, lat, 6); eig = np.linalg.eigvals(W)
    out = dict(G1=[0, 0, []], G2=[0, 0, []])
    for draw in range(start, stop):
        rng = np.random.default_rng([SEED+cell, draw])
        base, old_y = simulation_draw('linear', L, None, rng)
        x1 = base[:, 1]; err = old_y-1-.5*x1
        true = np.column_stack([x1]+[.5*x1+np.sqrt(.75)*(L@rng.standard_normal(n)) for _ in range(p-1)])
        obs = true+rng.standard_normal((n, p))*sx
        y = 1+.5*true.sum(axis=1)+.3*state+err+rng.standard_normal(n)*sy
        rep = make_replicates(np.column_stack((obs, y)), np.column_stack((sx, sy)), rng)
        dev = rep-np.column_stack((obs, y))[:, :, None]
        Dx = np.transpose(dev[:, :p, :], (2, 0, 1)); e = dev[:, p, :].T
        X = np.column_stack((np.ones(n), obs, state))
        D = np.concatenate((np.zeros((80, n, 1)), Dx, np.zeros((80, n, 1))), axis=2)
        for key in out:
            try:
                if key == 'G2':
                    b, V, _ = se.g2(X, y, D, e, W, eig)
                    crit = stats.t.ppf(.95, n-X.shape[1]); s = np.sqrt(V[1, 1]); lo, hi, est = b[1]-crit*s, b[1]+crit*s, b[1]
                else:
                    r = se.im_summary(se.g1(obs, y, Dx, e, labels)); lo, hi, est = r['lower'][0], r['upper'][0], r['estimate'][0]
                if not np.isfinite([lo, hi]).all():
                    raise ValueError('nonfinite interval')
                out[key][0] += lo <= .5 <= hi; out[key][2].append(float(est))
            except ERRORS:
                out[key][1] += 1
    return out


def job(args):
    cell, start, stop = args
    fn = dict(J=j_draws, S=s_draws, M=m_draws)[CELLS[cell][0]]
    return cell, fn(cell, start, stop)


def run(draws, workers, chunk):
    tasks = [(c, s, min(s+chunk, draws)) for c in range(len(CELLS)) for s in range(0, draws, chunk)]
    acc = {}
    t0 = time.time()
    with ProcessPoolExecutor(workers) as ex:
        for cell, out in ex.map(job, tasks):
            a = acc.setdefault(cell, {k: [0, 0, []] for k in out})
            for k, (c, f, est) in out.items():
                a[k][0] += c; a[k][1] += f; a[k][2] += est
            print({'cell': cell, 'seconds': round(time.time()-t0)}, flush=True)
    cells = []
    target = dict(J=.3, S=.3, M=.5)
    for c, (kind, par) in enumerate(CELLS):
        a = acc[c]
        cells.append(dict(problem=kind, **par, coverage={k: v[0]/draws for k, v in a.items()},
                          failed={k: v[1] for k, v in a.items()},
                          bias={k: (float(np.mean(v[2])-target[kind]) if v[2] else None) for k, v in a.items()}))
    passed = {}
    for cell in cells:
        if cell['problem'] == 'J':
            key = f"J1_{cell['model']}"
        elif cell['problem'] == 'S':
            key = f"S1_{cell['model']}"
        else:
            for proc in ('G1', 'G2'):
                k = f"{proc}_p{cell['p']}"; passed[k] = bool(passed.get(k, True) and cell['coverage'][proc] >= .86)
            continue
        passed[key] = bool(passed.get(key, True) and cell['coverage'][key[:2]] >= .86)
    return dict(cells=cells, passed=passed)


def validate_pins(commit):
    subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'], cwd=ROOT, check=True)
    for rel in FROZEN:
        if subprocess.check_output(['git', 'show', commit+':'+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
            raise SystemExit('script/design differs from criterion commit: '+rel)


def write_audit(result, commit):
    out = ROOT/'docs/audits/glm_correction2_validation'
    result.update(criterion_commit=commit, draws_per_cell=DRAWS, seed=SEED,
                  frozen_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FROZEN})
    out.with_suffix('.json').write_text(json.dumps(result, indent=1)+'\n')
    L = ['# Corrected GLM slopes, part 2: validation (Round 53)', '',
         'J: regression calibration with delete-one-area jackknife SEs (t, n - p df), independent areas, Round 46 '
         'generator. S: pooled calibration + IM-8 per-cluster Poisson/NB2 slopes (S1) vs naive IM-8 (S0), MI/NY '
         'spatial fields. M: G1/G2 with five and six error-prone covariates. Pass: coverage >= .86 in every cell.', '',
         f'Criterion commit: `{commit}`. {DRAWS:,} draws per cell.', '',
         '| Problem | Setting | Coverage | Bias | Failed |', '| :--- | :--- | :--- | :--- | :--- |']
    for c in result['cells']:
        setting = ', '.join(f'{k} {v}' for k, v in c.items() if k not in ('problem', 'coverage', 'failed', 'bias'))
        cov = ', '.join(f'{k} {v:.4f}' for k, v in c['coverage'].items())
        bias = ', '.join(f'{k} {v:+.4f}' if v is not None else f'{k} —' for k, v in c['bias'].items())
        fail = ', '.join(f'{k} {v}' for k, v in c['failed'].items())
        L.append(f"| {c['problem']} | {setting} | {cov} | {bias} | {fail} |")
    L += ['', f"Outcomes: `{json.dumps(result['passed'], sort_keys=True)}`.", '']
    out.with_suffix('.md').write_text('\n'.join(L))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--smoke-draws', type=int)
    ap.add_argument('--criterion-commit')
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--chunk', type=int, default=CHUNK, help='draws per task (seeds are per draw; results do not depend on it)')
    a = ap.parse_args()
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
