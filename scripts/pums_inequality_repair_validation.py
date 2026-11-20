# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fixed Round 60 validation: repaired intervals for Theil T, Atkinson (.5, 1) and the top-decile share (PUMS).

Round 56's generator (scripts/pums_tests_validation.py draw_sample), cells, incomes (I1 = y1, I2 = y1 ** 1.6,
I3 = y1 with zeros where D) and targets (docs/audits/pums_inequality_targets.json). Judged: Theil T and Atkinson
.5/1 on I1 and I2; top-decile share on I1, I2 and I3. Procedures: T0 = Round 56 normal interval (comparison);
T1 = transformed SDR interval (log Theil, logit Atkinson / top share); T2 = Round 50 SDR bias correction
theta - 4 (mean theta_r - theta), then T1's interval around it. Acceptance per measure and procedure: coverage
>= .86 in every cell on every income judged (T1 preferred to T2); else, if a procedure passes in every m = 3000
cell, it is validated with a sample gate of 7,000 unweighted records; else exploratory. Failed draws count as
non-coverage.

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
import pums_inequality_validation as R56  # noqa: E402

SEED = 20280601
DRAWS = 2000
CHUNK = 50
CELLS = PTV.CELLS
TARGETS = 'docs/audits/pums_inequality_targets.json'
JUDGED = ([(i, m) for i in ('I1', 'I2') for m in ('theil_t', 'atkinson_0.5', 'atkinson_1', 'top10_share')]
          + [('I3', 'top10_share')])
PROCS = ('T0', 'T1', 'T2')
FROZEN = ('scripts/pums_inequality_repair_validation.py', 'scripts/pums_inequality_validation.py',
          'census/pums_inequality_core.py', 'scripts/pums_tests_validation.py', 'census/pums_tests.py',
          'docs/audits/pums_inequality_repair_validation_criterion.md', TARGETS)


def intervals(theta, measure):
    kind = pc.TRANSFORM[measure]
    out = {'T0': pc.sdr_summary(theta)}
    out['T1'] = pc.transformed_summary(theta, kind)
    out['T2'] = pc.transformed_summary(theta, kind, center=pc.bias_corrected(theta))
    return out


def job(args):
    cell, start, stop = args
    rho, cv, m = CELLS[cell]
    targets = json.loads((ROOT/TARGETS).read_text())
    sigma = PTV.sigma_for(cv)
    keys = [f'{i}|{k}|{p}' for i, k in JUDGED for p in PROCS]
    hits = dict.fromkeys(keys, 0); fails = dict.fromkeys(keys, 0)
    for d in range(start, stop):
        rng = np.random.default_rng([SEED+cell, d])
        p, W = PTV.draw_sample(rng, sigma, rho, m)
        try:
            vals = R56.evaluate(p, W)
        except (ValueError, FloatingPointError):
            vals = {}
        for i, k in JUDGED:
            tgt = targets[f'{i}|{k}']
            try:
                ivs = intervals(vals[(i, k)], k)
            except (KeyError, ValueError, FloatingPointError):
                for pr in PROCS:
                    fails[f'{i}|{k}|{pr}'] += 1
                continue
            for pr, s in ivs.items():
                hits[f'{i}|{k}|{pr}'] += s['lower'] <= tgt <= s['upper']
    return cell, hits, fails


