# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fixed Round 39 validation: multivariate wild score bootstrap; Poisson/NB/ZIP slope intervals.

    --prepare-targets       count-slope targets per family and cell (400,000 areas; once, before freezing)
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
from census import manova_counts_core as mc
from census.simulation import make_replicates
from spatial_hac_validation import simulation_setup, haversine_matrix

SEED = 20270211
DRAWS = 2000
MV = [(m, design) for m in (2, 3) for design in ('oneway4', 'ancova4')]
CT = [(emed, shape, zeros) for emed in (100, 10) for shape in (None, 2.) for zeros in (0., .2)]
TARGETS = 'docs/audits/manova_counts_targets.json'
GEOMETRY = 'docs/audits/im_acs_beta_star.json'
FROZEN = ('scripts/manova_counts_validation.py', 'census/manova_counts_core.py', 'census/simulation.py',
          'scripts/spatial_hac_validation.py', 'docs/audits/manova_counts_validation_criterion.md', TARGETS, GEOMETRY)
BETA = .3


def geometry(seed):
    g = json.loads((ROOT/GEOMETRY).read_text())['coordinates']
    return simulation_setup('linear', 0, haversine_matrix(np.asarray(g['lon']), np.asarray(g['lat'])), seed)


def counts(rng, E, x_true, shape, zeros, noise):
    lam = E*np.exp(BETA*x_true+.15*noise)
    if shape is not None:
        lam = lam*rng.gamma(shape, 1/shape, len(E))
    y = rng.poisson(lam).astype(float)
    if zeros:
        y[rng.random(len(E)) < zeros] = 0.
    return y


def count_setup(cell):
    emed, shape, zeros = CT[cell]
    rng, L, _ = geometry(SEED+100+cell); n = len(L)
    E = np.maximum(1, np.rint(rng.lognormal(np.log(emed), 1, n)))
    se = rng.lognormal(0, .5, n); se *= np.sqrt(((1-.9)/.9)/np.mean(se**2))
    return rng, L, E, se


def prepare_targets():
    path = ROOT/TARGETS
    if path.exists():
        raise ValueError('refusing to replace committed targets')
    rows = []
    for cell, (emed, shape, zeros) in enumerate(CT):
        _, _, E, se = count_setup(cell)
        rng = np.random.default_rng(np.random.SeedSequence([SEED, cell, 400000]))
        n = 400000; idx = rng.integers(0, len(E), n)
        x = rng.standard_normal(n); xo = x+rng.standard_normal(n)*se[idx]
        y = counts(rng, E[idx], x, shape, zeros, rng.standard_normal(n))
        X = np.column_stack((np.ones(n), xo))
        t = {fam: mc.count_slope(y, X, E[idx], fam)['estimate'] for fam in ('poisson', 'negbin')}
        # ZIP target: the estimate only (Nelder-Mead; statsmodels' ZIP Hessian is NaN at high counts).
        import statsmodels.api as sm
        z = sm.ZeroInflatedPoisson(y, X, exog_infl=np.ones((n, 1)), exposure=E[idx], inflation='logit').fit(
            disp=0, maxiter=2000, method='nm')
        t['zip'] = float(np.asarray(z.params)[2])
        rows.append(dict(cell=cell, **t)); print(cell, t, flush=True)
    path.write_text(json.dumps(dict(seed=SEED, reference_areas=400000, rows=rows), indent=2)+'\n')


def mv_cell(args):
    cell, draws = args
    m, design = MV[cell]
    rng, L, _ = geometry(SEED+cell); n = len(L)
    groups = np.empty(n, int)
    for k, idx in enumerate(np.array_split(np.argsort(rng.standard_normal(n)), 4)):
        groups[idx] = k
    se = rng.lognormal(0, .5, (n, m+1)); se *= np.sqrt((.15/.85)/np.mean(se**2, axis=0))
    se[:, m] *= np.sqrt((.3/.7)/(.15/.85))      # the ANCOVA covariate: reliability 0.7 (outcomes 0.85)
    corr = np.full((m+1, m+1), .5); np.fill_diagonal(corr, 1.); corr[-1, :-1] = corr[:-1, -1] = 0.
    D = np.column_stack([(groups == k).astype(float) for k in (1, 2, 3)])
    rej = {'V1': 0, 'V0': 0}; fails = 0
    start = time.time()
    for draw in range(draws):
        z = rng.standard_normal((n, m))@np.linalg.cholesky(corr[:m, :m]).T
        cov = (L@rng.standard_normal(n))*(1 if design == 'ancova4' else 0)
        Yt = 1+z+.5*cov[:, None]
        e = rng.standard_normal((n, m+1))@np.linalg.cholesky(corr).T*se
        Y = Yt+e[:, :m]
        xo = cov+e[:, m]                          # covariate observed with its own sampling error
        X = np.column_stack((np.ones(n), D)) if design == 'oneway4' else np.column_stack((np.ones(n), D, xo))
        test = [1, 2, 3]
        aux = np.random.default_rng(np.random.SeedSequence([SEED, cell, draw, 7]))
        obs = np.column_stack((Y, xo)); rep = make_replicates(obs, se, aux, corr=corr)
        b = mc.stacked_coefficients(X, Y, test)
        br = []
        for r in range(80):
            Xr = X.copy()
            if design == 'ancova4':
                Xr[:, -1] = rep[:, m, r]
            br.append(mc.stacked_coefficients(Xr, rep[:, :m, r], test))
        Vs = .05*(np.array(br)-b).T @ (np.array(br)-b)
        boot = np.random.default_rng(np.random.SeedSequence([SEED, cell, draw, 9]))
        try:
            rej['V1'] += mc.mv_wild_score(X, Y, test, Vs, boot)['p'] < .10
            rej['V0'] += mc.pillai(X, Y, test)['p'] < .10
        except (ValueError, np.linalg.LinAlgError):
            fails += 1; rej['V1'] += 1
    row = dict(cell=cell, outcomes=m, design=design, draws=draws, size_10={k: v/draws for k, v in rej.items()}, failures=fails,
               seconds=time.time()-start)
    print('mv', row, flush=True)
    return row


