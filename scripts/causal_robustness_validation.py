# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fixed Round 47 validation: noisy same-sign confounders (T), weak instruments (W), error-prone mediator (S),
two incomplete covariates (D).

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
sys.path.insert(0, str(ROOT))
import numpy as np
from scipy import stats
from scipy.optimize import brentq
from scipy.special import expit
from census import causal_core as cc
from census import causal_robustness_core as cr

SEED = 20270501
DRAWS = 2000
CHUNK = 250
N = 145
CELLS = ([('T', dict(reliability=r, rho=rho)) for r in (.9, .8, .7) for rho in (0., .3)]
         + [('W', dict(expected_f=f, reliability=r)) for r in (.9, .7) for f in (2, 5, 10, 20, 30)]
         + [('S', dict(reliability=r, b=b)) for r in (.9, .8, .7) for b in (.5, .25)]
         + [('D', dict(mechanism=mech, fraction=f)) for mech in ('MCAR', 'MAR') for f in (.2, .4)])
BINS = (0, 5, 10, 20)
MIN_BIN = 200
FROZEN = ('scripts/causal_robustness_validation.py', 'census/causal_robustness_core.py', 'census/causal_core.py',
          'docs/audits/causal_robustness_validation_criterion.md')


def error_sd(rng, n, var):
    """Heteroscedastic error SDs (lognormal, log-SD .5) scaled so mean(s^2) = var."""
    s = rng.lognormal(0, .5, n)
    return s*np.sqrt(var/np.mean(s**2))


def draw_t(rng, par):
    z = rng.standard_normal((N, 2)); rho = par['rho']
    z[:, 1] = rho*z[:, 0]+np.sqrt(1-rho**2)*z[:, 1]
    T = rng.binomial(1, expit(.5*z[:, 0]+.5*z[:, 1])).astype(float)
    y = 1+.5*T+.5*z[:, 0]+.5*z[:, 1]+rng.standard_normal(N)
    var = (1-par['reliability'])/par['reliability']
    s = np.column_stack([error_sd(rng, N, var) for _ in range(2)])
    W = z+rng.standard_normal((N, 2))*s
    rec = {}
    for key in ('T0', 'T1'):
        try:
            if min(T.sum(), N-T.sum()) < 10:
                raise ValueError('small treatment group')
            r = cc.treatment_effect(y, T, W, 'aipw') if key == 'T0' else cr.aipw_calibrated(y, T, W, s**2, rng)
            rec[key] = (bool(r['lower'] <= .5 <= r['upper']), r['estimate'])
        except (ValueError, np.linalg.LinAlgError):
            rec[key] = None
    return rec


def draw_w(rng, par):
    rel = par['reliability']; lam = par['expected_f']-1
    r2 = lam/(N-2+lam); pi = np.sqrt(r2/rel)          # first-stage R^2 of observed x on z = pi^2 * rel
    z = rng.standard_normal(N)
    xs = pi*z+np.sqrt(1-pi**2)*rng.standard_normal(N)
    x = xs+rng.standard_normal(N)*np.sqrt((1-rel)/rel)
    y = 1+.5*xs+rng.standard_normal(N)
    rec = dict(F=cc_first_stage_f(x, z))
    try:
        r = cc.iv_2sls(y, x, z); rec['W1'] = (bool(r['lower'] <= .5 <= r['upper']), r['estimate'])
    except (ValueError, np.linalg.LinAlgError):
        rec['W1'] = None
    try:
        ar = cr.anderson_rubin(y, x, z); rec['W2'] = (bool(cr.ar_covers(ar, .5)), None); rec['kind'] = ar['kind']
    except (ValueError, np.linalg.LinAlgError):
        rec['W2'] = None; rec['kind'] = 'failed'
    return rec


def cc_first_stage_f(x, z):
    zc, xc = z-z.mean(), x-x.mean()
    g = (zc @ xc)/(zc @ zc); ssr = xc @ xc-g*g*(zc @ zc)
    return float(g*g*(zc @ zc)/(ssr/(N-2)))


def draw_s(rng, par):
    rel, b = par['reliability'], par['b']
    x = rng.standard_normal(N); m = .4*x+rng.standard_normal(N)
    y = .3*x+b*m+rng.standard_normal(N)
    s = error_sd(rng, N, 1.16*(1-rel)/rel)
    w = m+rng.standard_normal(N)*s
    rec = {}
    for key in ('S0', 'S1'):
        try:
            r = cc.mediation(x, w, y, 'bootstrap', rng, draws=400) if key == 'S0' else cr.mediation_calibrated(x, w, s**2, y, rng)
            rec[key] = (bool(r['lower'] <= .4*b <= r['upper']), r['estimate'])
        except (ValueError, np.linalg.LinAlgError):
            rec[key] = None
    return rec


