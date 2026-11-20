# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 58: spatial inference outside MI/NY (frozen with the criterion).

N (24 cells): Round 30 C1 cells (linear/binomial/Poisson x range 0/100 km x reliability .9/.7;
   im_acs_validation setup/outcome) on MI/NY and OH/PA; SCPC (rho_bar .05 and .10) and IM-8 on the same draw;
   target the observed-estimate beta* of each geometry.
R (3 cells, 10,000 draws): MI/NY linear, binomial, Poisson at 100 km, reliability .7: IM-8, SCPC .05, .10.
G (12 cells): G1/G2 with p = 3, 4, 5 error-prone covariates x geometry x range 0/100 at reliability .8 (Round 53/54
   M generator with the state indicator); target .5.
B (4 cells): calibrated binomial slopes with IM-8 (rc_im_binomial), MI/NY, reliability .9/.7 x range 0/100;
   Round 53 S design with a binomial outcome; target .3.
Acceptance: coverage >= .86 in every cell of the problem per procedure (SCPC per rho_bar and model over N and R;
G1/G2 per p over G; B1 over B). Failed fits count as non-coverage.

    --smoke-draws N         1..50 draws per cell; no files
    --criterion-commit SHA  the full run
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
from scipy import stats  # noqa: E402
from scipy.special import expit  # noqa: E402

from census import scpc_core as sc  # noqa: E402
from census import spatial_eiv_core as se  # noqa: E402
from census.im_acs import cluster_coefficients, constant_columns, summarize  # noqa: E402
from census.rc_spatial_core import rc_im_binomial  # noqa: E402
from census.simulation import make_replicates  # noqa: E402
from spatial_hac_validation import simulation_setup, simulation_draw, haversine_matrix  # noqa: E402
import im_acs_validation as r30  # noqa: E402

SEED = 20280401
DRAWS = 2000
R_DRAWS = 10000
CHUNK = 100
GEO = {'miny': 'docs/audits/im_acs_beta_star.json', 'ohpa': 'docs/audits/ohpa_geometry.json'}
STATE2 = {'miny': '36', 'ohpa': '42'}
RHOS = (.05, .10)
CELLS = ([('N', dict(geometry=g, r30_cell=c)) for g in ('miny', 'ohpa') for c in range(len(r30.CELLS))]
         + [('R', dict(geometry='miny', r30_cell=c)) for c in (3, 7, 11)]
         + [('G', dict(p=p, geometry=g, range_km=d)) for p in (3, 4, 5) for g in ('miny', 'ohpa') for d in (0, 100)]
         + [('B', dict(reliability=r, range_km=d)) for r in (.9, .7) for d in (0, 100)])
FROZEN = ('scripts/spatial_outside_validation.py', 'census/scpc_core.py', 'census/rc_spatial_core.py',
          'census/im_clusters_core.py', 'census/im_acs.py', 'census/models.py', 'census/spatial_eiv_core.py',
          'census/simulation.py', 'scripts/spatial_hac_validation.py', 'scripts/im_acs_validation.py',
          'docs/audits/spatial_outside_validation_criterion.md', GEO['miny'], GEO['ohpa'])
ERRORS = (ValueError, np.linalg.LinAlgError, RuntimeError, FloatingPointError)


def draws_for(cell):
    return R_DRAWS if CELLS[cell][0] == 'R' else DRAWS


def geometry(geo):
    g = json.loads((ROOT/GEO[geo]).read_text()); c = g['coordinates']; ids = c['GEOID']
    return (g, c, np.array([g['assignment'][i] for i in ids]),
            np.array([float(i.startswith(STATE2[geo])) for i in ids]))


@lru_cache(maxsize=None)
def scpc_setup(geo, rho):
    _, c, _, _ = geometry(geo)
    return sc.setup(sc.haversine(c['lon'], c['lat']), rho)


