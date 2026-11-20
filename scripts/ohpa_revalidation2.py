# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 54: OH/PA re-check of the Round 45/46/53 spatial designs and IM with G = 4, 6 within-state clusters.

    --prepare               write docs/audits/im_cluster_counts_geometry.json; commit it before the run
    --smoke-draws N         1..50 draws per cell; no files
    --criterion-commit SHA  the full run (2,000 draws per cell)

C (24 cells): Round 30 C1 cells (scripts/im_acs_validation.py setup/outcome) on MI/NY and OH/PA; naive IM with
   G = 4, 6 (within-state cluster_points, 2 / 3 per state) and 8 (the Round 30 / Round 44 assignments) on the
   same draw; target the observed-estimate beta* of each geometry.
K (4): Round 45 K2 on OH/PA (median E 10/30 x range 0/100): NB2 (K2a) and Poisson (K2b) IM-8 counts.
S (8): Round 53 S on OH/PA: S1 rc_im, S0 naive im_counts.
M (12): G1/G2 with p = 3, 4, 5 on OH/PA (Round 53 M generator, PA indicator).
Acceptance: coverage >= .86 in every cell of the problem, per procedure (C per G over both geometries).
Failed fits count as non-coverage.
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

from census import im_clusters_core as imc  # noqa: E402
from census import spatial_eiv_core as se  # noqa: E402
from census.count_repairs_core import im_counts  # noqa: E402
from census.im_acs import constant_columns  # noqa: E402
from census.rc_spatial_core import rc_im  # noqa: E402
from census.simulation import make_replicates  # noqa: E402
from spatial_hac_validation import simulation_setup, simulation_draw, haversine_matrix  # noqa: E402
import im_acs_validation as r30  # noqa: E402

SEED = 20271201
DRAWS = 2000
CHUNK = 100
N_OHPA = 155
GEO = {'miny': 'docs/audits/im_acs_beta_star.json', 'ohpa': 'docs/audits/ohpa_geometry.json'}
COUNTS = 'docs/audits/im_cluster_counts_geometry.json'
STATES = {'miny': ('26', '36'), 'ohpa': ('39', '42')}
GS = (4, 6, 8)
CELLS = ([('C', dict(geometry=g, r30_cell=c)) for g in ('miny', 'ohpa') for c in range(len(r30.CELLS))]
         + [('K', dict(median=m, range_km=d)) for m in (10, 30) for d in (0, 100)]
         + [('S', dict(model=m, reliability=r, range_km=d)) for m in ('poisson', 'negbin') for r in (.9, .7) for d in (0, 100)]
         + [('M', dict(p=p, reliability=r, range_km=d)) for p in (3, 4, 5) for r in (.9, .7) for d in (0, 100)])
FROZEN = ('scripts/ohpa_revalidation2.py', 'census/im_clusters_core.py', 'census/im_acs.py', 'census/rc_spatial_core.py',
          'census/count_repairs_core.py', 'census/models.py', 'census/spatial_eiv_core.py', 'census/simulation.py',
          'scripts/spatial_hac_validation.py', 'scripts/im_acs_validation.py',
          'docs/audits/ohpa_revalidation2_criterion.md', GEO['miny'], GEO['ohpa'], COUNTS)
ERRORS = (ValueError, np.linalg.LinAlgError, RuntimeError, KeyError, FloatingPointError)


