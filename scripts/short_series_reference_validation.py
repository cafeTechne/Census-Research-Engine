# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fixed Round 55 validation: interrupted series below 30 points (I) and SMRs with an estimated reference
population (R). Frozen with the criterion.

I: Round 48 generator (mci_core.its_design, interruption at n//2 + 1, AR(1) errors with unit innovations, level
   change 1 and slope change .2), n in {15, 20, 25} x phi in {.3, .6}. I2 = small_spatial_core.its_bootstrap_t
   (Round 48; comparison), I3 = its_small_core.its_bootstrap_t_bc, I4 = its_small_core.its_ewc. Validated down
   to the smallest n where both changes cover >= .86 for both phi there and at every larger tested n.
R: five bands, Round 24 rates as truth; reference person-years P_b with D/5 expected deaths per band; reference
   deaths D_b ~ Poisson(rate_b P_b); observed reference population P_b (1 + c z_b) with SE c P_b(observed);
   estimated rates D_b / P_b(observed); study bands equal, scaled so the true expected count is E; O ~
   Poisson(1.2 E). R1 = indirect_standardize(reference_counts=D, reference_population_se=...), R0 = without the
   population SE. Cells D in {50, 500} x c in {.02, .08} x E in {10, 100}. R1 passes with coverage of 1.2 >= .86
   in all eight cells; refused draws and O = 0 count as non-coverage.

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
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from census import its_small_core as isc  # noqa: E402
from census import mci_core as mi  # noqa: E402
from census import small_spatial_core as sc  # noqa: E402
from census.standardize import indirect_standardize  # noqa: E402

SEED = 20280101
DRAWS = 2000
CHUNK = 50
RATES = np.array([.0005, .001, .003, .01, .04])
CELLS = ([('I', dict(n=n, phi=phi)) for n in (15, 20, 25) for phi in (.3, .6)]
         + [('R', dict(deaths=d, c=c, expected=e)) for d in (50, 500) for c in (.02, .08) for e in (10, 100)])
FROZEN = ('scripts/short_series_reference_validation.py', 'census/its_small_core.py', 'census/small_spatial_core.py',
          'census/mci_core.py', 'census/standardize.py', 'docs/audits/short_series_reference_validation_criterion.md')
ERRORS = (ValueError, np.linalg.LinAlgError, FloatingPointError, RuntimeError)


