#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pre-specified Round 24 SMR validation; --smoke-draws 1..20 never writes audits."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from census.simulation import make_replicates
from census.standardize import indirect_standardize

CRITERION='Combined nominal 90% interval coverage >= 0.86 in all six cells. O=0 and invalid draws count as non-coverage.'


def run(draws):
    cells=[]; rates=np.array([.0005,.001,.003,.01,.04])
    for ci,(expected,cv) in enumerate((e,cv) for e in (10,50,500) for cv in (.05,.20)):
        rng=np.random.default_rng(20261117+ci)
        pop=np.repeat(expected/rates.sum(),5)  # Equal populations, then scaled to E.
        obs=pd.Series([0],index=['synthetic'])
        frame=pd.DataFrame([pop],index=obs.index)
        combined=exact=invalid=zeros=0
        for _ in range(draws):
            o=int(rng.poisson(1.2*expected)); obs.iloc[0]=o; zeros+=int(o==0)
            observed_pop=pop*(1+rng.normal(0,cv,5))
            reps=make_replicates(observed_pop[None,:],(cv*pop)[None,:],rng)
            frame.iloc[0,:]=observed_pop
            try:
                row=indirect_standardize(obs,frame,rates,reps).iloc[0]
                combined+=int(o>0 and row.smr_lower<=1.2<=row.smr_upper)
                exact+=int(row.smr_exact_lower<=1.2<=row.smr_exact_upper)
            except ValueError: invalid+=1
        c={'expected':expected,'band_cv':cv,'draws':draws,'seed':20261117+ci,
           'combined_coverage':combined/draws,'exact_coverage':exact/draws,'zero_counts':zeros,'invalid_draws':invalid}
        cells.append(c); print(f"E={expected} CV={cv}: combined={combined/draws:.3f}, exact={exact/draws:.3f}",flush=True)
    return {'criterion':CRITERION,'passed':all(c['combined_coverage']>=.86 for c in cells),'cells':cells}


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--smoke-draws',type=int); parser.add_argument('--criterion-commit')
    args=parser.parse_args()
    if args.smoke_draws is not None:
        if not 1<=args.smoke_draws<=20: parser.error('smoke draws must be 1..20')
        run(args.smoke_draws); return
    if not args.criterion_commit: parser.error('full run requires --criterion-commit')
    for rel in ('scripts/smr_validation.py','docs/audits/smr_validation_criterion.md'):
        committed=subprocess.check_output(['git','show',args.criterion_commit+':'+rel],cwd=ROOT)
        if committed!=(ROOT/rel).read_bytes(): raise SystemExit('criterion/script differs from pre-run commit')
    report=run(2000); report['criterion_commit']=args.criterion_commit
    report['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    out=ROOT/'docs/audits/smr_validation'; out.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
    lines=['# Indirect SMR validation','',CRITERION,'',f"Criterion commit: `{args.criterion_commit}`.",'',
           f"Result: **{'PASS' if report['passed'] else 'FAIL — exploratory only'}**.",'',
           '| Expected | Band CV | Combined coverage | Fixed-E exact coverage | O=0 | Invalid |',
           '|---:|---:|---:|---:|---:|---:|']
    for c in report['cells']:
        lines.append(f"| {c['expected']} | {c['band_cv']:.0%} | {c['combined_coverage']:.3f} | {c['exact_coverage']:.3f} | {c['zero_counts']} | {c['invalid_draws']} |")
    lines+=['','2,000 draws per cell; true SMR 1.2, five equally populated bands scaled to the target expected count.',
            'Gaussian population errors are not clipped/redrawn. Nonpositive/invalid populations or expected counts count as non-coverage.',
            'Reference-rate uncertainty, correlated band errors and spatial dependence were not simulated; rates are treated as fixed.']
    out.with_suffix('.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__': main()