def nr_draws(cell, start, stop):
    _, par = CELLS[cell]
    g, coords, labels, state = geometry(par['geometry'])
    rc = par['r30_cell']; model = r30.CELLS[rc][0]
    _, L, trials, exposure, sev = r30.setup(rc, coords)
    target = g['rows'][rc]['beta_star']
    keys = ['IM8']+[f'SCPC{int(100*r):02d}' for r in RHOS]
    out = {k: [0, 0, []] for k in keys}
    S = {r: scpc_setup(par['geometry'], r) for r in RHOS}
    for draw in range(start, stop):
        rng = np.random.default_rng([SEED+cell, draw])
        base, old_y = simulation_draw('linear', L, None, rng)
        x1 = base[:, 1]; error = old_y-1-.5*x1
        true = np.column_stack((x1, .5*x1+np.sqrt(.75)*(L@rng.standard_normal(len(L)))))
        z = rng.standard_normal((len(L), 2))
        observed = true+np.column_stack((z[:, 0], .3*z[:, 0]+np.sqrt(.91)*z[:, 1]))*sev
        y = r30.outcome(model, true, state, error, rng, trials, exposure)
        X = np.column_stack((np.ones(len(L)), observed, state))
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            try:
                keep, _ = constant_columns(X, labels, ['Intercept', 'x1', 'x2', 'state'])
                s = summarize(cluster_coefficients(X[:, keep], y, labels, model, trials=trials, exposure=exposure))
                lo, hi = s['lower'][1], s['upper'][1]
                if not np.isfinite([lo, hi]).all():
                    raise ValueError('nonfinite')
                out['IM8'][0] += lo <= target <= hi; out['IM8'][2].append(float(hi-lo))
            except ERRORS:
                out['IM8'][1] += 1
            try:
                theta, e = sc.influence(X, y, model, 1, trials=trials, exposure=exposure)
                for r in RHOS:
                    k = f'SCPC{int(100*r):02d}'
                    iv = sc.interval(theta, e, S[r])
                    out[k][0] += iv['lower'] <= target <= iv['upper']; out[k][2].append(iv['upper']-iv['lower'])
            except ERRORS:
                for r in RHOS:
                    out[f'SCPC{int(100*r):02d}'][1] += 1
    return out


def g_draws(cell, start, stop):
    _, par = CELLS[cell]
    _, c, labels, state = geometry(par['geometry'])
    p, rel = par['p'], .8
    lon, lat = np.asarray(c['lon']), np.asarray(c['lat'])
    fixed, L, _ = simulation_setup('linear', par['range_km'], haversine_matrix(lon, lat), SEED+cell)
    n = len(L)
    sx = fixed.lognormal(0, .5, (n, p)); sx *= np.sqrt(((1-rel)/rel)/np.mean(sx**2, axis=0))
    sy = fixed.lognormal(0, .5, n); sy *= np.sqrt(.2/np.mean(sy**2))
    Wk = se.knn_weights(lon, lat, 6); eig = np.linalg.eigvals(Wk)
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
                    b, V, _ = se.g2(X, y, D, e, Wk, eig)
                    crit = stats.t.ppf(.95, n-X.shape[1]); s = np.sqrt(V[1, 1]); lo, hi, est = b[1]-crit*s, b[1]+crit*s, b[1]
                else:
                    r = se.im_summary(se.g1(obs, y, Dx, e, labels)); lo, hi, est = r['lower'][0], r['upper'][0], r['estimate'][0]
                if not np.isfinite([lo, hi]).all():
                    raise ValueError('nonfinite interval')
                out[key][0] += lo <= .5 <= hi; out[key][2].append(float(est))
            except ERRORS:
                out[key][1] += 1
    return out


