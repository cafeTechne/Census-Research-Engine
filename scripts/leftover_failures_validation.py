# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 62: leftover failures (frozen with the criterion).

A (9 cells): binomial SCPC with rho_bar .15 and .20 on Round 58's binomial N cells (MI/NY and OH/PA, 2,000 draws)
   and R cell (MI/NY 100 km, reliability .7, 10,000 draws); generator and targets of Rounds 30/44/58; target beta*.
   Passes per rho_bar with coverage >= .86 in all nine cells.
B (4 cells): Theil T with m = 8,000 households (Round 56 generator and targets; rho .1/.4 x weight CV .3/1.0;
   incomes I1, I2): T1 (Round 60 log interval) and T0 (comparison). Passes when T1 >= .86 in all cells, both incomes.
C (2 cells): Round 57 design A on six groups (Round 50 Gamma observed counts, Round 51 Gaussian replicates clipped),
   rho 0 and -.15; Round 52 bins, Round 50 bin rule, Round 57 per-bin affected-draw check.
Failed draws count as non-coverage. Per-draw seeds [20280701 + cell, draw].

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
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'scripts'))
import numpy as np  # noqa: E402

from census import pums_inequality_core as pc  # noqa: E402
from census import scpc_core as sc  # noqa: E402
from census.segregation import _indices  # noqa: E402
from spatial_hac_validation import simulation_draw  # noqa: E402
import im_acs_validation as r30  # noqa: E402
import spatial_outside_validation as r58  # noqa: E402
import pums_tests_validation as PTV  # noqa: E402
import pums_inequality_validation as R56  # noqa: E402
import segregation_realistic_validation as r50  # noqa: E402
import negative_replicates_validation as r51  # noqa: E402
import segregation_groups_validation as r52  # noqa: E402
import segregation_gaps_validation as r57  # noqa: E402

SEED = 20280701
DRAWS = 2000
R_DRAWS = 10000
RHOS = (.15, .20)
BIN_CELLS = [4, 5, 6, 7]                                    # Round 30 binomial cells
CELLS = ([('A', dict(geometry=g, r30_cell=c)) for g in ('miny', 'ohpa') for c in BIN_CELLS]
         + [('A', dict(geometry='miny', r30_cell=7, long=True))]
         + [('B', dict(rho=rho, weight_cv=cv, households=8000)) for rho in (.1, .4) for cv in (.3, 1.)]
         + [('C', dict(rho=rho)) for rho in (0., -.15)])
FROZEN = ('scripts/leftover_failures_validation.py', 'census/scpc_core.py', 'census/pums_inequality_core.py',
          'census/segregation.py', 'census/im_acs.py', 'census/simulation.py', 'census/pums_tests.py',
          'scripts/spatial_outside_validation.py', 'scripts/im_acs_validation.py', 'scripts/spatial_hac_validation.py',
          'scripts/pums_tests_validation.py', 'scripts/pums_inequality_validation.py',
          'scripts/segregation_realistic_validation.py', 'scripts/negative_replicates_validation.py',
          'scripts/segregation_groups_validation.py', 'scripts/segregation_gaps_validation.py',
          'docs/audits/pums_inequality_targets.json', 'docs/audits/segregation_r57_counts.csv.gz',
          'docs/audits/im_acs_beta_star.json', 'docs/audits/ohpa_geometry.json',
          'docs/audits/leftover_failures_validation_criterion.md')
ERRORS = (ValueError, np.linalg.LinAlgError, RuntimeError, FloatingPointError, KeyError)


def draws_for(cell):
    return R_DRAWS if CELLS[cell][1].get('long') else DRAWS


def a_draws(cell, start, stop):
    par = CELLS[cell][1]
    g, coords, _, state = r58.geometry(par['geometry'])
    rc = par['r30_cell']; model = r30.CELLS[rc][0]
    _, L, trials, exposure, sev = r30.setup(rc, coords)
    target = g['rows'][rc]['beta_star']
    S = {r: r58.scpc_setup(par['geometry'], r) for r in RHOS}
    out = {f'SCPC{int(100*r)}': [0, 0] for r in RHOS}
    for d in range(start, stop):
        rng = np.random.default_rng([SEED+cell, d])
        base, old_y = simulation_draw('linear', L, None, rng)
        x1 = base[:, 1]; error = old_y-1-.5*x1
        true = np.column_stack((x1, .5*x1+np.sqrt(.75)*(L@rng.standard_normal(len(L)))))
        z = rng.standard_normal((len(L), 2))
        observed = true+np.column_stack((z[:, 0], .3*z[:, 0]+np.sqrt(.91)*z[:, 1]))*sev
        y = r30.outcome(model, true, state, error, rng, trials, exposure)
        X = np.column_stack((np.ones(len(L)), observed, state))
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                theta, e = sc.influence(X, y, model, 1, trials=trials, exposure=exposure)
            for r in RHOS:
                iv = sc.interval(theta, e, S[r]); out[f'SCPC{int(100*r)}'][0] += iv['lower'] <= target <= iv['upper']
        except ERRORS:
            for r in RHOS:
                out[f'SCPC{int(100*r)}'][1] += 1
    return out


