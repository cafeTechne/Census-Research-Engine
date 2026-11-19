# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fixed Round 33 validation of rank/partial correlation intervals and rank group procedures.

    --prepare-targets       400,000-area reference values per cell (once, before freezing)
    --smoke-draws N         1..20 draws per cell; no files
    --criterion-commit SHA  the full run
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
from census import rank_methods as rm
from census.simulation import make_replicates
from spatial_hac_validation import simulation_setup, haversine_matrix

SEED = 20261231
DRAWS = 2000
CELLS = [(rho, rel, dist) for rho in (0., .4) for rel in (.9, .7) for dist in (0, 100)]
TARGETS = 'docs/audits/rank_targets.json'
GEOMETRY = 'docs/audits/im_acs_beta_star.json'
FROZEN = ('scripts/rank_validation.py', 'census/rank_methods.py', 'census/simulation.py',
          'scripts/spatial_hac_validation.py', 'docs/audits/rank_validation_criterion.md', TARGETS, GEOMETRY)
METHODS = ('pearson', 'spearman', 'kendall', 'partial')
LOGVAR = (np.exp(.25)-1)*np.exp(.25)     # variance of exp(0.5*N(0,1))
SE_GROUP = (1., 1.5, 1., 1.5)


def coords():
    g = json.loads((ROOT/GEOMETRY).read_text())['coordinates']
    return np.asarray(g['lon']), np.asarray(g['lat'])


def setup(cell):
    rho, rel, dist = CELLS[cell]
    lon, lat = coords()
    rng, L, _ = simulation_setup('linear', dist, haversine_matrix(lon, lat), SEED+cell)
    n = len(L)
    se = rng.lognormal(0, .5, (n, 4))                         # x, y, z, group outcome w
    se *= np.sqrt(LOGVAR*(1-rel)/rel/np.mean(se**2, axis=0))
    urban = (L@rng.standard_normal(n)+rng.standard_normal(n))/np.sqrt(2)
    groups = np.empty(n, int)
    for k, idx in enumerate(np.array_split(np.argsort(urban, kind='stable'), 4)):
        groups[idx] = k
    se[:, 3] *= np.array(SE_GROUP)[groups]
    return rng, L, se, groups


def truths(rng, L, rho, n):
    f = [L@rng.standard_normal(n) for _ in range(4)]
    x = f[0]; y = rho*x+np.sqrt(1-rho**2)*f[1]; z = .5*x+np.sqrt(.75)*f[2]
    return np.exp(.5*np.column_stack((x, y, z, f[3])))


def prepare_targets():
    path = ROOT/TARGETS
    if path.exists():
        raise ValueError('refusing to replace committed targets')
    rows = []
    for cell, (rho, rel, dist) in enumerate(CELLS):
        _, _, se, _ = setup(cell)
        rng = np.random.default_rng(np.random.SeedSequence([SEED, cell, 400000]))
        n = 400000
        t = np.exp(.5*_iid(rng, rho, n))
        idx = rng.integers(0, len(se), n)
        e = rng.standard_normal((n, 3))
        o = t[:, :3]+e*se[idx, :3]
        sub = rng.choice(n, 40000, replace=False)                # Kendall on a 40,000-area subsample
        vals = {m: rm.coefficient(o[sub if m == 'kendall' else slice(None), 0], o[sub if m == 'kendall' else slice(None), 1],
                                  m, o[:, 2] if m == 'partial' else None) for m in METHODS}
        true = {m: rm.coefficient(t[sub if m == 'kendall' else slice(None), 0], t[sub if m == 'kendall' else slice(None), 1],
                                  m, t[:, 2] if m == 'partial' else None) for m in METHODS}
        rows.append(dict(cell=cell, rho=rho, reliability=rel, range_km=dist, observed=vals, true=true))
        print(cell, vals, flush=True)
    path.write_text(json.dumps(dict(seed=SEED, rows=rows, reference_areas=400000, kendall_subsample=40000), indent=2)+'\n')