def count_cell(args):
    cell, draws = args
    emed, shape, zeros = CT[cell]
    tg = json.loads((ROOT/TARGETS).read_text())['rows'][cell]
    rng, L, E, se = count_setup(cell); n = len(L)
    cov = {f: 0 for f in ('poisson', 'negbin', 'zip')}; fails = {f: 0 for f in cov}
    start = time.time()
    for _ in range(draws):
        x = L@rng.standard_normal(n); xo = x+rng.standard_normal(n)*se
        y = counts(rng, E, x, shape, zeros, L@rng.standard_normal(n))
        X = np.column_stack((np.ones(n), xo))
        for fam in cov:
            try:
                r = mc.count_slope(y, X, E, fam); cov[fam] += r['lower'] <= tg[fam] <= r['upper']
            except (ValueError, np.linalg.LinAlgError):
                fails[fam] += 1
    row = dict(cell=cell, E_median=emed, gamma_shape=shape, zero_share=zeros, draws=draws,
               coverage={f: c/draws for f, c in cov.items()}, failures=fails, seconds=time.time()-start)
    print('ct', row, flush=True)
    return row


def run(draws, workers):
    with Pool(workers) as pool:
        mv = pool.map(mv_cell, [(c, draws) for c in range(len(MV))])
        ct = pool.map(count_cell, [(c, draws) for c in range(len(CT))])
    passed = {'V1': all(.07 <= r['size_10']['V1'] <= .13 for r in mv),
              'poisson': all(r['coverage']['poisson'] >= .86 for r in ct),
              'negbin': all(r['coverage']['negbin'] >= .86 for r in ct),
              'zip': all(r['coverage']['zip'] >= .86 for r in ct if r['zero_share'] > 0 and r['E_median'] <= 10)}
    return dict(multivariate=mv, counts=ct, passed=passed, draws_per_cell=draws,
                criterion='V1: nominal-.10 size in [.07,.13] in every multivariate cell; counts: 90% coverage of the '
                          "family's naive-target slope >= .86 (poisson, negbin all cells; zip low-count cells with structural zeros); "
                          'failures count as rejections / non-coverage; V0 informational')


def validate_pins(commit):
    subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'], cwd=ROOT, check=True)
    for rel in FROZEN:
        if subprocess.check_output(['git', 'show', commit+':'+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
            raise ValueError('script/design differs from criterion commit: '+rel)


def write_audit(result, commit):
    out = ROOT/'docs/audits/manova_counts_validation'
    result['criterion_commit'] = commit
    result['frozen_sha256'] = {rel: hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() for rel in FROZEN}
    out.with_suffix('.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    lines = ['# Multivariate group tests and count-model slopes: validation (Round 39)', '', result['criterion']+'.', '',
             f"Criterion commit: `{commit}`. {result['draws_per_cell']:,} draws per cell.", '',
             '| Outcomes | Design | V1 size .10 | V0 Pillai (iid) size .10 | failures |', '| ---: | :--- | ---: | ---: | ---: |']
    for r in result['multivariate']:
        lines.append(f"| {r['outcomes']} | {r['design']} | {r['size_10']['V1']:.4f} | {r['size_10']['V0']:.4f} | {r['failures']} |")
    lines += ['', '| E median | gamma shape | zero share | Poisson HC3 | NB2 HC3 | ZIP | failures |', '| ---: | :--- | ---: | ---: | ---: | ---: | :--- |']
    for r in result['counts']:
        c = r['coverage']
        lines.append(f"| {r['E_median']} | {r['gamma_shape']} | {r['zero_share']} | {c['poisson']:.4f} | {c['negbin']:.4f} | {c['zip']:.4f} | {r['failures']} |")
    lines += ['', 'Outcomes: `'+json.dumps(result['passed'], sort_keys=True)+'`.']
    out.with_suffix('.md').write_text('\n'.join(lines)+'\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepare-targets', action='store_true'); p.add_argument('--smoke-draws', type=int)
    p.add_argument('--criterion-commit'); p.add_argument('--workers', type=int, default=12)
    a = p.parse_args()
    with patch('requests.sessions.Session.request', side_effect=RuntimeError('Round 39: HTTP blocked')):
        if a.prepare_targets:
            prepare_targets(); return
        if a.smoke_draws is not None:
            if not 1 <= a.smoke_draws <= 20:
                p.error('smoke draws must be 1..20')
            run(a.smoke_draws, a.workers); return
        if not a.criterion_commit:
            p.error('full run requires --criterion-commit')
        validate_pins(a.criterion_commit)
        if (ROOT/'docs/audits/manova_counts_validation.json').exists():
            p.error('refusing to overwrite the full audit')
        write_audit(run(DRAWS, a.workers), a.criterion_commit)


if __name__ == '__main__':
    main()
