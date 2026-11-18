#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fixed Round 28 segregation experiment; see adjacent criterion."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from scipy.stats import norm
from census.simulation import make_replicates

INDICES=('dissimilarity','isolation','theil_h')
CRITERION='For each index and naive/bias_corrected version separately: nominal 90% coverage >= .86 in all four CV .15 cells; CV .30 informational. Invalid draws count as noncoverage.'


def indices(counts):
    """Batch x tracts x groups; zero tracts excluded, absent groups undefined."""
    x=np.asarray(counts,float)
    if x.ndim!=3 or x.shape[2]<2 or not np.isfinite(x).all() or (x<0).any():
        raise ValueError('counts must be finite nonnegative (batch,tracts,groups>=2)')
    totals=x.sum(axis=2);groups=x.sum(axis=1);N=groups.sum(axis=1)
    shares=np.divide(x,totals[:,:,None],out=np.zeros_like(x),where=totals[:,:,None]>0)
    area_shares=np.divide(groups,N[:,None],out=np.zeros_like(groups),where=N[:,None]>0)
    with np.errstate(divide='ignore',invalid='ignore'):
        entropy=-np.where(area_shares>0,area_shares*np.log(area_shares),0).sum(axis=1)
        tract_entropy=-np.where(shares>0,shares*np.log(shares),0).sum(axis=2)
    H=np.divide((totals*(entropy[:,None]-tract_entropy)).sum(axis=1),N*entropy,
                out=np.full(len(x),np.nan),where=N*entropy>0)
    out=np.full((len(x),3),np.nan);out[:,2]=H
    if x.shape[2]==2:
        proportions=np.divide(x,groups[:,None,:],out=np.zeros_like(x),where=groups[:,None,:]>0)
        out[:,0]=.5*np.abs(proportions[:,:,0]-proportions[:,:,1]).sum(axis=1)
        out[:,1]=(proportions[:,:,0]*shares[:,:,0]).sum(axis=1)
    out[(groups<=0).any(axis=1)]=np.nan
    return out


def truth_counts(n,target,rng):
    # Matched lognormal tract pairs give exactly the requested D and integer
    # group counts. Rounding to multiples of 20 preserves .2 and .5 designs.
    totals=np.maximum(20,20*np.rint(rng.lognormal(np.log(4000),1,n//2)/20))
    totals=np.repeat(totals,2)
    p=.5+target/2*np.tile([1.,-1.],n//2)
    return np.column_stack((totals*p,totals*(1-p)))


def run(draws):
    cells=[];z=norm.ppf(.95)
    for ci,(n,D,cv) in enumerate((n,d,c) for n in (20,100) for d in (.2,.5) for c in (.15,.30)):
        rng=np.random.default_rng(20261129+ci);true=truth_counts(n,D,rng);truth=indices(true[None])[0]
        se_count=cv*true;covered=np.zeros((2,3));estimates=[[],[]];ses=[];invalid=0
        for _ in range(draws):
            observed=true+rng.normal(size=true.shape)*se_count
            reps=make_replicates(observed,se_count,rng).transpose(2,0,1)
            if (observed<0).any() or (reps<0).any():invalid+=1;continue
            raw=indices(observed[None])[0];rep=indices(reps)
            if not np.isfinite(rep).all() or not np.isfinite(raw).all():invalid+=1;continue
            se=np.sqrt(.05*np.sum((rep-raw)**2,axis=0));corrected=raw-4*(rep.mean(axis=0)-raw)
            for j,point in enumerate((raw,corrected)):
                covered[j]+=np.abs(point-truth)<=z*se;estimates[j].append(point)
            ses.append(se)
        stats={}
        for k,name in enumerate(INDICES):
            stats[name]={}
            for j,variant in enumerate(('naive','bias_corrected')):
                e=np.asarray(estimates[j]);s=np.asarray(ses)
                stats[name][variant]=dict(coverage=float(covered[j,k]/draws),
                    bias=float(np.mean(e[:,k]-truth[k])) if len(e) else None,
                    mean_se_over_empirical_sd=float(np.mean(s[:,k])/np.std(e[:,k],ddof=1)) if len(e)>1 else None)
        cell=dict(cell=ci,n_tracts=n,true_dissimilarity=D,group_cv=cv,seed=20261129+ci,draws=draws,
                  true_indices=dict(zip(INDICES,map(float,truth))),invalid_draws=invalid,statistics=stats)
        cells.append(cell);print(json.dumps(cell),flush=True)
    passed={name:{v:all(c['statistics'][name][v]['coverage']>=.86 for c in cells if c['group_cv']==.15)
                  for v in ('naive','bias_corrected')} for name in INDICES}
    default={name:'bias_corrected' if passed[name]['bias_corrected'] else 'naive' for name in INDICES}
    return dict(criterion=CRITERION,passed=passed,default=default,cells=cells)


def main():
    p=argparse.ArgumentParser();p.add_argument('--smoke-draws',type=int);p.add_argument('--criterion-commit');a=p.parse_args()
    if a.smoke_draws is not None:
        if not 1<=a.smoke_draws<=20:p.error('smoke draws must be 1..20')
        run(a.smoke_draws);print('SMOKE ONLY, no audit written');return
    if not a.criterion_commit:p.error('full run requires --criterion-commit (commit and push first)')
    for path in ('scripts/segregation_validation.py','scripts/segregation_validation_criterion.md'):
        if subprocess.check_output(['git','show',a.criterion_commit+':'+path],cwd=ROOT)!=(ROOT/path).read_bytes():
            p.error('criterion/script differs from pre-run commit')
    report=run(1000);report.update(criterion_commit=a.criterion_commit,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    base=ROOT/'docs/audits/segregation_validation';base.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
    lines=['# Round 28 segregation validation','',CRITERION,'',f'Criterion commit: `{a.criterion_commit}`.','',
           '| Index | Naive passed | Corrected passed | Default |','| :-- | :-- | :-- | :-- |']
    for name in INDICES:lines.append(f"| {name} | {report['passed'][name]['naive']} | {report['passed'][name]['bias_corrected']} | {report['default'][name]} |")
    lines+=['','| Tracts | True D | CV | Index | Coverage naive / corrected | Bias naive / corrected | Mean SE / empirical SD naive / corrected | Invalid |','| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |']
    for c in report['cells']:
        for name in INDICES:
            v=c['statistics'][name];na=v['naive'];bc=v['bias_corrected']
            lines.append(f"| {c['n_tracts']} | {c['true_dissimilarity']} | {c['group_cv']} | {name} | {na['coverage']:.4f} / {bc['coverage']:.4f} | {na['bias']} / {bc['bias']} | {na['mean_se_over_empirical_sd']} / {bc['mean_se_over_empirical_sd']} | {c['invalid_draws']} |")
    lines+=['','1,000 draws/cell; count errors are independent Gaussian, not clipped or redrawn. Invalid full draws or any invalid replicate count as noncoverage. Bias/SD diagnostics condition on valid draws. The corrected estimate is I - 4(mean(Ir)-I), with the same raw-replicate SE, without clipping corrected indices or confidence limits.','', 'The experiment assesses two declared groups, matched-pair fixed tract populations, 20/100 tracts, and CV .15 for acceptance. CV .30 is informational. Multigroup H and county/release contrasts have computational tests, not separate coverage experiments. See the frozen criterion for full conventions.']
    base.with_suffix('.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':main()