def b_draws(cell, start, stop):
    _, par = CELLS[cell]
    _, c, labels, state = geometry('miny')
    rel = par['reliability']
    fixed, L, _ = simulation_setup('linear', par['range_km'], haversine_matrix(np.asarray(c['lon']), np.asarray(c['lat'])), SEED+cell)
    n = len(L)
    sev = fixed.lognormal(0, .5, (n, 2)); sev *= np.sqrt(((1-rel)/rel)/np.mean(sev**2, axis=0))
    trials = np.maximum(50, np.rint(fixed.lognormal(np.log(3900), 1, n)))
    out = dict(B1=[0, 0, []])
    for draw in range(start, stop):
        rng = np.random.default_rng([SEED+cell, draw])
        x1 = L@rng.standard_normal(n); x2 = .5*x1+np.sqrt(.75)*(L@rng.standard_normal(n))
        w = np.column_stack((x1, x2))+rng.standard_normal((n, 2))*sev
        rep = make_replicates(w, sev, rng)
        se_hat = np.sqrt(.05*np.sum((rep-w[:, :, None])**2, axis=2))
        y = rng.binomial(trials.astype(int), expit(-2.6+.3*x1+.3*x2+.3*state+.15*(L@rng.standard_normal(n))))/trials
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                r = rc_im_binomial(y, w, se_hat, state[:, None], trials, labels)
            if not np.isfinite([r['lower'], r['upper']]).all():
                raise ValueError('nonfinite')
            out['B1'][0] += r['lower'] <= .3 <= r['upper']; out['B1'][2].append(r['estimate'])
        except ERRORS:
            out['B1'][1] += 1
    return out


def job(args):
    cell, start, stop = args
    kind = CELLS[cell][0]
    fn = nr_draws if kind in ('N', 'R') else g_draws if kind == 'G' else b_draws
    return cell, fn(cell, start, stop)


def run(scale, workers, chunk):
    tasks = []
    for c in range(len(CELLS)):
        n = max(1, int(round(draws_for(c)*scale)))
        tasks += [(c, s, min(s+chunk, n)) for s in range(0, n, chunk)]
    acc = {}; t0 = time.time()
    with ProcessPoolExecutor(workers) as ex:
        for cell, out in ex.map(job, tasks):
            a = acc.setdefault(cell, {k: [0, 0, []] for k in out})
            for k, (cv, f, xs) in out.items():
                a[k][0] += cv; a[k][1] += f; a[k][2] += xs
            print({'cell': cell, 'seconds': round(time.time()-t0)}, flush=True)
    cells = []
    for c, (kind, par) in enumerate(CELLS):
        n = max(1, int(round(draws_for(c)*scale))); a = acc[c]
        row = dict(problem=kind, **par, draws=n, coverage={k: v[0]/n for k, v in a.items()}, failed={k: v[1] for k, v in a.items()})
        if kind in ('N', 'R'):
            rc = par['r30_cell']; row.update(model=r30.CELLS[rc][0], range_km=r30.CELLS[rc][1], reliability=r30.CELLS[rc][2])
            row['mean_width'] = {k: (float(np.mean(v[2])) if v[2] else None) for k, v in a.items()}
        else:
            row['bias'] = {k: (float(np.mean(v[2])-(.5 if kind == 'G' else .3)) if v[2] else None) for k, v in a.items()}
        cells.append(row)
    passed = {}
    def mark(key, ok):
        passed[key] = bool(passed.get(key, True) and ok)
    for r in cells:
        if r['problem'] in ('N', 'R'):
            for k in r['coverage']:
                if k.startswith('SCPC'):
                    mark(f"{k}_{r['model']}", r['coverage'][k] >= .86)
            if r['problem'] == 'R':
                mark(f"IM8_R_{r['model']}", r['coverage']['IM8'] >= .86)
        elif r['problem'] == 'G':
            for k in ('G1', 'G2'):
                mark(f"{k}_p{r['p']}_rel80", r['coverage'][k] >= .86)
        else:
            mark('B1_binomial', r['coverage']['B1'] >= .86)
    return dict(cells=cells, passed=passed)


