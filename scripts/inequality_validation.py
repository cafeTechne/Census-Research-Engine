#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pre-specified Round 24 area-inequality validation (see adjacent criterion).

Full run: python scripts/inequality_validation.py --criterion-commit SHA
Smoke only: --smoke-draws 1..20 (never writes the audit).
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
from scipy.special import expit
from scipy.stats import norm
from census.inequality import ridits, inequality_replicate, TERMS
from census.simulation import make_replicates
from census.variance import REPLICATE_COLUMNS

CRITERION = "Conservative nominal 90% coverage >= 0.86 for all three statistics in all four cells with rank CV <= 0.15. CV 0.30 is informational."


def run(draws):
    cells=[]; z=norm.ppf(.95)
    for ci,(n,cv) in enumerate((n,cv) for n in (145,1000) for cv in (.05,.15,.30)):
        rng=np.random.default_rng(20261116+ci)
        w=rng.lognormal(np.log(20000 if n==145 else 4000),1,n)
        x=expit(rng.normal(-1.6,.6,n)); r=ridits(x,w,True)
        base=.07+.03*r; rm=np.average(r,weights=w); ym=np.average(base,weights=w)
        truth=np.array([.03,np.log(.10/.07),2*np.average((base-ym)*(r-rm),weights=w)/ym])
        denom=np.maximum(1,np.rint(w/50)).astype(int)
        f=pd.DataFrame({'GEOID':[str(i) for i in range(n)],'y':base,'x':x,'w':w,'x_se':cv*x})
        rep=pd.DataFrame(np.zeros((n,80)),columns=REPLICATE_COLUMNS)
        rep.insert(0,'variable','x'); rep.insert(0,'GEOID',f.GEOID)
        est=np.full((draws,3),np.nan); se=np.full_like(est,np.nan); sm=np.full_like(est,np.nan)
        failures=0
        for d in range(draws):
            probability=base+rng.normal(0,.008,n)
            if ((probability<0)|(probability>1)).any():
                failures+=1; continue
            f['y']=rng.binomial(denom,probability)/denom
            f['x']=x+rng.normal(0,cv*x,n)
            rep.loc[:,REPLICATE_COLUMNS]=make_replicates(f.x.to_numpy()[:,None],(cv*x)[:,None],rng)[:,0,:]
            try:
                result=inequality_replicate(f,'y','x','w',True,rep,fixed=('y','w'))
                c=result.coefficients.set_index('term').loc[list(TERMS)]
                est[d]=c.estimate; se[d]=c.se_total; sm[d]=c.se_model
            except (ValueError,RuntimeError): failures+=1
        stats={}
        for j,term in enumerate(TERMS):
            good=np.isfinite(est[:,j]); sd=float(np.std(est[good,j],ddof=1)) if good.sum()>1 else float('nan')
            coverage=lambda s:float(np.mean(np.isfinite(s[:,j]) & (np.abs(est[:,j]-truth[j])<=z*s[:,j])))
            stats[term]={'truth':float(truth[j]),'conservative_coverage':coverage(se),'population_coverage':coverage(sm),
                         'bias':float(np.nanmean(est[:,j])-truth[j]),'empirical_sd':sd,
                         'mean_total_se_over_sd':float(np.nanmean(se[:,j])/sd),
                         'mean_model_se_over_sd':float(np.nanmean(sm[:,j])/sd)}
        cell={'n':n,'rank_cv':cv,'draws':draws,'seed':20261116+ci,'invalid_draws':failures,'statistics':stats}
        cells.append(cell)
        print(f"n={n} CV={cv}: "+', '.join(f"{k}={v['conservative_coverage']:.3f}" for k,v in stats.items()),flush=True)
    passed=all(s['conservative_coverage']>=.86 for c in cells if c['rank_cv']<=.15 for s in c['statistics'].values())
    return {'criterion':CRITERION,'passed':passed,'cells':cells}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--smoke-draws',type=int); parser.add_argument('--criterion-commit')
    args=parser.parse_args()
    if args.smoke_draws is not None:
        if not 1<=args.smoke_draws<=20: parser.error('smoke draws must be 1..20')
        run(args.smoke_draws); return
    if not args.criterion_commit: parser.error('full run requires --criterion-commit')
    # Verify the exact script and criterion were in the named, already-pushed commit.
    for rel in ('scripts/inequality_validation.py','docs/audits/inequality_validation_criterion.md'):
        committed=subprocess.check_output(['git','show',args.criterion_commit+':'+rel],cwd=ROOT)
        if committed!=(ROOT/rel).read_bytes(): raise SystemExit('criterion/script differs from pre-run commit')
    report=run(1000); report['criterion_commit']=args.criterion_commit
    report['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    out=ROOT/'docs/audits/inequality_validation'
    out.with_suffix('.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    lines=['# Area-inequality validation','',CRITERION,'',f"Criterion commit: `{args.criterion_commit}`.",
           '',f"Result: **{'PASS' if report['passed'] else 'FAIL — exploratory only'}**.",
           '', 'Invalid/undefined draws count as non-coverage. No seeds, designs or criteria were changed.',
           '', '| n | Rank CV | Statistic | Conservative coverage | Population coverage | Bias | Mean total SE / SD | Mean model SE / SD |',
           '|---:|---:|:---|---:|---:|---:|---:|---:|']
    for c in report['cells']:
        for term,s in c['statistics'].items():
            lines.append(f"| {c['n']} | {c['rank_cv']:.0%} | {term} | {s['conservative_coverage']:.3f} | {s['population_coverage']:.3f} | {s['bias']:.6g} | {s['mean_total_se_over_sd']:.3f} | {s['mean_model_se_over_sd']:.3f} |")
    lines+=['','Design: 1,000 draws per cell, fixed area weights and true ranks, independent areas; all invalid-draw counts are in the JSON.',
            'Validated range, if passed: median rank CV <=15%. CV 30% is informational; HC3/conservative intervals do not correct rank-error attenuation.',
            'Positive indices mean higher outcomes among more deprived areas. Concentration has the reverse sign of the usual income-ranked convention.']
    out.with_suffix('.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__': main()
