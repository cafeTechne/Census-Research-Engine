# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 63: interrupted series below 20 points and spatial EIV with six to eight error-prone covariates (frozen with
the criterion).

I (6 cells): Round 48/55 generator (its_design, interruption at n//2 + 1, AR(1) errors, level change 1, slope change
   .2), n in {15, 17, 19} x phi in {.3, .6}. I3 (Round 55, comparison), I6 (conservative critical values), I7
   (bootstrap-bias-corrected AR coefficient). Validated down to the smallest n with both changes >= .86 for both
   phi there and at every larger tested n.
G (24 cells): G1/G2 with p in {6, 7, 8} x reliability {.8, .9} x geometry {MI/NY, OH/PA} x range {0, 100} km; Round
   58 G generator (state indicator, fixed eight clusters); target .5. Validated for p when >= .86 in every cell for p.
Failed fits count as non-coverage. Per-draw seeds [20280801 + cell, draw].

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
from scipy import stats  # noqa: E402

from census import its_small_core as isc  # noqa: E402
from census import mci_core as mi  # noqa: E402
from census import spatial_eiv_core as se  # noqa: E402
from census.simulation import make_replicates  # noqa: E402
from spatial_hac_validation import simulation_setup, simulation_draw, haversine_matrix  # noqa: E402
import spatial_outside_validation as r58  # noqa: E402

SEED = 20280801
DRAWS = 2000
CELLS = ([('I', dict(n=n, phi=phi)) for n in (15, 17, 19) for phi in (.3, .6)]
         + [('G', dict(p=p, reliability=r, geometry=g, range_km=d)) for p in (6, 7, 8) for r in (.8, .9)
            for g in ('miny', 'ohpa') for d in (0, 100)])
FROZEN = ('scripts/small_many_validation.py', 'census/its_small_core.py', 'census/small_spatial_core.py',
          'census/mci_core.py', 'census/spatial_eiv_core.py', 'census/simulation.py', 'scripts/spatial_hac_validation.py',
          'scripts/spatial_outside_validation.py', 'docs/audits/im_acs_beta_star.json', 'docs/audits/ohpa_geometry.json',
          'docs/audits/small_many_validation_criterion.md')
ERRORS = (ValueError, np.linalg.LinAlgError, FloatingPointError, RuntimeError)