def prepare():
    from census.spatial_clusters import cluster_points
    path = ROOT/COUNTS
    if path.exists():
        raise ValueError('refusing to replace the committed geometry')
    out = {}
    for geo, rel in GEO.items():
        g = json.loads((ROOT/rel).read_text()); c = g['coordinates']
        coords = pd.DataFrame(dict(GEOID=c['GEOID'], lon=c['lon'], lat=c['lat']))
        out[geo] = {}
        for G in (4, 6):
            labels = np.empty(len(coords), int)
            for s, st in enumerate(STATES[geo]):
                idx = np.flatnonzero(coords.GEOID.str.startswith(st).to_numpy())
                labels[idx] = cluster_points(coords.iloc[idx].reset_index(drop=True), G//2)+G//2*s
            assert np.bincount(labels).min() >= 5 and len(np.unique(labels)) == G
            out[geo][str(G)] = dict(zip(coords.GEOID, map(int, labels)))
    path.write_text(json.dumps(dict(method='cluster_points (seed 20261126) within each state, G/2 clusters per state',
                                    assignments=out), indent=1, sort_keys=True)+'\n')


def geometry(geo):
    g = json.loads((ROOT/GEO[geo]).read_text()); c = g['coordinates']; ids = c['GEOID']
    extra = json.loads((ROOT/COUNTS).read_text())['assignments'][geo]
    labels = {8: np.array([g['assignment'][i] for i in ids])}
    labels.update({G: np.array([extra[str(G)][i] for i in ids]) for G in (4, 6)})
    state = np.array([float(i.startswith(STATES[geo][1])) for i in ids])
    return g, c, labels, state


def c_draws(cell, start, stop):
    _, par = CELLS[cell]
    g, coords, labels, state = geometry(par['geometry'])
    rc = par['r30_cell']; model = r30.CELLS[rc][0]
    _, L, trials, exposure, sev = r30.setup(rc, coords)      # cell constants of Round 30 (rng discarded)
    target = g['rows'][rc]['beta_star']
    out = {f'IM{G}': [0, 0, []] for G in GS}
    for draw in range(start, stop):
        rng = np.random.default_rng([SEED+cell, draw])
        base, old_y = simulation_draw('linear', L, None, rng)
        x1 = base[:, 1]; error = old_y-1-.5*x1
        true = np.column_stack((x1, .5*x1+np.sqrt(.75)*(L@rng.standard_normal(len(L)))))
        z = rng.standard_normal((len(L), 2))
        observed = true+np.column_stack((z[:, 0], .3*z[:, 0]+np.sqrt(.91)*z[:, 1]))*sev
        y = r30.outcome(model, true, state, error, rng, trials, exposure)
        X = np.column_stack((np.ones(len(L)), observed, state))
        for G in GS:
            key = f'IM{G}'
            try:
                keep, _ = constant_columns(X, labels[G], ['Intercept', 'x1', 'x2', 'state'])
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore')
                    s = imc.summarize(imc.cluster_coefficients(X[:, keep], y, labels[G], model, trials=trials,
                                                               exposure=exposure))
                lo, hi = s['lower'][1], s['upper'][1]
                if not np.isfinite([lo, hi]).all():
                    raise ValueError('nonfinite interval')
                out[key][0] += lo <= target <= hi; out[key][2].append(float(hi-lo))
            except ERRORS:
                out[key][1] += 1
    return out


def k_draws(cell, start, stop):
    _, par = CELLS[cell]
    _, c, labels, state = geometry('ohpa')
    fixed, L, _ = simulation_setup('linear', par['range_km'], haversine_matrix(np.asarray(c['lon']), np.asarray(c['lat'])), SEED+cell)
    n = len(L)
    E = np.maximum(1, np.rint(fixed.lognormal(np.log(par['median']), 1, n)))
    out = dict(K2a=[0, 0, []], K2b=[0, 0, []])
    for draw in range(start, stop):
        rng = np.random.default_rng([SEED+cell, draw])
        x = L@rng.standard_normal(n); u = .3*(L@rng.standard_normal(n))
        y = rng.poisson(E*np.exp(.3*x+.2*state+u)*rng.gamma(4., .25, n)).astype(float)
        X = np.column_stack((np.ones(n), x, state))
        for key, fam in (('K2a', 'negbin'), ('K2b', 'poisson')):
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore')
                    r = im_counts(y, X, E, labels[8], fam)
                if not np.isfinite([r['lower'], r['upper']]).all():
                    raise ValueError('nonfinite interval')
                out[key][0] += r['lower'] <= .3 <= r['upper']; out[key][2].append(float(r['estimate']))
            except ERRORS:
                out[key][1] += 1
    return out


def s_draws(cell, start, stop):
    _, par = CELLS[cell]
    _, c, labels, state = geometry('ohpa')
    model, rel = par['model'], par['reliability']
    fixed, L, _ = simulation_setup('linear', par['range_km'], haversine_matrix(np.asarray(c['lon']), np.asarray(c['lat'])), SEED+cell)
    n = len(L)
    sev = fixed.lognormal(0, .5, (n, 2)); sev *= np.sqrt(((1-rel)/rel)/np.mean(sev**2, axis=0))
    E = np.maximum(1, np.rint(fixed.lognormal(np.log(30), 1, n)))
    out = dict(S1=[0, 0, []], S0=[0, 0, []])
    for draw in range(start, stop):
        rng = np.random.default_rng([SEED+cell, draw])
        x1 = L@rng.standard_normal(n); x2 = .5*x1+np.sqrt(.75)*(L@rng.standard_normal(n))
        w = np.column_stack((x1, x2))+rng.standard_normal((n, 2))*sev
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
                    r = (rc_im(y, w, se_hat, state[:, None], E, labels[8], model) if key == 'S1'
                         else im_counts(y, np.column_stack((np.ones(n), w, state)), E, labels[8], model))
                if not np.isfinite([r['lower'], r['upper']]).all():
                    raise ValueError('nonfinite interval')
                out[key][0] += r['lower'] <= .3 <= r['upper']; out[key][2].append(float(r['estimate']))
            except ERRORS:
                out[key][1] += 1
    return out


def m_draws(cell, start, stop):
    _, par = CELLS[cell]
    _, c, labels, state = geometry('ohpa')
    p, rel = par['p'], par['reliability']
    lon, lat = np.asarray(c['lon']), np.asarray(c['lat'])
    fixed, L, _ = simulation_setup('linear', par['range_km'], haversine_matrix(lon, lat), SEED+cell)
    n = len(L)
    sx = fixed.lognormal(0, .5, (n, p)); sx *= np.sqrt(((1-rel)/rel)/np.mean(sx**2, axis=0))
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
                    r = se.im_summary(se.g1(obs, y, Dx, e, labels[8])); lo, hi, est = r['lower'][0], r['upper'][0], r['estimate'][0]
                if not np.isfinite([lo, hi]).all():
                    raise ValueError('nonfinite interval')
                out[key][0] += lo <= .5 <= hi; out[key][2].append(float(est))
            except ERRORS:
                out[key][1] += 1
    return out


def job(args):
    cell, start, stop = args
    fn = dict(C=c_draws, K=k_draws, S=s_draws, M=m_draws)[CELLS[cell][0]]
    return cell, fn(cell, start, stop)


def run(draws, workers, chunk):
    tasks = [(c, s, min(s+chunk, draws)) for c in range(len(CELLS)) for s in range(0, draws, chunk)]
    acc = {}; t0 = time.time()
    with ProcessPoolExecutor(workers) as ex:
        for cell, out in ex.map(job, tasks):
            a = acc.setdefault(cell, {k: [0, 0, []] for k in out})
            for k, (cv, f, xs) in out.items():
                a[k][0] += cv; a[k][1] += f; a[k][2] += xs
            print({'cell': cell, 'seconds': round(time.time()-t0)}, flush=True)
    target = dict(K=.3, S=.3, M=.5)
    cells = []
    for c, (kind, par) in enumerate(CELLS):
        a = acc[c]
        row = dict(problem=kind, **par, coverage={k: v[0]/draws for k, v in a.items()}, failed={k: v[1] for k, v in a.items()})
        if kind == 'C':
            rc = par['r30_cell']; row.update(model=r30.CELLS[rc][0], range_km=r30.CELLS[rc][1], reliability=r30.CELLS[rc][2])
            row['mean_width'] = {k: (float(np.mean(v[2])) if v[2] else None) for k, v in a.items()}
        else:
            row['bias'] = {k: (float(np.mean(v[2])-target[kind]) if v[2] else None) for k, v in a.items()}
        cells.append(row)
    passed = {}
    def mark(key, ok):
        passed[key] = bool(passed.get(key, True) and ok)
    for r in cells:
        if r['problem'] == 'C':
            for G in GS:
                mark(f'IM{G}', r['coverage'][f'IM{G}'] >= .86)
                mark(f'IM{G}_{r["geometry"]}', r['coverage'][f'IM{G}'] >= .86)
        elif r['problem'] == 'K':
            mark('K2a', r['coverage']['K2a'] >= .86); mark('K2b', r['coverage']['K2b'] >= .86)
        elif r['problem'] == 'S':
            mark(f"S1_{r['model']}", r['coverage']['S1'] >= .86)
        else:
            for k in ('G1', 'G2'):
                mark(f"{k}_p{r['p']}", r['coverage'][k] >= .86)
    return dict(cells=cells, passed=passed)


def validate_pins(commit):
    subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'], cwd=ROOT, check=True)
    for rel in FROZEN:
        if subprocess.check_output(['git', 'show', commit+':'+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
            raise SystemExit('script/design differs from criterion commit: '+rel)


def write_audit(result, commit):
    out = ROOT/'docs/audits/ohpa_revalidation2'
    result.update(criterion_commit=commit, draws_per_cell=DRAWS, seed=SEED,
                  frozen_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FROZEN})
    out.with_suffix('.json').write_text(json.dumps(result, indent=1)+'\n')
    L = ['# OH/PA external validity, part 2, and IM with 4/6 clusters: validation (Round 54)', '',
         'C: naive IM (observed-estimate target) with G = 4, 6 (within-state) and 8 clusters on MI/NY and OH/PA. '
         'K: Round 45 IM-8 counts on OH/PA. S: Round 53 calibrated IM-8 counts on OH/PA. M: G1/G2 with 3-5 '
         'error-prone covariates on OH/PA. Pass: coverage >= .86 in every cell of the problem.', '',
         f'Criterion commit: `{commit}`. {DRAWS:,} draws per cell.', '',
         '## C: naive IM by cluster count', '',
         '| Geometry | Model | Range km | Reliability | IM4 | IM6 | IM8 | Mean width IM4 / IM6 / IM8 |',
         '| :--- | :--- | ---: | ---: | ---: | ---: | ---: | :--- |']
    for r in result['cells']:
        if r['problem'] == 'C':
            w = ' / '.join('—' if r['mean_width'][f'IM{G}'] is None else f"{r['mean_width'][f'IM{G}']:.3f}" for G in GS)
            L.append(f"| {r['geometry']} | {r['model']} | {r['range_km']} | {r['reliability']} | "
                     + ' | '.join(f"{r['coverage'][f'IM{G}']:.4f}" for G in GS) + f' | {w} |')
    L += ['', '## K, S, M on OH/PA', '', '| Problem | Setting | Coverage | Bias | Failed |', '| :--- | :--- | :--- | :--- | :--- |']
    for r in result['cells']:
        if r['problem'] == 'C':
            continue
        setting = ', '.join(f'{k} {v}' for k, v in r.items() if k not in ('problem', 'coverage', 'failed', 'bias'))
        L.append(f"| {r['problem']} | {setting} | " + ', '.join(f'{k} {v:.4f}' for k, v in r['coverage'].items()) + ' | '
                 + ', '.join(f'{k} {v:+.4f}' if v is not None else f'{k} —' for k, v in r['bias'].items()) + ' | '
                 + ', '.join(f'{k} {v}' for k, v in r['failed'].items()) + ' |')
    L += ['', f"Outcomes: `{json.dumps(result['passed'], sort_keys=True)}`.", '']
    out.with_suffix('.md').write_text('\n'.join(L))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--prepare', action='store_true')
    ap.add_argument('--smoke-draws', type=int)
    ap.add_argument('--criterion-commit')
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--chunk', type=int, default=CHUNK, help='draws per task (seeds are per draw; results do not depend on it)')
    a = ap.parse_args()
    if a.prepare:
        prepare(); return
    if a.smoke_draws is not None:
        if not 1 <= a.smoke_draws <= 50:
            ap.error('smoke draws must be 1..50')
        r = run(a.smoke_draws, a.workers, max(1, min(a.chunk, a.smoke_draws)))
        for c in r['cells']:
            print({k: v for k, v in c.items() if k != 'mean_width'})
        print(r['passed'])
        return
    if not a.criterion_commit:
        ap.error('full run requires --criterion-commit')
    validate_pins(a.criterion_commit)
    write_audit(run(DRAWS, a.workers, a.chunk), a.criterion_commit)


if __name__ == '__main__':
    main()
