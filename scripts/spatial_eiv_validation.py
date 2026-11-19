# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fixed Round 35 validation of corrected slope inference under spatial dependence.

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
from scipy import stats
from census import spatial_eiv_core as se
from census.simulation import make_replicates
from spatial_hac_validation import simulation_setup, simulation_draw, haversine_matrix

SEED = 20270114
DRAWS = 2000
CELLS = [(rel, dist, rho_e) for rel in (.9, .7) for dist in (0, 100) for rho_e in (0., .3)]
GEOMETRY = 'docs/audits/im_acs_beta_star.json'
FROZEN = ('scripts/spatial_eiv_validation.py', 'census/spatial_eiv_core.py', 'census/simulation.py',
          'scripts/spatial_hac_validation.py', 'docs/audits/spatial_eiv_validation_criterion.md', GEOMETRY)
BETA = .5


def geometry():
    g = json.loads((ROOT/GEOMETRY).read_text())
    c = g['coordinates']; ids = c['GEOID']
    return (np.asarray(c['lon']), np.asarray(c['lat']), np.array([g['assignment'][i] for i in ids]),
            np.array([float(i.startswith('36')) for i in ids]))


def setup(cell):
    rel, dist, rho_e = CELLS[cell]
    lon, lat, labels, state = geometry()
    rng, L, _ = simulation_setup('linear', dist, haversine_matrix(lon, lat), SEED+cell)
    n = len(L)
    sx = rng.lognormal(0, .5, (n, 2)); sx *= np.sqrt(((1-rel)/rel)/np.mean(sx**2, axis=0))
    sy = rng.lognormal(0, .5, n); sy *= np.sqrt(.2/np.mean(sy**2))
    W = se.knn_weights(lon, lat, 6)
    return rng, L, sx, sy, W, np.linalg.eigvals(W), labels, state


def run_cell(args):
    cell, draws = args
    rel, dist, rho_e = CELLS[cell]
    rng, L, sx, sy, W, eig, labels, state = setup(cell)
    n = len(L)
    corr = np.array([[1, .3, rho_e], [.3, 1, 0], [rho_e, 0, 1.]])
    out = {k: dict(cover=0, failed=0, est=[], width=[]) for k in ('G1', 'G2', 'C1_naive')}
    lams = []
    start = time.time()
    for draw in range(draws):
        base, old_y = simulation_draw('linear', L, None, rng)
        x1 = base[:, 1]; err = old_y-1-.5*x1
        true = np.column_stack((x1, .5*x1+np.sqrt(.75)*(L@rng.standard_normal(n))))
        z = rng.standard_normal((n, 3))
        z = z@np.linalg.cholesky(corr).T
        u = z[:, :2]*sx; ey = z[:, 2]*sy
        obs = true+u
        y = 1+BETA*true[:, 0]+BETA*true[:, 1]+.3*state+err+ey
        aux = np.random.default_rng(np.random.SeedSequence([SEED, cell, draw, 7]))
        rep = make_replicates(np.column_stack((obs, y)), np.column_stack((sx, sy)), aux, corr=corr)
        dev = rep-np.column_stack((obs, y))[:, :, None]                 # n x 3 x 80
        Dx = np.transpose(dev[:, :2, :], (2, 0, 1)); e = dev[:, 2, :].T  # (80, n, 2), (80, n)
        X = np.column_stack((np.ones(n), obs, state))
        D = np.concatenate((np.zeros((80, n, 1)), Dx, np.zeros((80, n, 1))), axis=2)
        for key in out:
            try:
                if key == 'G2':
                    b, V, lam = se.g2(X, y, D, e, W, eig); lams.append(lam)
                    crit = stats.t.ppf(.95, n-X.shape[1]); s = np.sqrt(V[1, 1])
                    lo, hi, est = b[1]-crit*s, b[1]+crit*s, b[1]
                elif key == 'G1':
                    r = se.im_summary(se.g1(obs, y, Dx, e, labels))
                    lo, hi, est = r['lower'][0], r['upper'][0], r['estimate'][0]
                else:
                    naive = se.g1(obs, y, np.zeros_like(Dx), np.zeros_like(e), labels)
                    r = se.im_summary(naive); lo, hi, est = r['lower'][0], r['upper'][0], r['estimate'][0]
                if not np.isfinite([lo, hi]).all():
                    raise ValueError('nonfinite interval')
                out[key]['cover'] += lo <= BETA <= hi; out[key]['est'].append(est); out[key]['width'].append(hi-lo)
            except (ValueError, np.linalg.LinAlgError):
                out[key]['failed'] += 1
    row = dict(cell=cell, reliability=rel, range_km=dist, error_corr=rho_e, draws=draws,
               coverage={k: v['cover']/draws for k, v in out.items()}, failed={k: v['failed'] for k, v in out.items()},
               bias={k: float(np.mean(v['est'])-BETA) if v['est'] else None for k, v in out.items()},
               width={k: float(np.mean(v['width'])) if v['width'] else None for k, v in out.items()},
               mean_lambda=float(np.mean(lams)) if lams else None, seconds=time.time()-start)
    print(f"cell {cell} rel={rel} dist={dist} rho_e={rho_e} cov={row['coverage']} bias={row['bias']} "
          f"fail={row['failed']} lam={row['mean_lambda']} {row['seconds']:.0f}s", flush=True)
    return row