def i_draws(cell, start, stop):
    par = CELLS[cell][1]; n, phi = par['n'], par['phi']
    X = mi.its_design(n, n//2+1)
    out = {k: [0, 0, 0] for k in ('I3', 'I6', 'I7')}
    for d in range(start, stop):
        rng = np.random.default_rng([SEED+cell, d])
        e = rng.standard_normal(n); u = np.empty(n); u[0] = e[0]/np.sqrt(1-phi**2)
        for t in range(1, n):
            u[t] = phi*u[t-1]+e[t]
        y = X @ np.array([0., 0., 1., .2])+u
        for key in out:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore')
                    fn = {'I3': isc.its_bootstrap_t_bc, 'I6': isc.its_bootstrap_t_cons, 'I7': isc.its_bootstrap_t_bb}[key]
                    res = fn(y, X, rng)[0]
                out[key][0] += res[0]['lower'] <= 1. <= res[0]['upper']
                out[key][1] += res[1]['lower'] <= .2 <= res[1]['upper']
            except ERRORS:
                out[key][2] += 1
    return out


def g_draws(cell, start, stop):
    par = CELLS[cell][1]
    _, c, labels, state = r58.geometry(par['geometry'])
    p, rel = par['p'], par['reliability']
    lon, lat = np.asarray(c['lon']), np.asarray(c['lat'])
    fixed, L, _ = simulation_setup('linear', par['range_km'], haversine_matrix(lon, lat), SEED+cell)
    n = len(L)
    sx = fixed.lognormal(0, .5, (n, p)); sx *= np.sqrt(((1-rel)/rel)/np.mean(sx**2, axis=0))
    sy = fixed.lognormal(0, .5, n); sy *= np.sqrt(.2/np.mean(sy**2))
    Wk = se.knn_weights(lon, lat, 6); eig = np.linalg.eigvals(Wk)
    out = dict(G1=[0, 0, 0], G2=[0, 0, 0])
    for d in range(start, stop):
        rng = np.random.default_rng([SEED+cell, d])
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
                    crit = stats.t.ppf(.95, n-X.shape[1]); s = np.sqrt(V[1, 1]); lo, hi = b[1]-crit*s, b[1]+crit*s
                else:
                    r = se.im_summary(se.g1(obs, y, Dx, e, labels)); lo, hi = r['lower'][0], r['upper'][0]
                if not np.isfinite([lo, hi]).all():
                    raise ValueError('nonfinite interval')
                out[key][0] += lo <= .5 <= hi
            except ERRORS:
                out[key][2] += 1
    return out


def job(args):
    cell, start, stop = args
    return cell, (i_draws if CELLS[cell][0] == 'I' else g_draws)(cell, start, stop)


def run(draws, workers, chunk):
    tasks = [(c, s, min(s+chunk, draws)) for c in range(len(CELLS)) for s in range(0, draws, chunk)]
    tasks.sort(key=lambda t: CELLS[t[0]][0] != 'I')
    acc = {}; t0 = time.time()
    with ProcessPoolExecutor(workers) as ex:
        for cell, out in ex.map(job, tasks):
            a = acc.setdefault(cell, {k: [0, 0, 0] for k in out})
            for k, v in out.items():
                for i in range(3):
                    a[k][i] += v[i]
            print({'cell': cell, 'seconds': round(time.time()-t0)}, flush=True)
    cells = []
    for c, (kind, par) in enumerate(CELLS):
        a = acc[c]
        if kind == 'I':
            cells.append(dict(problem='I', **par, coverage={k: dict(level=v[0]/draws, slope=v[1]/draws) for k, v in a.items()},
                              failed={k: v[2] for k, v in a.items()}))
        else:
            cells.append(dict(problem='G', **par, coverage={k: v[0]/draws for k, v in a.items()}, failed={k: v[2] for k, v in a.items()}))
    passed = {}
    for key in ('I3', 'I6', 'I7'):
        ok_n = {n: all(min(r['coverage'][key].values()) >= .86 for r in cells if r['problem'] == 'I' and r['n'] == n)
                for n in (15, 17, 19)}
        min_n = None
        for n in (19, 17, 15):
            if ok_n[n]:
                min_n = n
            else:
                break
        passed[f'{key}_min_n'] = min_n
    for key in ('G1', 'G2'):
        cap = 5
        for p in (6, 7, 8):
            if all(r['coverage'][key] >= .86 for r in cells if r['problem'] == 'G' and r['p'] == p):
                cap = p
            else:
                break
        passed[f'{key}_gated_cap'] = cap
        for p in (6, 7, 8):
            passed[f'{key}_p{p}'] = bool(all(r['coverage'][key] >= .86 for r in cells if r['problem'] == 'G' and r['p'] == p))
    return dict(cells=cells, passed=passed)


def validate_pins(commit):
    subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'], cwd=ROOT, check=True)
    for rel in FROZEN:
        if subprocess.check_output(['git', 'show', commit+':'+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
            raise SystemExit('script/design differs from criterion commit: '+rel)


def write_audit(result, commit):
    out = ROOT/'docs/audits/small_many_validation'
    result.update(criterion_commit=commit, draws_per_cell=DRAWS, seed=SEED,
                  frozen_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FROZEN})
    out.with_suffix('.json').write_text(json.dumps(result, indent=1)+'\n')
    L = ['# Small samples and many covariates: validation (Round 63)', '',
         'I: interrupted series at 15-19 points; I3 Round 55 (comparison), I6 conservative critical values, I7 '
         'bootstrap-bias-corrected AR coefficient. G: G1/G2 with six to eight error-prone covariates at reliability '
         '.8 and .9 on MI/NY and OH/PA. Pass: coverage >= .86 in every cell (I: smallest n with every larger n).', '',
         f'Criterion commit: `{commit}`. {DRAWS:,} draws per cell.', '',
         '| n | phi | I3 level / slope | I6 level / slope | I7 level / slope | Failed (I3/I6/I7) |', '| ---: | ---: | :--- | :--- | :--- | :--- |']
    for r in result['cells']:
        if r['problem'] == 'I':
            cv = ' | '.join(f"{r['coverage'][k]['level']:.4f} / {r['coverage'][k]['slope']:.4f}" for k in ('I3', 'I6', 'I7'))
            L.append(f"| {r['n']} | {r['phi']} | {cv} | {r['failed']['I3']}/{r['failed']['I6']}/{r['failed']['I7']} |")
    L += ['', '| p | Reliability | Geometry | Range km | G1 | G2 | Failed (G1/G2) |', '| ---: | ---: | :--- | ---: | ---: | ---: | :--- |']
    for r in result['cells']:
        if r['problem'] == 'G':
            L.append(f"| {r['p']} | {r['reliability']} | {r['geometry']} | {r['range_km']} | {r['coverage']['G1']:.4f} | "
                     f"{r['coverage']['G2']:.4f} | {r['failed']['G1']}/{r['failed']['G2']} |")
    L += ['', f"Outcomes: `{json.dumps(result['passed'], sort_keys=True)}`.", '']
    out.with_suffix('.md').write_text('\n'.join(L))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--smoke-draws', type=int)
    ap.add_argument('--criterion-commit')
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--chunk', type=int, default=50)
    a = ap.parse_args()
    if a.smoke_draws is not None:
        if not 1 <= a.smoke_draws <= 50:
            ap.error('smoke draws must be 1..50')
        r = run(a.smoke_draws, a.workers, max(1, min(a.chunk, a.smoke_draws)))
        print(json.dumps(r['passed']))
        return
    if not a.criterion_commit:
        ap.error('full run requires --criterion-commit')
    validate_pins(a.criterion_commit)
    write_audit(run(DRAWS, a.workers, a.chunk), a.criterion_commit)


if __name__ == '__main__':
    main()