def run(draws, workers, chunk):
    tasks = [(c, s, min(s+chunk, draws)) for c in range(len(CELLS)) for s in range(0, draws, chunk)]
    acc = {}; t0 = time.time()
    with ProcessPoolExecutor(workers) as ex:
        for cell, hits, fails in ex.map(job, tasks):
            a = acc.setdefault(cell, dict(hits=dict.fromkeys(hits, 0), fails=dict.fromkeys(hits, 0)))
            for k in hits:
                a['hits'][k] += hits[k]; a['fails'][k] += fails[k]
            print({'cell': cell, 'seconds': round(time.time()-t0)}, flush=True)
    cells = [dict(rho=rho, weight_cv=cv, households=m, coverage={k: acc[c]['hits'][k]/draws for k in acc[c]['hits']},
                  failed=acc[c]['fails']) for c, (rho, cv, m) in enumerate(CELLS)]
    measures = sorted({k for _, k in JUDGED})
    passed = {}
    for meas in measures:
        incomes = [i for i, k in JUDGED if k == meas]
        res = {}
        for pr in PROCS:
            keys = [f'{i}|{meas}|{pr}' for i in incomes]
            res[pr] = dict(all=bool(all(r['coverage'][k] >= .86 for r in cells for k in keys)),
                           large=bool(all(r['coverage'][k] >= .86 for r in cells if r['households'] == 3000 for k in keys)))
        choice = next((pr for pr in ('T1', 'T2') if res[pr]['all']), None)
        gate = None
        if choice is None:
            choice = next((pr for pr in ('T1', 'T2') if res[pr]['large']), None)
            gate = 7000 if choice else None
        passed[meas] = dict(procedure=choice, min_records=gate, detail=res)
    return dict(cells=cells, passed=passed)


def validate_pins(commit):
    subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'], cwd=ROOT, check=True)
    for rel in FROZEN:
        if subprocess.check_output(['git', 'show', commit+':'+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
            raise SystemExit('script/design differs from criterion commit: '+rel)


def write_audit(result, commit):
    out = ROOT/'docs/audits/pums_inequality_repair_validation'
    result.update(criterion_commit=commit, draws_per_cell=DRAWS, seed=SEED,
                  frozen_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FROZEN})
    out.with_suffix('.json').write_text(json.dumps(result, indent=1)+'\n')
    keys = list(result['cells'][0]['coverage'])
    L = ['# PUMS inequality repairs: validation (Round 60)', '',
         'Round 56 generator, cells, incomes and targets. T0 Round 56 normal interval (comparison); T1 transformed SDR '
         'interval (log Theil, logit Atkinson and top share); T2 SDR bias correction then T1. Pass: coverage >= .86 in '
         'every cell on every income; else a 7,000-record gate if every m = 3000 cell passes.', '',
         f'Criterion commit: `{commit}`. {DRAWS:,} draws per cell.', '',
         '| Income | Measure | Procedure | Lowest cell | Lowest m = 3000 cell | Highest cell | Failed |',
         '| :--- | :--- | :--- | ---: | ---: | ---: | ---: |']
    for k in keys:
        i, meas, pr = k.split('|')
        cov = [r['coverage'][k] for r in result['cells']]
        big = [r['coverage'][k] for r in result['cells'] if r['households'] == 3000]
        L.append(f"| {i} | {meas} | {pr} | {min(cov):.4f} | {min(big):.4f} | {max(cov):.4f} | "
                 f"{sum(r['failed'][k] for r in result['cells'])} |")
    L += ['', '| Measure | Validated procedure | Record gate |', '| :--- | :--- | :--- |']
    for meas, v in result['passed'].items():
        L.append(f"| {meas} | {v['procedure']} | {v['min_records']} |")
    L += ['', f"Outcomes: `{json.dumps({k: [v['procedure'], v['min_records']] for k, v in result['passed'].items()}, sort_keys=True)}`.", '']
    out.with_suffix('.md').write_text('\n'.join(L))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--smoke-draws', type=int)
    ap.add_argument('--criterion-commit')
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--chunk', type=int, default=CHUNK)
    a = ap.parse_args()
    if a.smoke_draws is not None:
        if not 1 <= a.smoke_draws <= 50:
            ap.error('smoke draws must be 1..50')
        r = run(a.smoke_draws, a.workers, max(1, min(a.chunk, a.smoke_draws)))
        print(json.dumps({k: [v['procedure'], v['min_records']] for k, v in r['passed'].items()}))
        return
    if not a.criterion_commit:
        ap.error('full run requires --criterion-commit')
    validate_pins(a.criterion_commit)
    write_audit(run(DRAWS, a.workers, a.chunk), a.criterion_commit)


if __name__ == '__main__':
    main()
