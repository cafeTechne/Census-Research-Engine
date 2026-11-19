# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fixed Round 31 omnibus-test validation (PLAN_ROUND_31 section 2).

Commit and push this script and the criterion, then run once:
    scripts/omnibus_validation.py --criterion-commit <sha>
Smoke runs (--smoke-draws 1..20) write no files. Cells run in parallel worker
processes; each cell has fixed seeds, so results do not depend on worker count.
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
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'scripts'))
import numpy as np
import patsy
from scipy.special import expit
from census import omnibus as om
from census.im_acs import constant_columns, cluster_coefficients
from census.simulation import make_replicates
from spatial_hac_validation import simulation_setup, haversine_matrix

SEED = 20261218
NULL_DRAWS, ALT_DRAWS = 2000, 500
DESIGNS = ('oneway4', 'oneway6', 'ancova4', 'twoway', 'spline3', 'spline5')
FAMILY = {'oneway4': 'factor', 'oneway6': 'factor', 'ancova4': 'factor', 'twoway': 'factor',
          'spline3': 'spline', 'spline5': 'spline'}
CELLS = [(model, design, distance) for model in ('linear', 'binomial', 'poisson')
         for design in DESIGNS for distance in (0, 100)]
CANDIDATES = ('W0', 'W1', 'W2', 'W3', 'W4')
GEOMETRY = 'docs/audits/im_acs_beta_star.json'   # Round 30 committed coordinates and k=8 assignment
FROZEN = ('scripts/omnibus_validation.py', 'census/omnibus.py', 'census/im_acs.py', 'census/simulation.py',
          'scripts/spatial_hac_validation.py', 'docs/audits/omnibus_validation_criterion.md', GEOMETRY)
Y_RELIABILITY, ANCOVA_RELIABILITY, SPLINE_RELIABILITY = .85, .7, .85
INFEASIBLE = ('term constant in some clusters but not others', 'tested column constant within clusters')


def geometry():
    g = json.loads((ROOT/GEOMETRY).read_text())
    coords = g['coordinates']; ids = coords['GEOID']
    labels = np.array([g['assignment'][i] for i in ids])
    state = np.array([float(i.startswith('36')) for i in ids])
    return coords, labels, state


def scaled_se(rng, n, k, reliability):
    se = rng.lognormal(0, .5, (n, k))
    return se*np.sqrt(((1-reliability)/reliability)/np.mean(se**2, axis=0))


def split(score, k):
    labels = np.empty(len(score), int)
    for g, idx in enumerate(np.array_split(np.argsort(score, kind='stable'), k)):
        labels[idx] = g
    return labels


def setup(cell, coords):
    model, design, distance = CELLS[cell]
    dist = haversine_matrix(np.asarray(coords['lon']), np.asarray(coords['lat']))
    rng, L, trials = simulation_setup('binomial' if model == 'binomial' else 'linear', distance, dist, SEED+cell)
    n = len(L)
    exposure = np.maximum(5, np.rint(rng.lognormal(np.log(100), 1, n))) if model == 'poisson' else None
    # Fixed "urbanicity" groups: half spatial field, half independent noise.
    urban = (L@rng.standard_normal(n)+rng.standard_normal(n))/np.sqrt(2)
    second = (L@rng.standard_normal(n)+rng.standard_normal(n))/np.sqrt(2)
    k = {'oneway4': 4, 'oneway6': 6, 'ancova4': 4}.get(design)
    groups = split(urban, k) if k else None
    twoway = (split(urban, 2), split(second, 3)) if design == 'twoway' else None
    se_y = scaled_se(rng, n, 1, Y_RELIABILITY)[:, 0] if model == 'linear' else None
    ncov = 2 if design == 'ancova4' else 1 if design.startswith('spline') else 0
    rel = ANCOVA_RELIABILITY if design == 'ancova4' else SPLINE_RELIABILITY
    se_x = scaled_se(rng, n, ncov, rel) if ncov else None
    return dict(rng=rng, L=L, trials=trials, exposure=exposure, groups=groups, twoway=twoway,
                se_y=se_y, se_x=se_x, model=model, design=design, distance=distance)


def dummies(labels, k):
    return np.column_stack([(labels == j).astype(float) for j in range(1, k)])