def validate_pins(commit):
    subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'], cwd=ROOT, check=True)
    for rel in FROZEN:
        if subprocess.check_output(['git', 'show', commit+':'+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
            raise SystemExit('script/design differs from criterion commit: '+rel)


def write_audit(result, commit):
    out = ROOT/'docs/audits/spatial_outside_validation'
    result.update(criterion_commit=commit, draws_per_cell=DRAWS, r_draws=R_DRAWS, seed=SEED,
                  frozen_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FROZEN},
                  scpc={geo: {str(r): dict(q=scpc_setup(geo, r)['q'], cv=scpc_setup(geo, r)['cv'],
                                            benchmark_range_km=1/scpc_setup(geo, r)['c0']) for r in RHOS} for geo in GEO})
    out.with_suffix('.json').write_text(json.dumps(result, indent=1)+'\n')
    L = ['# Spatial inference outside MI/NY: validation (Round 58)', '',
         'N/R: naive (observed-estimate) slopes with SCPC (rho_bar .05, .10) and IM-8 on MI/NY and OH/PA; R cells '
         '10,000 draws. G: G1/G2 with three to five error-prone covariates at reliability .8. B: calibrated binomial '
         'slopes with IM-8. Pass: coverage >= .86 in every cell of the problem.', '',
         f'Criterion commit: `{commit}`.', '',
         '| Geometry | rho_bar | q | Critical value | Benchmark range (km) |', '| :--- | ---: | ---: | ---: | ---: |']
    for geo, d in result['scpc'].items():
        for rho, v in d.items():
            L.append(f"| {geo} | {rho} | {v['q']} | {v['cv']:.3f} | {v['benchmark_range_km']:.1f} |")
    L += ['', '| Problem | Geometry | Model | Range | Reliability | Draws | IM8 | SCPC05 | SCPC10 | Width IM8 / SCPC05 / SCPC10 |',
          '| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | :--- |']
    for r in result['cells']:
        if r['problem'] in ('N', 'R'):
            w = ' / '.join('—' if r['mean_width'][k] is None else f"{r['mean_width'][k]:.3f}" for k in ('IM8', 'SCPC05', 'SCPC10'))
            L.append(f"| {r['problem']} | {r['geometry']} | {r['model']} | {r['range_km']} | {r['reliability']} | {r['draws']} | "
                     + ' | '.join(f"{r['coverage'][k]:.4f}" for k in ('IM8', 'SCPC05', 'SCPC10')) + f' | {w} |')
    L += ['', '| Problem | Setting | Coverage | Bias | Failed |', '| :--- | :--- | :--- | :--- | :--- |']
    for r in result['cells']:
        if r['problem'] in ('G', 'B'):
            setting = ', '.join(f'{k} {v}' for k, v in r.items() if k not in ('problem', 'coverage', 'failed', 'bias', 'draws'))
            L.append(f"| {r['problem']} | {setting} | " + ', '.join(f'{k} {v:.4f}' for k, v in r['coverage'].items()) + ' | '
                     + ', '.join(f'{k} {v:+.4f}' if v is not None else f'{k} —' for k, v in r['bias'].items()) + ' | '
                     + ', '.join(f'{k} {v}' for k, v in r['failed'].items()) + ' |')
    L += ['', f"Outcomes: `{json.dumps(result['passed'], sort_keys=True)}`.", '']
    out.with_suffix('.md').write_text('\n'.join(L))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--smoke-draws', type=int)
    ap.add_argument('--criterion-commit')
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--chunk', type=int, default=CHUNK, help='draws per task (seeds are per draw)')
    a = ap.parse_args()
    if a.smoke_draws is not None:
        if not 1 <= a.smoke_draws <= 50:
            ap.error('smoke draws must be 1..50')
        r = run(a.smoke_draws/DRAWS, a.workers, max(1, min(a.chunk, a.smoke_draws)))
        for c in r['cells']:
            print({k: v for k, v in c.items() if k != 'mean_width'})
        print(r['passed'])
        return
    if not a.criterion_commit:
        ap.error('full run requires --criterion-commit')
    validate_pins(a.criterion_commit)
    write_audit(run(1., a.workers, a.chunk), a.criterion_commit)


if __name__ == '__main__':
    main()