def i_draws(cell, start, stop):
    _, par = CELLS[cell]
    n, phi = par['n'], par['phi']
    X = mi.its_design(n, n//2+1)
    out = {k: [0, 0, 0] for k in ('I2', 'I3', 'I4')}     # level covered, slope covered, failed
    for draw in range(start, stop):
        rng = np.random.default_rng([SEED+cell, draw])
        e = rng.standard_normal(n); u = np.empty(n); u[0] = e[0]/np.sqrt(1-phi**2)
        for t in range(1, n):
            u[t] = phi*u[t-1]+e[t]
        y = X @ np.array([0., 0., 1., .2])+u
        for key in out:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore')
                    res = (sc.its_bootstrap_t(y, X, rng)[0] if key == 'I2' else
                           isc.its_bootstrap_t_bc(y, X, rng)[0] if key == 'I3' else isc.its_ewc(y, X))
                if not all(np.isfinite([r['lower'], r['upper']]).all() for r in res):
                    raise ValueError('nonfinite interval')
                out[key][0] += res[0]['lower'] <= 1. <= res[0]['upper']
                out[key][1] += res[1]['lower'] <= .2 <= res[1]['upper']
            except ERRORS:
                out[key][2] += 1
    return out


def r_draws(cell, start, stop):
    _, par = CELLS[cell]
    D, c, E = par['deaths'], par['c'], par['expected']
    P = (D/5)/RATES
    pop = np.repeat(E/RATES.sum(), 5)
    frame = pd.DataFrame([pop], index=['synthetic'])
    out = {k: [0, 0, 0] for k in ('R1', 'R0')}           # covered, refused, zero O
    for draw in range(start, stop):
        rng = np.random.default_rng([SEED+cell, draw])
        deaths = rng.poisson(RATES*P).astype(float)
        p_obs = P*(1+c*rng.standard_normal(5))
        o = int(rng.poisson(1.2*E))
        obs = pd.Series([o], index=frame.index)
        for key in out:
            try:
                if (deaths <= 0).any() or (p_obs <= 0).any():
                    raise ValueError('zero reference deaths or nonpositive population')
                kw = dict(reference_counts=deaths)
                if key == 'R1':
                    kw['reference_population_se'] = c*p_obs
                row = indirect_standardize(obs, frame, deaths/p_obs, None, **kw).iloc[0]
            except ERRORS:
                out[key][1] += 1
                continue
            out[key][2] += o == 0
            out[key][0] += bool(o > 0 and row.smr_lower <= 1.2 <= row.smr_upper)
    return out


def job(args):
    cell, start, stop = args
    return cell, (i_draws if CELLS[cell][0] == 'I' else r_draws)(cell, start, stop)


def run(draws, workers, chunk):
    tasks = [(c, s, min(s+chunk, draws)) for c in range(len(CELLS)) for s in range(0, draws, chunk)]
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
            cells.append(dict(problem='R', **par, coverage={k: v[0]/draws for k, v in a.items()},
                              refused={k: v[1] for k, v in a.items()}, zero_o={k: v[2] for k, v in a.items()}))
    passed = {}
    for key in ('I2', 'I3', 'I4'):
        ok_n = {}
        for n in (15, 20, 25):
            sel = [r for r in cells if r['problem'] == 'I' and r['n'] == n]
            ok_n[n] = all(min(r['coverage'][key].values()) >= .86 for r in sel)
        min_n = None
        for n in (25, 20, 15):
            if ok_n[n]:
                min_n = n
            else:
                break
        passed[f'{key}_min_n'] = min_n
    passed['R1'] = bool(all(r['coverage']['R1'] >= .86 for r in cells if r['problem'] == 'R'))
    passed['R0'] = bool(all(r['coverage']['R0'] >= .86 for r in cells if r['problem'] == 'R'))
    return dict(cells=cells, passed=passed)


def validate_pins(commit):
    subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'], cwd=ROOT, check=True)
    for rel in FROZEN:
        if subprocess.check_output(['git', 'show', commit+':'+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
            raise SystemExit('script/design differs from criterion commit: '+rel)


def write_audit(result, commit):
    out = ROOT/'docs/audits/short_series_reference_validation'
    result.update(criterion_commit=commit, draws_per_cell=DRAWS, seed=SEED,
                  frozen_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FROZEN})
    out.with_suffix('.json').write_text(json.dumps(result, indent=1)+'\n')
    L = ['# Short interrupted series and estimated reference populations: validation (Round 55)', '',
         'I: AR(1) series of 15-25 points; I2 Round 48 bootstrap-t (comparison), I3 bootstrap-t at a bias-corrected '
         'AR coefficient, I4 EWC HAR t test; validated down to the smallest n where both changes cover >= .86 for '
         'both phi there and at every larger n. R: SMR with an estimated reference population; R1 adds the '
         'population SE, R0 does not; R1 passes with >= .86 in all eight cells.', '',
         f'Criterion commit: `{commit}`. {DRAWS:,} draws per cell.', '',
         '| n | phi | I2 level / slope | I3 level / slope | I4 level / slope | Failed (I2/I3/I4) |',
         '| ---: | ---: | :--- | :--- | :--- | :--- |']
    for r in result['cells']:
        if r['problem'] == 'I':
            cv = ' | '.join(f"{r['coverage'][k]['level']:.4f} / {r['coverage'][k]['slope']:.4f}" for k in ('I2', 'I3', 'I4'))
            L.append(f"| {r['n']} | {r['phi']} | {cv} | {r['failed']['I2']}/{r['failed']['I3']}/{r['failed']['I4']} |")
    L += ['', '| Reference deaths | Population CV | E | R1 | R0 | Refused (R1/R0) | O = 0 |', '| ---: | ---: | ---: | ---: | ---: | :--- | ---: |']
    for r in result['cells']:
        if r['problem'] == 'R':
            L.append(f"| {r['deaths']} | {r['c']} | {r['expected']} | {r['coverage']['R1']:.4f} | {r['coverage']['R0']:.4f} | "
                     f"{r['refused']['R1']}/{r['refused']['R0']} | {r['zero_o']['R1']} |")
    L += ['', f"Outcomes: `{json.dumps(result['passed'], sort_keys=True)}`.", '']
    out.with_suffix('.md').write_text('\n'.join(L))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--smoke-draws', type=int)
    ap.add_argument('--criterion-commit')
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--chunk', type=int, default=CHUNK, help='draws per task (seeds are per draw; results do not depend on it)')
    a = ap.parse_args()
    if a.smoke_draws is not None:
        if not 1 <= a.smoke_draws <= 50:
            ap.error('smoke draws must be 1..50')
        r = run(a.smoke_draws, a.workers, max(1, min(a.chunk, a.smoke_draws)))
        for c in r['cells']:
            print(c)
        print(r['passed'])
        return
    if not a.criterion_commit:
        ap.error('full run requires --criterion-commit')
    validate_pins(a.criterion_commit)
    write_audit(run(DRAWS, a.workers, a.chunk), a.criterion_commit)


if __name__ == '__main__':
    main()
