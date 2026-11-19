# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fixed Round 49 validation: survey-weighted PUMS models with the SDR replicate variance.

    --prepare-targets       write the reference-population targets (once, before freezing)
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
from census import pums_models_core as pm
from census import pums_tests as pt
import pums_tests_validation as PTV

SEED = 20270701
DRAWS = 2000
CHUNK = 250
CELLS = PTV.CELLS                                   # (rho, weight CV, households)
TARGETS = 'docs/audits/pums_models_targets.json'
FROZEN = ('scripts/pums_models_validation.py', 'census/pums_models_core.py', 'census/pums_tests.py',
          'scripts/pums_tests_validation.py', 'docs/audits/pums_models_validation_criterion.md', TARGETS)
MODELS = ('O', 'P', 'M', 'Q', 'G')


def draw_sample(rng, sigma, rho, m):
    """Round 32 ``draw_sample`` line for line, also returning each person's geography g."""
    u = rng.uniform(0, 1, m)
    pi = np.exp(sigma*PTV.field(PTV.GRID)); cdf = np.cumsum(pi); cdf /= cdf[-1]
    g = np.sort(np.interp(u, cdf, PTV.GRID))
    w = 1/np.exp(sigma*PTV.field(g))
    p = PTV.population(rng, g, rho)
    W = (w[:, None]*np.column_stack((np.ones(m), pt.sdr_factors(m))))[p['idx']]
    return p, W, g[p['idx']]


def designs(p, gp):
    s, c = np.sin(2*np.pi*gp), np.cos(2*np.pi*gp); one = np.ones(len(gp))
    A = p['A'].astype(int)
    return dict(
        O=('ordered_logit', A, s[:, None], [0]),
        P=('ordered_probit', A, s[:, None], [0]),
        M=('mnlogit', A, np.column_stack((one, s)), [1, 3]),       # s slopes for A = 1 and A = 2 vs 0
        Q=('median', np.log(p['y1']), np.column_stack((one, A, gp)), [1, 2]),
        G=('probit', p['C'].astype(float), np.column_stack((one, A, c)), [1, 2]))


def prepare_targets():
    path = ROOT/TARGETS
    if path.exists():
        raise ValueError('refusing to replace committed targets')
    rng = np.random.default_rng(np.random.SeedSequence([SEED, 400000]))
    g = rng.uniform(0, 1, 400000)
    p = PTV.population(rng, g, .25)
    d = designs(p, g[p['idx']]); one = np.ones(len(p['idx']))
    o, _ = pm.ordered_fit(d['O'][1], d['O'][2], one, 'logit')
    mn, _ = pm.mnlogit_fit(d['M'][1], d['M'][2], one)
    targets = dict(O=[float(o[0])], P=[.8], M=[float(mn[1]), float(mn[3])], Q=[.15, .3], G=[.4, .5],
                   reference=dict(households=400000, persons=int(len(p['idx'])), seed=[SEED, 400000], rho=.25,
                                  note='O and M are pseudo-true values of misspecified logit models (the latent '
                                       'model is probit); P, Q and G are exact'))
    path.write_text(json.dumps(targets, indent=2)+'\n')
    print(json.dumps(targets, indent=2))


def one_draw(rng, cell, targets):
    rho, cv, m = CELLS[cell]
    p, W, gp = draw_sample(rng, PTV.sigma_for(cv), rho, m)
    rec = {}
    for key, (kind, y, X, idx) in designs(p, gp).items():
        try:
            r = pm.sdr_fit(kind, y, X, W)
            rec[f'V1_{key}'] = [bool(r['lower'][j] <= t <= r['upper'][j]) for j, t in zip(idx, targets[key])]
            rec[f'est_{key}'] = [float(r['estimate'][j]) for j in idx]
        except (ValueError, np.linalg.LinAlgError, FloatingPointError):
            rec[f'V1_{key}'] = None; rec[f'est_{key}'] = None
        if key != 'Q':
            try:
                th, se = pm.model_se(kind, y, X, W[:, 0])
                rec[f'V0_{key}'] = [bool(abs(th[j]-t) <= pm.Z90*se[j]) for j, t in zip(idx, targets[key])]
            except (ValueError, np.linalg.LinAlgError, FloatingPointError):
                rec[f'V0_{key}'] = None
    return rec


def job(args):
    cell, start, stop = args
    targets = json.loads((ROOT/TARGETS).read_text())
    with warnings.catch_warnings(), np.errstate(all='ignore'):
        warnings.simplefilter('ignore')
        return cell, [one_draw(np.random.default_rng([SEED+cell, d]), cell, targets) for d in range(start, stop)]