def _iid(rng, rho, n):
    f = rng.standard_normal((n, 4))
    x = f[:, 0]; y = rho*x+np.sqrt(1-rho**2)*f[:, 1]; z = .5*x+np.sqrt(.75)*f[:, 2]
    return np.column_stack((x, y, z, f[:, 3]))


def run_cell(args):
    cell, draws = args
    rho, rel, dist = CELLS[cell]
    target = json.loads((ROOT/TARGETS).read_text())['rows'][cell]
    rng, L, se, groups = setup(cell)
    n = len(L)
    cov = {f'{m}/{v}': 0 for m in METHODS for v in (1, 2)}
    covtrue = dict(cov)
    b = {'B1/cover': 0, 'B2/cover': 0, 'B1/reject': 0, 'B2/reject': 0, 'B1/power': 0, 'B2/power': 0, 'KW/reject': 0}
    fails = {}
    start = time.time()
    for draw in range(draws):
        t = truths(rng, L, rho, n)
        o = t+rng.standard_normal((n, 4))*se
        aux = np.random.default_rng(np.random.SeedSequence([SEED, cell, draw, 7]))
        rep = make_replicates(o, se, aux)                    # n x 4 x 80
        for m in METHODS:
            for v in (1, 2):
                key = f'{m}/{v}'
                try:
                    r = rm.correlation_interval(o[:, 0], o[:, 1], m, v, reps_x=rep[:, 0], reps_y=rep[:, 1],
                                                z=o[:, 2] if m == 'partial' else None,
                                                reps_z=rep[:, 2] if m == 'partial' else None)
                    cov[key] += r['lower'] <= target['observed'][m] <= r['upper']
                    covtrue[key] += r['lower'] <= target['true'][m] <= r['upper']
                except ValueError:
                    fails[key] = fails.get(key, 0)+1
        g0, g1 = groups == 0, groups == 1
        shift = o[:, 3]+.3*np.sqrt(LOGVAR)*(groups == 1)            # alternative: group 1 shifted up
        rep_shift = rep[:, 3]+.3*np.sqrt(LOGVAR)*(groups == 1)[:, None]
        for v in (1, 2):
            try:
                r = rm.superiority_interval(o[g0, 3], o[g1, 3], v, reps_x=rep[g0, 3], reps_y=rep[g1, 3])
                b[f'B{v}/cover'] += r['lower'] <= .5 <= r['upper']
                b[f'B{v}/reject'] += r['p_value'] < .10
                a = rm.superiority_interval(shift[g0], shift[g1], v, reps_x=rep_shift[g0], reps_y=rep_shift[g1])
                b[f'B{v}/power'] += a['p_value'] < .10
            except ValueError:
                fails[f'B{v}'] = fails.get(f'B{v}', 0)+1
        if rho == 0:
            b['KW/reject'] += rm.kruskal([o[groups == k, 3] for k in range(4)])['p'] < .10
    row = dict(cell=cell, rho=rho, reliability=rel, range_km=dist, draws=draws,
               coverage_observed={k: v/draws for k, v in cov.items()}, coverage_true={k: v/draws for k, v in covtrue.items()},
               superiority={k: v/draws for k, v in b.items() if not k.startswith('KW')},
               kruskal_size=(b['KW/reject']/draws if rho == 0 else None), failures=fails, seconds=time.time()-start)
    print(f"cell {cell} rho={rho} rel={rel} dist={dist} " + ' '.join(f"{k}={v:.3f}" for k, v in row['coverage_observed'].items())
          + ' | ' + ' '.join(f"{k}={v:.3f}" for k, v in row['superiority'].items())
          + (f" KW={row['kruskal_size']:.3f}" if row['kruskal_size'] is not None else '') + f" {row['seconds']:.0f}s", flush=True)
    return row