def run(draws, workers):
    with Pool(workers) as pool:
        rows = pool.map(run_cell, [(c, draws) for c in range(len(CELLS))])
    passed = {k: all(r['coverage'][k] >= .86 for r in rows) for k in ('G1', 'G2')}
    return dict(rows=rows, passed=passed, draws_per_cell=draws,
                criterion='90% coverage of the true slope >= .86 in every cell (spatial and independent), per candidate; '
                          'failed fits count as non-coverage; C1_naive informational')


def validate_pins(commit):
    subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'], cwd=ROOT, check=True)
    for rel in FROZEN:
        if subprocess.check_output(['git', 'show', commit+':'+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
            raise ValueError('script/design differs from criterion commit: '+rel)


def write_audit(result, commit):
    out = ROOT/'docs/audits/spatial_eiv_validation'
    result['criterion_commit'] = commit
    result['frozen_sha256'] = {rel: hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() for rel in FROZEN}
    out.with_suffix('.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    lines = ['# Corrected slope inference under spatial dependence: validation (Round 35)', '', result['criterion']+'.', '',
             f"Criterion commit: `{commit}`. {result['draws_per_cell']:,} draws per cell.", '',
             '| Reliability | Range km | Error corr | G1 | G2 | C1 naive (true slope) | G1 bias | G2 bias | G1 / G2 failed | mean λ̂ |',
             '| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- | ---: |']
    for r in result['rows']:
        c, b, f = r['coverage'], r['bias'], r['failed']
        fmt = lambda v: 'n/a' if v is None else f'{v:+.4f}'
        lines.append(f"| {r['reliability']} | {r['range_km']} | {r['error_corr']} | {c['G1']:.4f} | {c['G2']:.4f} | {c['C1_naive']:.4f} | "
                     f"{fmt(b['G1'])} | {fmt(b['G2'])} | {f['G1']} / {f['G2']} | {r['mean_lambda']:.3f} |")
    lines += ['', 'Outcomes: `'+json.dumps(result['passed'], sort_keys=True)+'`.']
    out.with_suffix('.md').write_text('\n'.join(lines)+'\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--smoke-draws', type=int); p.add_argument('--criterion-commit'); p.add_argument('--workers', type=int, default=8)
    a = p.parse_args()
    with patch('requests.sessions.Session.request', side_effect=RuntimeError('Round 35: HTTP blocked')):
        if a.smoke_draws is not None:
            if not 1 <= a.smoke_draws <= 20:
                p.error('smoke draws must be 1..20')
            run(a.smoke_draws, a.workers); return
        if not a.criterion_commit:
            p.error('full run requires --criterion-commit')
        validate_pins(a.criterion_commit)
        if (ROOT/'docs/audits/spatial_eiv_validation.json').exists():
            p.error('refusing to overwrite the full audit')
        write_audit(run(DRAWS, a.workers), a.criterion_commit)


if __name__ == '__main__':
    main()