def b_draws(cell, start, stop):
    par = CELLS[cell][1]
    targets = json.loads((ROOT/R56.TARGETS).read_text())
    sigma = PTV.sigma_for(par['weight_cv'])
    out = {f'{i}|{p}': [0, 0] for i in ('I1', 'I2') for p in ('T0', 'T1')}
    for d in range(start, stop):
        rng = np.random.default_rng([SEED+cell, d])
        p, W = PTV.draw_sample(rng, sigma, par['rho'], par['households'])
        for i in ('I1', 'I2'):
            tgt = targets[f'{i}|theil_t']
            try:
                th = pc.measures(R56.incomes(p)[i], W)['theil_t']
                ivs = {'T0': pc.sdr_summary(th), 'T1': pc.transformed_summary(th, 'log')}
            except ERRORS:
                for pr in ('T0', 'T1'):
                    out[f'{i}|{pr}'][1] += 1
                continue
            for pr, s in ivs.items():
                out[f'{i}|{pr}'][0] += s['lower'] <= tgt <= s['upper']
    return out


def c_draws(cell, start, stop):
    rho = CELLS[cell][1]['rho']
    S = r57.setup6(); P = r52.MULTI; C = len(S['counties'])
    hits = np.zeros((C, len(P))); fails = np.zeros((C, len(P))); aff_n = np.zeros(C); aff_hits = np.zeros((C, len(P)))
    for d in range(start, stop):
        rng = np.random.default_rng([SEED+cell, d])
        obs = r50.gamma_copula(rng, S['mu'], S['sd'], rho)
        reps = r51.gaussian_replicates(rng, obs, S['sd'], rho)
        negany = (reps < 0).any(axis=0); reps = np.maximum(reps, 0.)
        for c, idx in enumerate(S['members']):
            v = _indices(np.concatenate((obs[idx][None], reps[:, idx]), axis=0))
            raw, rr = v[0], v[1:]
            with np.errstate(invalid='ignore'):
                se = np.sqrt(.05*np.sum((rr-raw)**2, axis=0)); bc = raw-4*(rr.mean(axis=0)-raw)
            ok = np.isfinite(raw) & np.isfinite(rr).all(axis=0)
            affected = bool(negany[idx].any()); aff_n[c] += affected
            for j, (_, k, corr) in enumerate(P):
                if not ok[k]:
                    fails[c, j] += 1; continue
                h = abs((bc[k] if corr else raw[k])-S['truth'][c, k]) <= r50.Z90*se[k]
                hits[c, j] += h; aff_hits[c, j] += h and affected
    return dict(hits=hits, fails=fails, aff_n=aff_n, aff_hits=aff_hits)


def job(args):
    cell, start, stop = args
    kind = CELLS[cell][0]
    return cell, (a_draws if kind == 'A' else b_draws if kind == 'B' else c_draws)(cell, start, stop)


