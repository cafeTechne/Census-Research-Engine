# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fixed Round 56 validation: PUMS income inequality measures with SDR replicate variance.

Round 32 generator (scripts/pums_tests_validation.py draw_sample: unequal-probability household sample along a
geography, household-correlated person attributes, ACS-style SDR replicate weights); cells rho {.1, .4} x weight
CV {.3, 1.0} x m {800, 3000} households. Incomes: I1 = y1; I2 = y1 ** 1.6; I3 = y1 with zeros where D is true.
Measures (census.pums_inequality_core): I1 and I2 all seven; I3 Gini and top-decile share; I1 Gini(A = 2) -
Gini(A = 0). Targets: population values from 2,000,000 reference households (docs/audits/pums_inequality_targets.json,
committed before the run). Acceptance: coverage >= .86 in every cell per measure and income; failed draws count
as non-coverage; a measure is validated when it passes on every income on which it is judged.

    --prepare               write the targets file (commit it before the run)
    --smoke-draws N         1..50 draws per cell; no files
    --criterion-commit SHA  the full run (2,000 draws per cell)
"""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'scripts'))
import numpy as np  # noqa: E402

from census import pums_inequality_core as pc  # noqa: E402
import pums_tests_validation as PTV  # noqa: E402

SEED = 20280201
DRAWS = 2000
CHUNK = 50
CELLS = PTV.CELLS
TARGETS = 'docs/audits/pums_inequality_targets.json'
FROZEN = ('scripts/pums_inequality_validation.py', 'census/pums_inequality_core.py', 'scripts/pums_tests_validation.py',
          'census/pums_tests.py', 'docs/audits/pums_inequality_validation_criterion.md', TARGETS)
JUDGED = ([('I1', m) for m in pc.MEASURES] + [('I2', m) for m in pc.MEASURES]
          + [('I3', 'gini'), ('I3', 'top10_share'), ('I1', 'gini_diff_A2_A0')])


def incomes(p):
    y1 = p['y1']
    return dict(I1=y1, I2=y1**1.6, I3=np.where(p['D'], 0., y1))


def evaluate(p, W):
    """Dict (income, measure) -> (81,) values."""
    out = {}
    for inc, y in incomes(p).items():
        for m, v in pc.measures(y, W).items():
            out[(inc, m)] = v
    a2, a0 = p['A'] == 2, p['A'] == 0
    out[('I1', 'gini_diff_A2_A0')] = pc.measures(p['y1'][a2], W[a2])['gini']-pc.measures(p['y1'][a0], W[a0])['gini']
    return out


def prepare():
    path = ROOT/TARGETS
    if path.exists():
        raise ValueError('refusing to replace committed targets')
    rng = np.random.default_rng(np.random.SeedSequence([SEED, 2000000]))
    p = PTV.population(rng, rng.uniform(0, 1, 2000000), .25)
    vals = evaluate(p, np.ones((len(p['idx']), 1)))
    targets = {f'{i}|{m}': float(vals[(i, m)][0]) for i, m in JUDGED}
    targets['reference'] = dict(households=2000000, persons=int(len(p['idx'])), seed=[SEED, 2000000], rho=.25,
                                zero_share_I3=float(p['D'].mean()),
                                note='person-level population values at unit weights; marginal distributions do not '
                                     'depend on rho, weights or m')
    path.write_text(json.dumps(targets, indent=2)+'\n')
    print(json.dumps(targets, indent=2))


def job(args):
    cell, start, stop = args
    rho, cv, m = CELLS[cell]
    targets = json.loads((ROOT/TARGETS).read_text())
    sigma = PTV.sigma_for(cv)
    hits = {f'{i}|{k}': 0 for i, k in JUDGED}; fails = dict.fromkeys(hits, 0); est = {k: [] for k in hits}
    for d in range(start, stop):
        rng = np.random.default_rng([SEED+cell, d])
        p, W = PTV.draw_sample(rng, sigma, rho, m)
        try:
            vals = evaluate(p, W)
        except (ValueError, FloatingPointError):
            vals = {}
        for key in hits:
            i, k = key.split('|')
            try:
                s = pc.sdr_summary(vals[(i, k)])
            except (KeyError, ValueError):
                fails[key] += 1; continue
            hits[key] += s['lower'] <= targets[key] <= s['upper']; est[key].append(s['estimate'])
    return cell, hits, fails, {k: (float(np.sum(v)), len(v)) for k, v in est.items()}


def run(draws, workers, chunk):
    tasks = [(c, s, min(s+chunk, draws)) for c in range(len(CELLS)) for s in range(0, draws, chunk)]
    acc = {}; t0 = time.time()
    with ProcessPoolExecutor(workers) as ex:
        for cell, hits, fails, est in ex.map(job, tasks):
            a = acc.setdefault(cell, dict(hits=dict.fromkeys(hits, 0), fails=dict.fromkeys(hits, 0), sum=dict.fromkeys(hits, 0.), n=dict.fromkeys(hits, 0)))
            for k in hits:
                a['hits'][k] += hits[k]; a['fails'][k] += fails[k]; a['sum'][k] += est[k][0]; a['n'][k] += est[k][1]
            print({'cell': cell, 'seconds': round(time.time()-t0)}, flush=True)
    targets = json.loads((ROOT/TARGETS).read_text())
    cells = []
    for c, (rho, cv, m) in enumerate(CELLS):
        a = acc[c]
        cells.append(dict(rho=rho, weight_cv=cv, households=m,
                          coverage={k: a['hits'][k]/draws for k in a['hits']}, failed=a['fails'],
                          bias={k: (a['sum'][k]/a['n'][k]-targets[k] if a['n'][k] else None) for k in a['hits']}))
    passed_key = {k: bool(all(r['coverage'][k] >= .86 for r in cells)) for k in cells[0]['coverage']}
    measures = sorted({k.split('|')[1] for k in passed_key})
    passed = {m: bool(all(v for k, v in passed_key.items() if k.split('|')[1] == m)) for m in measures}
    return dict(cells=cells, passed_by_income=passed_key, passed=passed)


def validate_pins(commit):
    subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'], cwd=ROOT, check=True)
    for rel in FROZEN:
        if subprocess.check_output(['git', 'show', commit+':'+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
            raise SystemExit('script/design differs from criterion commit: '+rel)


def write_audit(result, commit):
    out = ROOT/'docs/audits/pums_inequality_validation'
    result.update(criterion_commit=commit, draws_per_cell=DRAWS, seed=SEED,
                  frozen_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FROZEN})
    out.with_suffix('.json').write_text(json.dumps(result, indent=1)+'\n')
    keys = list(result['cells'][0]['coverage'])
    L = ['# PUMS income inequality measures: validation (Round 56)', '',
         'Round 32 generator (8 cells: rho x weight CV x households); SDR replicate variance, normal 90% interval; '
         'targets are population values (2,000,000 reference households). Pass: coverage >= .86 in every cell per '
         'measure and income.', '',
         f'Criterion commit: `{commit}`. {DRAWS:,} draws per cell.', '',
         '| Income | Measure | Lowest cell | Highest cell | Largest abs. bias | Failed | Passed |',
         '| :--- | :--- | ---: | ---: | ---: | ---: | :--- |']
    for k in keys:
        cov = [r['coverage'][k] for r in result['cells']]
        bias = [abs(r['bias'][k]) for r in result['cells'] if r['bias'][k] is not None]
        fail = sum(r['failed'][k] for r in result['cells'])
        i, m = k.split('|')
        L.append(f"| {i} | {m} | {min(cov):.4f} | {max(cov):.4f} | {max(bias) if bias else float('nan'):.4f} | {fail} | "
                 f"{result['passed_by_income'][k]} |")
    L += ['', '| Cell (rho, weight CV, households) | ' + ' | '.join(keys) + ' |', '| :--- |' + ' ---: |'*len(keys)]
    for r in result['cells']:
        L.append(f"| {r['rho']}, {r['weight_cv']}, {r['households']} | " + ' | '.join(f"{r['coverage'][k]:.3f}" for k in keys) + ' |')
    L += ['', f"Outcomes by measure: `{json.dumps(result['passed'], sort_keys=True)}`.", '']
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
            print({k: round(v, 3) for k, v in c['coverage'].items()})
        print(r['passed'])
        return
    if not a.criterion_commit:
        ap.error('full run requires --criterion-commit')
    validate_pins(a.criterion_commit)
    write_audit(run(DRAWS, a.workers, a.chunk), a.criterion_commit)


if __name__ == '__main__':
    main()