def design_matrix(s, state, x_obs, info=None):
    """Return X, the tested column indices, IM term groups and the patsy info."""
    n = len(state); d = s['design']
    if d in ('oneway4', 'oneway6'):
        k = 4 if d == 'oneway4' else 6
        X = np.column_stack((np.ones(n), state, dummies(s['groups'], k)))
        return X, list(range(2, 2+k-1)), info
    if d == 'ancova4':
        X = np.column_stack((np.ones(n), state, x_obs, dummies(s['groups'], 4)))
        return X, [4, 5, 6], info
    if d == 'twoway':
        a, b = s['twoway']; A = (a == 1).astype(float); B = dummies(b, 3)
        X = np.column_stack((np.ones(n), state, A, B, A[:, None]*B))
        return X, [5, 6], info
    df = 3 if d == 'spline3' else 5
    if info is None:
        info = patsy.dmatrix(f'cr(x, df={df}, constraints="center") - 1', {'x': x_obs[:, 0]}).design_info
    basis = np.asarray(patsy.build_design_matrices([info], {'x': x_obs[:, 0]})[0], float)
    X = np.column_stack((np.ones(n), state, basis))
    return X, list(range(2, 2+df)), info


def term_groups(X, s):
    terms = [f'c{j}' for j in range(X.shape[1])]; terms[0] = 'Intercept'
    return terms, {'Intercept': [0], 'NY': [1], **{f'c{j}': [j] for j in range(2, X.shape[1])}}


def draw_data(s, state, null, rng):
    model, design, L = s['model'], s['design'], s['L']; n = len(L)
    e = L@rng.standard_normal(n)
    x_true = None
    if design == 'ancova4':
        x1 = L@rng.standard_normal(n)
        x_true = np.column_stack((x1, .5*x1+np.sqrt(.75)*(L@rng.standard_normal(n))))
    elif design.startswith('spline'):
        x_true = (L@rng.standard_normal(n))[:, None]
    x_obs = None
    if x_true is not None:
        z = rng.standard_normal(x_true.shape)
        if x_true.shape[1] == 2:
            z = np.column_stack((z[:, 0], .3*z[:, 0]+np.sqrt(.91)*z[:, 1]))
        x_obs = x_true+z*s['se_x']
    slope = .5 if model == 'linear' else .3
    signal = (.3 if model == 'linear' else .2)*state
    if design in ('oneway4', 'oneway6', 'ancova4') and not null:
        signal = signal+.15*s['groups']
    if design == 'ancova4':
        signal = signal+slope*x_true[:, 0]+slope*x_true[:, 1]
    if design == 'twoway':
        a, b = s['twoway']
        signal = signal+.2*a+.1*b+(0 if null else .2*a*b)
    if design.startswith('spline') and not null:
        signal = signal+.3*np.sin(x_true[:, 0])
    if model == 'linear':
        y = 1+signal+e
        y = y+rng.standard_normal(n)*s['se_y']
    elif model == 'binomial':
        y = rng.binomial(s['trials'].astype(int), expit(-2.6+signal+.15*e))/s['trials']
    else:
        y = rng.poisson(s['exposure']*np.exp(signal+.15*e)).astype(float)
    return y, x_obs


def evaluate(s, state, labels, y, x_obs, aux, boot):
    """p-values for every candidate (None marks a failed fit) and pairwise results."""
    model = s['model']; n = len(y)
    X, test, info = design_matrix(s, state, x_obs)
    b, mu, w = om.fit(X, y, model, s['trials'], s['exposure'])
    V3, _ = om.model_covariance(X, y, mu, w, model, s['trials'], 'HC3')
    V2, part = om.model_covariance(X, y, mu, w, model, s['trials'], 'HC2')
    # Replicates: outcome (linear only) and error-prone covariates.
    cols, ses = [], []
    if model == 'linear':
        cols.append(y[:, None]); ses.append(s['se_y'][:, None])
    if x_obs is not None:
        cols.append(x_obs); ses.append(s['se_x'])
    if cols:
        obs, se = np.column_stack(cols), np.column_stack(ses)
        k = obs.shape[1]; corr = np.eye(k)
        if x_obs is not None and x_obs.shape[1] == 2:
            corr[k-2, k-1] = corr[k-1, k-2] = .3
        rep = make_replicates(obs, se, aux, corr=corr)            # n x k x 80
        Yr = rep[:, 0, :].T if model == 'linear' else np.broadcast_to(y, (80, n))
        if x_obs is not None:
            Xr = np.stack([design_matrix(s, state, rep[:, -x_obs.shape[1]:, r], info)[0] for r in range(80)])
        else:
            Xr = X
        Vs = om.sampling_covariance(b, om.batched_refits(Xr, Yr, model, b, s['trials'], s['exposure']))
    else:
        Vs = np.zeros_like(V3)
    out = {}
    for name, fn in (('W0', lambda: om.w0(b, V3+Vs, test)), ('W1', lambda: om.w1(b, V3+Vs, test, n)),
                     ('W2', lambda: om.w2(b, V2, Vs, test, X, w, part['bread'], part['h'])),
                     ('W3', lambda: om.w3(X, y, model, test, Vs, boot, s['trials'], s['exposure']))):
        try:
            out[name] = fn()['p']
        except (ValueError, RuntimeError, np.linalg.LinAlgError, FloatingPointError):
            out[name] = None
    try:
        terms, groups = term_groups(X, s)
        keep, _ = constant_columns(X, labels, terms, groups)
        if not keep[test].all():
            raise ValueError('tested column constant within clusters')
        kept_test = [int(np.sum(keep[:j])) for j in test]
        betas = cluster_coefficients(X[:, keep], y, labels, model, trials=s['trials'], exposure=s['exposure'])
        out['W4'] = om.w4(betas, kept_test)['p']
    except ValueError as exc:
        # A design the engine refuses before fitting (a tested term constant in some
        # clusters) is infeasible, not a test result.
        out['W4'] = 'infeasible' if str(exc).startswith(INFEASIBLE) else None
    except (RuntimeError, np.linalg.LinAlgError, FloatingPointError):
        out['W4'] = None
    pw = None
    if s['design'] in ('oneway4', 'oneway6') and s['distance'] == 0:
        V = V3+Vs
        r = om.pairwise(b[test], V[np.ix_(test, test)], n-len(b))
        pw = (float(r['p_holm'].min()), float(r['p_simultaneous'].min()))
    return out, pw