def summarise(recs, targets):
    cov, failed, bias = {}, {}, {}
    for key in [k for k in recs[0] if k.startswith('V')]:
        vals = [r[key] for r in recs]; failed[key] = sum(v is None for v in vals)
        k = len(targets[key[3:]])
        for j in range(k):
            cov[f'{key}_{j}'] = sum(v[j] for v in vals if v is not None)/len(vals)
    for mdl in MODELS:
        est = [r[f'est_{mdl}'] for r in recs if r[f'est_{mdl}'] is not None]
        if est:
            bias[mdl] = [float(np.mean([e[j] for e in est])-t) for j, t in enumerate(targets[mdl])]
    return dict(coverage=cov, failed=failed, bias=bias)


def run(draws, workers):
    targets = json.loads((ROOT/TARGETS).read_text())
    jobs = [(c, s, min(s+CHUNK, draws)) for c in range(len(CELLS)) for s in range(0, draws, CHUNK)]
    jobs.sort(key=lambda j: -CELLS[j[0]][2])
    recs = {c: [] for c in range(len(CELLS))}
    start = time.time()
    with Pool(workers) as pool:
        for cell, rs in pool.imap_unordered(job, jobs):
            recs[cell].extend(rs)
            print(dict(cell=cell, done=len(recs[cell]), seconds=round(time.time()-start)), flush=True)
    rows = [dict(cell=c, rho=CELLS[c][0], weight_cv=CELLS[c][1], households=CELLS[c][2], draws=len(recs[c]),
                 **summarise(recs[c], targets)) for c in range(len(CELLS))]
    passed = {m: all(v >= .86 for r in rows for k, v in r['coverage'].items() if k.startswith(f'V1_{m}_'))
              for m in MODELS}
    return dict(rows=rows, passed=passed, targets={k: targets[k] for k in MODELS}, draws_per_cell=draws,
                criterion='V1 (SDR replicate variance) 90% coverage >= .86 in every cell for every target of the '
                          'model, judged per model; failed fits count as non-coverage; V0 (model-based SE) is a comparison')


def validate_pins(commit):
    subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'], cwd=ROOT, check=True)
    for rel in FROZEN:
        if subprocess.check_output(['git', 'show', commit+':'+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
            raise ValueError('script/design differs from criterion commit: '+rel)


def write_audit(result, commit):
    out = ROOT/'docs/audits/pums_models_validation'
    result['criterion_commit'] = commit
    result['frozen_sha256'] = {rel: hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() for rel in FROZEN}
    out.with_suffix('.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    lines = ['# Survey-weighted PUMS models: validation (Round 49)', '', result['criterion']+'.', '',
             f"Criterion commit: `{commit}`. {result['draws_per_cell']:,} draws per cell. Models: O ordered logit, P ordered "
             "probit, M multinomial logit, Q median regression, G probit; suffix = target index. Targets: "
             f"`{json.dumps(result['targets'])}`.", '',
             '| ρ | weight CV | households | Coverage | Bias | Failed |', '| ---: | ---: | ---: | :--- | :--- | :--- |']
    for r in result['rows']:
        lines.append(f"| {r['rho']} | {r['weight_cv']} | {r['households']} | "
                     + ', '.join(f'{k} {v:.4f}' for k, v in r['coverage'].items()) + ' | '
                     + ', '.join(f"{k} " + '/'.join(f'{b:+.4f}' for b in v) for k, v in r['bias'].items()) + ' | '
                     + ', '.join(f'{k} {v}' for k, v in r['failed'].items()) + ' |')
    lines += ['', 'Outcomes: `'+json.dumps(result['passed'], sort_keys=True)+'`.']
    out.with_suffix('.md').write_text('\n'.join(lines)+'\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepare-targets', action='store_true'); p.add_argument('--smoke-draws', type=int)
    p.add_argument('--criterion-commit'); p.add_argument('--workers', type=int, default=6)
    a = p.parse_args()
    if a.prepare_targets:
        prepare_targets(); return
    if a.smoke_draws is not None:
        if not 1 <= a.smoke_draws <= 20:
            p.error('smoke draws must be 1..20')
        res = run(a.smoke_draws, a.workers)
        for r in res['rows']:
            print(r['rho'], r['weight_cv'], r['households'], r['coverage'], r['failed'])
        print(res['passed']); return
    if not a.criterion_commit:
        p.error('full run requires --criterion-commit')
    validate_pins(a.criterion_commit)
    if (ROOT/'docs/audits/pums_models_validation.json').exists():
        p.error('refusing to overwrite the full audit')
    write_audit(run(DRAWS, a.workers), a.criterion_commit)


if __name__ == '__main__':
    main()