def run(draws, workers):
    with Pool(workers) as pool:
        rows = pool.map(run_cell, [(c, draws) for c in range(len(CELLS))])
    judged = [r for r in rows if r['range_km'] == 0]
    passed = {k: all(r['coverage_observed'][k] >= .86 for r in judged) for k in rows[0]['coverage_observed']}
    passed.update({f'B{v}': all(r['superiority'][f'B{v}/cover'] >= .86 for r in judged) for v in (1, 2)})
    passed['KW'] = all(.07 <= r['kruskal_size'] <= .13 for r in judged if r['kruskal_size'] is not None)
    return dict(rows=rows, passed=passed, draws_per_cell=draws,
                criterion='intervals: 90% coverage of the observed-estimate target >= .86 in every independent cell; '
                          'Kruskal-Wallis: nominal-.10 size in [.07,.13] in independent null cells; failures count as non-coverage')


def validate_pins(commit):
    subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'], cwd=ROOT, check=True)
    for rel in FROZEN:
        if subprocess.check_output(['git', 'show', commit+':'+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
            raise ValueError('script/design differs from criterion commit: '+rel)


def write_audit(result, commit):
    out = ROOT/'docs/audits/rank_validation'
    result['criterion_commit'] = commit
    result['frozen_sha256'] = {rel: hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() for rel in FROZEN}
    out.with_suffix('.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    keys = sorted(result['rows'][0]['coverage_observed'])
    lines = ['# Rank and partial correlation, superiority and Kruskal-Wallis: validation (Round 33)', '',
             result['criterion']+'.', '', f"Criterion commit: `{commit}`. {result['draws_per_cell']:,} draws per cell.", '',
             '## Coverage of the observed-estimate target (90%)', '',
             '| corr | reliability | range km | ' + ' | '.join(keys) + ' | B1 | B2 |',
             '| ' + ' | '.join([':---']*3+['---:']*(len(keys)+2)) + ' |']
    for r in result['rows']:
        lines.append(f"| {r['rho']} | {r['reliability']} | {r['range_km']} | " + ' | '.join(f"{r['coverage_observed'][k]:.4f}" for k in keys)
                     + f" | {r['superiority']['B1/cover']:.4f} | {r['superiority']['B2/cover']:.4f} |")
    lines += ['', '## Superiority test size/power and Kruskal-Wallis size (nominal .10)', '',
              '| corr | reliability | range km | B1 size | B2 size | B1 power | B2 power | KW size |', '| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: |']
    for r in result['rows']:
        s = r['superiority']; kw = 'n/a' if r['kruskal_size'] is None else f"{r['kruskal_size']:.4f}"
        lines.append(f"| {r['rho']} | {r['reliability']} | {r['range_km']} | {s['B1/reject']:.4f} | {s['B2/reject']:.4f} | "
                     f"{s['B1/power']:.3f} | {s['B2/power']:.3f} | {kw} |")
    lines += ['', 'Coverage of the error-free coefficient is in the JSON (attenuation expected).', '',
              'Outcomes: `'+json.dumps(result['passed'], sort_keys=True)+'`.', '',
              'Spatial (100 km) cells are informational; the procedures assume independent areas.']
    out.with_suffix('.md').write_text('\n'.join(lines)+'\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepare-targets', action='store_true'); p.add_argument('--smoke-draws', type=int)
    p.add_argument('--criterion-commit'); p.add_argument('--workers', type=int, default=8)
    a = p.parse_args()
    with patch('requests.sessions.Session.request', side_effect=RuntimeError('Round 33: HTTP blocked')):
        if a.prepare_targets:
            prepare_targets(); return
        if a.smoke_draws is not None:
            if not 1 <= a.smoke_draws <= 20:
                p.error('smoke draws must be 1..20')
            run(a.smoke_draws, a.workers); return
        if not a.criterion_commit:
            p.error('full run requires --criterion-commit')
        validate_pins(a.criterion_commit)
        out = ROOT/'docs/audits/rank_validation'
        if out.with_suffix('.json').exists():
            p.error('refusing to overwrite the full audit')
        write_audit(run(DRAWS, a.workers), a.criterion_commit)


if __name__ == '__main__':
    main()