def run_cell(args):
    cell, draws, alt_draws = args
    coords, labels, state = geometry()
    s = setup(cell, coords)
    model, design, distance = CELLS[cell]
    count = {c: dict(r10=0, r05=0, failed=0, power=0, alt_failed=0, infeasible=0) for c in CANDIDATES}
    fwer = dict(P1=0, P2=0, draws=0)
    start = time.time()
    for draw in range(draws+alt_draws):
        null = draw < draws
        y, x_obs = draw_data(s, state, null, s['rng'])
        aux = np.random.default_rng(np.random.SeedSequence([SEED, cell, draw, 7]))
        boot = np.random.default_rng(np.random.SeedSequence([SEED, cell, draw, 9]))
        p, pw = evaluate(s, state, labels, y, x_obs, aux, boot)
        for c in CANDIDATES:
            v = count[c]
            if p[c] == 'infeasible':
                v['infeasible'] += 1
                continue
            if null:
                v['failed'] += p[c] is None
                v['r10'] += p[c] is None or p[c] < .10
                v['r05'] += p[c] is None or p[c] < .05
            else:
                v['alt_failed'] += p[c] is None
                v['power'] += p[c] is not None and p[c] < .10
        if null and pw is not None:
            fwer['draws'] += 1; fwer['P1'] += pw[0] < .10; fwer['P2'] += pw[1] < .10
    # Groups are fixed per cell, so a W4 design is either always or never infeasible;
    # a cell with any infeasible draw is "not applicable" for W4.
    rows = [dict(candidate=c, cell=cell, model=model, design=design, family=FAMILY[design], range_km=distance,
                 seed=SEED+cell, null_draws=draws, applicable=v['infeasible'] == 0,
                 size_10=v['r10']/draws if v['infeasible'] == 0 else None,
                 size_05=v['r05']/draws if v['infeasible'] == 0 else None,
                 failed=v['failed'], infeasible_draws=v['infeasible'],
                 power_10=(v['power']/alt_draws if alt_draws and v['infeasible'] == 0 else None),
                 alt_failed=v['alt_failed']) for c, v in count.items()]
    post = None
    if fwer['draws']:
        post = dict(cell=cell, model=model, design=design, draws=fwer['draws'],
                    fwer_P1=fwer['P1']/fwer['draws'], fwer_P2=fwer['P2']/fwer['draws'])
    print(f'cell {cell} {model} {design} {distance} ' +
          ' '.join(f"{c}={count[c]['r10']/draws:.3f}" if not count[c]['infeasible'] else f'{c}=n/a'
                   for c in CANDIDATES) +
          (f" P1={post['fwer_P1']:.3f} P2={post['fwer_P2']:.3f}" if post else '') +
          f' {time.time()-start:.0f}s', flush=True)
    return rows, post, time.time()-start