def draw_d(rng, par):
    x = rng.standard_normal((N, 2)); x[:, 1] = .5*x[:, 0]+np.sqrt(.75)*x[:, 1]
    y = 1+.5*x[:, 0]+.5*x[:, 1]+rng.standard_normal(N)*np.sqrt(.75)
    f = par['fraction']
    if par['mechanism'] == 'MCAR':
        miss = rng.random((N, 2)) < f
    else:
        ys = (y-y.mean())/y.std()
        c = brentq(lambda c: expit(c+ys).mean()-f, -20, 20)
        miss = rng.random((N, 2)) < expit(c+ys)[:, None]
    X = np.column_stack((np.ones(N), x)); X[:, 1][miss[:, 0]] = np.nan; X[:, 2][miss[:, 1]] = np.nan
    rec = {}
    try:
        res = cr.chained_mi(y, X, [1, 2], rng)
        rec['D1'] = [(bool(r['lower'] <= .5 <= r['upper']), r['estimate']) for r in res[1:]]
    except (ValueError, np.linalg.LinAlgError):
        rec['D1'] = None
    try:
        cc_rows = ~miss.any(axis=1); Xc, yc = X[cc_rows], y[cc_rows]
        if len(yc) < 10:
            raise ValueError('too few complete cases')
        b, v = cr._hc3(Xc, yc); t = stats.t.ppf(.95, len(yc)-3)
        rec['D0'] = [(bool(b[j]-t*np.sqrt(v[j]) <= .5 <= b[j]+t*np.sqrt(v[j])), b[j]) for j in (1, 2)]
    except (ValueError, np.linalg.LinAlgError):
        rec['D0'] = None
    return rec


DRAW = dict(T=draw_t, W=draw_w, S=draw_s, D=draw_d)


def job(args):
    cell, start, stop = args
    kind, par = CELLS[cell]
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        return cell, [DRAW[kind](np.random.default_rng([SEED+cell, d]), par) for d in range(start, stop)]


def summarise(kind, par, recs):
    keys = {'T': ('T0', 'T1'), 'W': ('W1', 'W2'), 'S': ('S0', 'S1'), 'D': ('D0', 'D1')}[kind]
    target = {'T': .5, 'W': .5, 'S': .4*par.get('b', 0), 'D': .5}[kind]
    cov, bias, failed = {}, {}, {}
    for k in keys:
        if kind == 'D':
            for j, name in ((0, 'x1'), (1, 'x2')):
                ok = [r[k][j] for r in recs if r[k] is not None]
                cov[f'{k}_{name}'] = sum(c for c, _ in ok)/len(recs)
                bias[f'{k}_{name}'] = float(np.mean([e for _, e in ok])-target) if ok else None
        else:
            ok = [r[k] for r in recs if r[k] is not None]
            cov[k] = sum(c for c, _ in ok)/len(recs)
            est = [e for _, e in ok if e is not None]
            bias[k] = float(np.mean(est)-target) if est else None
        failed[k] = sum(r[k] is None for r in recs)
    row = dict(coverage=cov, bias=bias, failed=failed)
    if kind == 'W':
        row['mean_first_stage_f'] = float(np.mean([r['F'] for r in recs]))
        row['ar_kinds'] = {k: sum(r['kind'] == k for r in recs) for k in ('bounded', 'disjoint', 'real_line', 'empty', 'failed')}
    return row


def bins(cells_recs):
    """Pool W draws within reliability; coverage by observed first-stage F bin."""
    out = {}
    for rel in (.9, .7):
        recs = [r for (kind, par), rs in cells_recs if kind == 'W' and par['reliability'] == rel for r in rs]
        for lo, hi in zip(BINS, BINS[1:]+(np.inf,)):
            sel = [r for r in recs if lo <= r['F'] < hi]
            out[f'rel{rel}_F{lo}'] = dict(
                draws=len(sel), **{k: (sum(r[k][0] for r in sel if r[k] is not None)/len(sel) if sel else None)
                                   for k in ('W1', 'W2')})
    return out


