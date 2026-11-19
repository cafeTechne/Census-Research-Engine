# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fixed Round 38 validation: pooled intervals, TOST and z-test power.

    --smoke-draws N         1..20 draws per cell; no files
    --criterion-commit SHA  the full run (2,000 draws per meta cell; 20,000 per TOST/power setting)
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from census import evidence_core as ev

SEED = 20270204
FROZEN = ('scripts/evidence_validation.py', 'census/evidence_core.py', 'docs/audits/evidence_validation_criterion.md')
META = [(k, het) for k in (2, 4, 8) for het in (False, True)]


def est_se(rng, s):
    return s*np.sqrt(rng.chisquare(80, np.shape(s))/80)


def run(draws, tost_draws):
    rows = []
    for cell, (k, het) in enumerate(META):
        rng = np.random.default_rng(SEED+cell)
        s = rng.lognormal(0, .5, k); tau2 = float(np.mean(s**2)) if het else 0.
        cover = {m: 0 for m in ('fixed', 'dl', 'hksj')}
        for _ in range(draws):
            theta = rng.normal(0, np.sqrt(tau2), k)+rng.normal(0, s)
            sh = est_se(rng, s)
            for m in cover:
                r = ev.pooled(theta, sh, m); cover[m] += r['lower'] <= 0 <= r['upper']
        rows.append(dict(cell=cell, k=k, heterogeneous=het, draws=draws, coverage={m: c/draws for m, c in cover.items()}))
        print(rows[-1], flush=True)
    tost_rows = []
    for i, (s1, s2) in enumerate(((1., 1.), (1., 2.))):
        rng = np.random.default_rng(SEED+100+i); margin = 3.
        size = power0 = 0
        for _ in range(tost_draws):
            e1 = rng.normal(0, s1); e2 = rng.normal(margin, s2)                 # true difference at the margin
            size += ev.tost(e1, est_se(rng, s1), e2, est_se(rng, s2), margin)['equivalent']
            f1 = rng.normal(0, s1); f2 = rng.normal(0, s2)
            power0 += ev.tost(f1, est_se(rng, s1), f2, est_se(rng, s2), margin)['equivalent']
        tost_rows.append(dict(se=(s1, s2), margin=margin, size=size/tost_draws, power_at_zero=power0/tost_draws))
        print(tost_rows[-1], flush=True)
    power_rows = []
    for j, (target, alpha) in enumerate(((.5, .10), (.8, .10), (.5, .05), (.8, .05))):
        rng = np.random.default_rng(SEED+200+j); s = 1.
        effect = ev.mde_z(s, target, alpha)
        rej = 0
        for _ in range(tost_draws):
            e = rng.normal(effect, s); sh = est_se(rng, s)
            rej += abs(e/sh) > __import__('scipy').stats.norm.ppf(1-alpha/2)
        power_rows.append(dict(predicted=ev.power_z(effect, s, alpha), alpha=alpha, empirical=rej/tost_draws))
        print(power_rows[-1], flush=True)
    passed = {}
    for k in (2, 4, 8):
        sel = [r for r in rows if r['k'] == k]
        passed[f'fixed/k{k}'] = all(r['coverage']['fixed'] >= .86 for r in sel if not r['heterogeneous'])
        for m in ('dl', 'hksj'):
            passed[f'{m}/k{k}'] = all(r['coverage'][m] >= .86 for r in sel)
    passed['tost'] = all(r['size'] <= .07 for r in tost_rows)
    passed['power'] = all(abs(r['predicted']-r['empirical']) <= .03 for r in power_rows)
    return dict(meta=rows, tost=tost_rows, power=power_rows, passed=passed, draws_per_meta_cell=draws, draws_per_setting=tost_draws,
                criterion='pooled: 90% coverage >= .86 per k (fixed only without heterogeneity; dl, hksj in all cells); '
                          'TOST: size at the margin <= .07 (nominal .05); power: |predicted - empirical| <= .03')


def validate_pins(commit):
    subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'], cwd=ROOT, check=True)
    for rel in FROZEN:
        if subprocess.check_output(['git', 'show', commit+':'+rel], cwd=ROOT) != (ROOT/rel).read_bytes():
            raise ValueError('script/design differs from criterion commit: '+rel)


def write_audit(result, commit):
    out = ROOT/'docs/audits/evidence_validation'
    result['criterion_commit'] = commit
    result['frozen_sha256'] = {rel: hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() for rel in FROZEN}
    out.with_suffix('.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    lines = ['# Combining evidence: validation (Round 38)', '', result['criterion']+'.', '',
             f"Criterion commit: `{commit}`.", '', '| k | heterogeneity | fixed | DerSimonian–Laird | Paule–Mandel + HKSJ |', '| ---: | :--- | ---: | ---: | ---: |']
    for r in result['meta']:
        c = r['coverage']; lines.append(f"| {r['k']} | {r['heterogeneous']} | {c['fixed']:.4f} | {c['dl']:.4f} | {c['hksj']:.4f} |")
    lines += ['', '| TOST SEs | margin | size at margin | power at 0 |', '| :--- | ---: | ---: | ---: |']
    for r in result['tost']:
        lines.append(f"| {r['se']} | {r['margin']} | {r['size']:.4f} | {r['power_at_zero']:.4f} |")
    lines += ['', '| α | predicted power | empirical |', '| ---: | ---: | ---: |']
    for r in result['power']:
        lines.append(f"| {r['alpha']} | {r['predicted']:.3f} | {r['empirical']:.4f} |")
    lines += ['', 'Outcomes: `'+json.dumps(result['passed'], sort_keys=True)+'`.']
    out.with_suffix('.md').write_text('\n'.join(lines)+'\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--smoke-draws', type=int); p.add_argument('--criterion-commit')
    a = p.parse_args()
    if a.smoke_draws is not None:
        if not 1 <= a.smoke_draws <= 20:
            p.error('smoke draws must be 1..20')
        run(a.smoke_draws, a.smoke_draws); return
    if not a.criterion_commit:
        p.error('full run requires --criterion-commit')
    validate_pins(a.criterion_commit)
    if (ROOT/'docs/audits/evidence_validation.json').exists():
        p.error('refusing to overwrite the full audit')
    write_audit(run(2000, 20000), a.criterion_commit)


if __name__ == '__main__':
    main()