def run(draws, alt_draws, workers):
    with Pool(workers) as pool:
        results = pool.map(run_cell, [(c, draws, alt_draws) for c in range(len(CELLS))])
    rows = [r for res in results for r in res[0]]
    posthoc = [res[1] for res in results if res[1]]
    judged = lambda r: r['applicable'] and (r['candidate'] == 'W4' or r['range_km'] == 0)
    passed = {}
    for c in CANDIDATES:
        for model in ('linear', 'binomial', 'poisson'):
            for family in ('factor', 'spline'):
                sel = [r for r in rows if r['candidate'] == c and r['model'] == model and r['family'] == family and judged(r)]
                passed[f'{c}/{model}/{family}'] = bool(sel) and all(.07 <= r['size_10'] <= .13 for r in sel)
    for proc in ('P1', 'P2'):
        for model in ('linear', 'binomial', 'poisson'):
            passed[f'{proc}/{model}'] = all(p['fwer_'+proc] <= .13 for p in posthoc if p['model'] == model)
    return dict(rows=rows, posthoc=posthoc, passed=passed, null_draws=draws, alt_draws=alt_draws,
                cell_seconds=[res[2] for res in results],
                criterion=('nominal-.10 null size in [.07,.13] in every judged cell, per candidate x model x '
                           'design family (W0-W3 independent cells; W4 all applicable cells, where a design the engine '
                           'refuses is not applicable; failed fits count as rejections; a family with no applicable '
                           'cell fails); pairwise familywise error <= .13 in independent one-way cells'))


def validate_pins(commit):
    subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'], cwd=ROOT, check=True)
    for rel in FROZEN:
        if subprocess.check_output(['git', 'show', commit+':'+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
            raise ValueError('script/design differs from criterion commit: '+rel)


def write_audit(result, commit):
    out = ROOT/'docs/audits/omnibus_validation'
    result['criterion_commit'] = commit
    result['frozen_sha256'] = {rel: hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() for rel in FROZEN}
    out.with_suffix('.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    lines = ['# Omnibus tests and pairwise comparisons: validation (Round 31)', '', result['criterion']+'.', '',
             f"Criterion commit: `{commit}`. {result['null_draws']:,} null and {result['alt_draws']} alternative "
             'draws per cell; nothing retuned.', '',
             '| Candidate | Model | Design | Range km | Size .10 | Size .05 | Failed | Power .10 |',
             '| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: |']
    fmt = lambda v, d: 'n/a' if v is None else f'{v:.{d}f}'
    for r in sorted(result['rows'], key=lambda r: (r['candidate'], r['model'], r['design'], r['range_km'])):
        lines.append(f"| {r['candidate']} | {r['model']} | {r['design']} | {r['range_km']} | {fmt(r['size_10'], 4)} | "
                     f"{fmt(r['size_05'], 4)} | {r['failed']} | {fmt(r['power_10'], 3)} |")
    lines += ['', '| Pairwise | Model | Design | FWER P1 (Holm) | FWER P2 (simultaneous) |', '| :--- | :--- | :--- | ---: | ---: |']
    for p in result['posthoc']:
        lines.append(f"| independent | {p['model']} | {p['design']} | {p['fwer_P1']:.4f} | {p['fwer_P2']:.4f} |")
    lines += ['', 'Outcomes (candidate/model/family): `'+json.dumps(result['passed'], sort_keys=True)+'`.', '',
              'W0 is the Round 27 chi-squared reference (comparison only). W1-W3 assume independent areas and are '
              'judged on independent cells; their spatial-cell sizes are informational. W4 targets the naive '
              '(observed-ACS) coefficients through the fixed eight MI/NY clusters and is judged on all cells.']
    out.with_suffix('.md').write_text('\n'.join(lines)+'\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--smoke-draws', type=int); p.add_argument('--criterion-commit')
    p.add_argument('--workers', type=int, default=16)
    args = p.parse_args()
    with patch('requests.sessions.Session.request', side_effect=RuntimeError('Round 31: HTTP blocked')):
        if args.smoke_draws is not None:
            if not 1 <= args.smoke_draws <= 20:
                p.error('smoke draws must be 1..20; no audits written')
            run(args.smoke_draws, args.smoke_draws, args.workers)
            return
        if not args.criterion_commit:
            p.error('full run requires --criterion-commit')
        validate_pins(args.criterion_commit)
        out = ROOT/'docs/audits/omnibus_validation'
        if out.with_suffix('.json').exists() or out.with_suffix('.md').exists():
            p.error('refusing to rerun/overwrite the full audit')
        write_audit(run(NULL_DRAWS, ALT_DRAWS, args.workers), args.criterion_commit)


if __name__ == '__main__':
    main()