def run(scale, workers, chunk):
    tasks = []
    for c in range(len(CELLS)):
        n = max(1, int(round(draws_for(c)*scale)))
        tasks += [(c, s, min(s+chunk, n)) for s in range(0, n, chunk)]
    acc = {}; t0 = time.time()
    with ProcessPoolExecutor(workers) as ex:
        for cell, out in ex.map(job, tasks):
            if cell not in acc:
                acc[cell] = out
            else:
                for k in out:
                    if isinstance(out[k], list):
                        acc[cell][k] = [a+b for a, b in zip(acc[cell][k], out[k])]
                    else:
                        acc[cell][k] = acc[cell][k]+out[k]
            print({'cell': cell, 'seconds': round(time.time()-t0)}, flush=True)
    result = dict(cells=[], passed={})
    for c, (kind, par) in enumerate(CELLS):
        if kind == 'C':
            continue
        n = max(1, int(round(draws_for(c)*scale)))
        result['cells'].append(dict(problem=kind, **par, draws=n, coverage={k: v[0]/n for k, v in acc[c].items()},
                                    failed={k: v[1] for k, v in acc[c].items()}))
    for r in RHOS:
        k = f'SCPC{int(100*r)}'
        result['passed'][f'binomial_{k}'] = bool(all(x['coverage'][k] >= .86 for x in result['cells'] if x['problem'] == 'A'))
    result['passed']['theil_t_T1_8000'] = bool(all(x['coverage'][f'{i}|T1'] >= .86 for x in result['cells']
                                                   if x['problem'] == 'B' for i in ('I1', 'I2')))
    S = r57.setup6(); n = max(1, int(round(DRAWS*scale)))
    cc = [c for c in range(len(CELLS)) if CELLS[c][0] == 'C']
    six = {}
    for j, (name, _, corr) in enumerate(r52.MULTI):
        cov = {str(CELLS[c][1]['rho']): acc[c]['hits'][:, j]/n for c in cc}
        bins = r52.judge(cov, S['noise'])
        aff = r57.bin_affected({str(CELLS[c][1]['rho']): (None, None, acc[c]['aff_n'], acc[c]['aff_hits']) for c in cc}, S['noise'], j)
        for b, row in zip(bins, aff):
            row_ok = all(v['coverage'] >= r50.MEAN_MIN for v in row.values() if v['pairs'] >= r57.AFFECTED_MIN)
            b['affected'] = row; b['passed'] = bool(b['passed'] and row_ok)
        st = [(b['passed'] if b['judged'] else None) for b in bins]
        six[name] = dict(bins=bins, validated_max_noise=r52.range_top(st),
                         failed_draws=int(sum(acc[c]['fails'][:, j].sum() for c in cc)))
    result['six_group_clipped'] = six
    result['passed']['clip_six'] = {k: v['validated_max_noise'] for k, v in six.items()}
    return result


def validate_pins(commit):
    subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'], cwd=ROOT, check=True)
    for rel in FROZEN:
        if subprocess.check_output(['git', 'show', commit+':'+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
            raise SystemExit('script/design differs from criterion commit: '+rel)


def write_audit(result, commit):
    out = ROOT/'docs/audits/leftover_failures_validation'
    result.update(criterion_commit=commit, draws_per_cell=DRAWS, r_draws=R_DRAWS, seed=SEED,
                  frozen_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FROZEN},
                  scpc={geo: {str(r): dict(q=r58.scpc_setup(geo, r)['q'], cv=r58.scpc_setup(geo, r)['cv'],
                                           benchmark_range_km=1/r58.scpc_setup(geo, r)['c0']) for r in RHOS}
                        for geo in ('miny', 'ohpa')})
    out.with_suffix('.json').write_text(json.dumps(result, indent=1, default=float)+'\n')
    L = ['# Leftover failures: validation (Round 62)', '',
         'A: binomial SCPC with rho_bar .15/.20 (Round 58 cells). B: Theil T with 8,000 households (T1 log interval). '
         'C: clipped six-group segregation (Round 57 design A). Pass: coverage >= .86 in every cell (C: Round 50 bin '
         'rule with the Round 57 affected-draw check).', '', f'Criterion commit: `{commit}`.', '',
         '| Problem | Setting | Draws | Coverage | Failed |', '| :--- | :--- | ---: | :--- | :--- |']
    for r in result['cells']:
        setting = ', '.join(f'{k} {v}' for k, v in r.items() if k not in ('problem', 'coverage', 'failed', 'draws'))
        L.append(f"| {r['problem']} | {setting} | {r['draws']} | " + ', '.join(f'{k} {v:.4f}' for k, v in r['coverage'].items())
                 + ' | ' + ', '.join(f'{k} {v}' for k, v in r['failed'].items() if v) + ' |')
    L += ['', '## C: clipped six-group H', '', '| Index | Bin | Counties | Judged | rho cells (mean / share >= .80 / min) | Affected | Passed |',
          '| :--- | :--- | ---: | :--- | :--- | :--- | :--- |']
    for name, p in result['six_group_clipped'].items():
        for b in p['bins']:
            if not b['counties']:
                continue
            cells = '; '.join('—' if c is None else f"{c['mean']:.4f} / {c['share_ge_80']:.3f} / {c['min']:.4f}" for c in b['cells'].values())
            aff = '; '.join(f"{v['pairs']} / {'—' if v['coverage'] is None else format(v['coverage'], '.4f')}" for v in b['affected'].values())
            L.append(f"| {name} | {b['bin']} | {b['counties']} | {b['judged']} | {cells} | {aff} | {b['passed']} |")
        L.append(f"| {name} | **validated to** | | | {p['validated_max_noise']} | | |")
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
        r = run(a.smoke_draws/DRAWS, a.workers, max(1, min(a.chunk, a.smoke_draws)))
        for c in r['cells']:
            print(c)
        print(r['passed'])
        return
    if not a.criterion_commit:
        ap.error('full run requires --criterion-commit')
    validate_pins(a.criterion_commit)
    write_audit(run(1., a.workers, a.chunk), a.criterion_commit)


if __name__ == '__main__':
    main()