def run(draws, workers):
    jobs = [(c, s, min(s+CHUNK, draws)) for c in range(len(CELLS)) for s in range(0, draws, CHUNK)]
    recs = {c: [] for c in range(len(CELLS))}
    start = time.time()
    with Pool(workers) as pool:
        for cell, rs in pool.imap_unordered(job, jobs):
            recs[cell].extend(rs)
            print(dict(cell=cell, done=len(recs[cell]), seconds=round(time.time()-start)), flush=True)
    rows = [dict(cell=c, kind=CELLS[c][0], parameters=CELLS[c][1], draws=len(recs[c]),
                 **summarise(*CELLS[c], recs[c])) for c in range(len(CELLS))]
    fbins = bins([(CELLS[c], recs[c]) for c in range(len(CELLS))])
    ok = lambda b, k: b['draws'] >= MIN_BIN and b[k] >= .86
    passed = dict(
        T1=all(r['coverage']['T1'] >= .86 for r in rows if r['kind'] == 'T'),
        S1=all(r['coverage']['S1'] >= .86 for r in rows if r['kind'] == 'S'),
        D1=all(v >= .86 for r in rows if r['kind'] == 'D' for k, v in r['coverage'].items() if k.startswith('D1')),
        W2=all(ok(b, 'W2') for b in fbins.values()))
    cutoff = None
    for lo in reversed(BINS):
        if all(ok(fbins[f'rel{rel}_F{e}'], 'W1') for rel in (.9, .7) for e in BINS if e >= lo):
            cutoff = lo
        else:
            break
    passed['W1_cutoff_f'] = cutoff
    return dict(rows=rows, f_bins=fbins, passed=passed, draws_per_cell=draws,
                criterion='90% coverage >= .86 (failed fits count as non-coverage): T1, S1 in every cell; D1 in every '
                          'cell for both slopes; W2 in every observed-F bin of both reliabilities (bins need >= 200 '
                          'draws); W1 cut-off = smallest bin edge with W1 >= .86 there and above in both reliabilities')


def validate_pins(commit):
    subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'], cwd=ROOT, check=True)
    for rel in FROZEN:
        if subprocess.check_output(['git', 'show', commit+':'+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
            raise ValueError('script/design differs from criterion commit: '+rel)


def fmt(d, f):
    return ', '.join(f"{k} {f.format(v)}" if v is not None else f"{k} -" for k, v in d.items())


def write_audit(result, commit):
    out = ROOT/'docs/audits/causal_robustness_validation'
    result['criterion_commit'] = commit
    result['frozen_sha256'] = {rel: hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() for rel in FROZEN}
    out.with_suffix('.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    lines = ['# Causal and missing-data robustness: validation (Round 47)', '', result['criterion']+'.', '',
             f"Criterion commit: `{commit}`. {result['draws_per_cell']:,} draws per cell.", '',
             '| Problem | Setting | Coverage | Bias | Failed |', '| :--- | :--- | :--- | :--- | :--- |']
    for r in result['rows']:
        setting = ', '.join(f'{k} {v}' for k, v in r['parameters'].items())
        if r['kind'] == 'W':
            setting += f", mean F {r['mean_first_stage_f']:.1f}, AR {fmt(r['ar_kinds'], '{}')}"
        lines.append(f"| {r['kind']} | {setting} | {fmt(r['coverage'], '{:.4f}')} | {fmt(r['bias'], '{:+.4f}')} | "
                     f"{fmt(r['failed'], '{}')} |")
    lines += ['', '## Weak instruments by observed first-stage F (pooled within reliability)', '',
              '| Bin | Draws | W1 2SLS Wald | W2 Anderson–Rubin |', '| :--- | ---: | :--- | :--- |']
    for k, b in result['f_bins'].items():
        cells = ['-' if b[w] is None else f'{b[w]:.4f}' for w in ('W1', 'W2')]
        lines.append(f"| {k} | {b['draws']} | {cells[0]} | {cells[1]} |")
    lines += ['', 'Outcomes: `'+json.dumps(result['passed'], sort_keys=True)+'`.']
    out.with_suffix('.md').write_text('\n'.join(lines)+'\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--smoke-draws', type=int); p.add_argument('--criterion-commit'); p.add_argument('--workers', type=int, default=6)
    a = p.parse_args()
    if a.smoke_draws is not None:
        if not 1 <= a.smoke_draws <= 20:
            p.error('smoke draws must be 1..20')
        res = run(a.smoke_draws, a.workers)
        for r in res['rows']:
            print(r['kind'], r['parameters'], r['coverage'], r['failed'])
        print(res['f_bins']); print(res['passed']); return
    if not a.criterion_commit:
        p.error('full run requires --criterion-commit')
    validate_pins(a.criterion_commit)
    if (ROOT/'docs/audits/causal_robustness_validation.json').exists():
        p.error('refusing to overwrite the full audit')
    write_audit(run(DRAWS, a.workers), a.criterion_commit)


if __name__ == '__main__':
    main()
