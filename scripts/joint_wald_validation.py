#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Frozen Round 27 joint-Wald experiment; see adjacent criterion.

Batch linear algebra is checked against production statsmodels refits in the
Round 27 tests. Spline designs use the same full-sample patsy DesignInfo.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import patsy
from scipy.special import expit
from scipy.stats import chi2
from census.simulation import make_replicates

CRITERION='Nominal .10 conservative joint-Wald size within [.07,.13] in all eight cells; power is informational.'


def fit_batch(X,y,model,trials=None):
    """Full-rank OLS / binomial IRLS, full HC3 and all replicate coefficients."""
    X=np.asarray(X,float); y=np.asarray(y,float)
    if model=='linear':
        bread=np.linalg.inv(np.einsum('bni,bnj->bij',X,X))
        coef=np.einsum('bij,bnj,n->bi',bread,X,y)
        fitted=X[0]@coef[0]
        leverage=np.einsum('ni,ij,nj->n',X[0],bread[0],X[0])
        score=X[0]*((y-fitted)/(1-leverage))[:,None]
    else:
        coef=np.zeros((len(X),X.shape[2])); coef[:,0]=np.log(np.average(y,weights=trials)/(1-np.average(y,weights=trials)))
        for _ in range(80):
            mu=expit(np.einsum('bni,bi->bn',X,coef))
            w=trials*mu*(1-mu)
            h=np.einsum('bni,bn,bnj->bij',X,w,X)
            delta=np.linalg.solve(h,np.einsum('bni,bn->bi',X,trials*(y-mu))[...,None])[...,0]
            coef+=delta
            if np.max(np.abs(delta))<1e-9:
                break
        else:
            raise RuntimeError('binomial IRLS failed')
        mu=expit(X[0]@coef[0]); w=trials*mu*(1-mu)
        bread=np.linalg.inv(X[0].T@(w[:,None]*X[0]))
        leverage=w*np.einsum('ni,ij,nj->n',X[0],bread,X[0])
        score=X[0]*(trials*(y-mu)/(1-leverage))[:,None]
        bread=bread[None,:,:]
    cov=bread[0]@(score.T@score)@bread[0]
    return coef,cov


def joint_stat(coef,cov):
    cov=np.asarray(cov,float); coef=np.asarray(coef,float)
    if not np.isfinite(cov).all() or not np.isfinite(coef).all() or np.linalg.matrix_rank(cov)<len(coef):
        raise ValueError('singular or non-finite joint covariance; no pseudoinverse')
    np.linalg.cholesky(cov)
    w=float(coef@np.linalg.solve(cov,coef))
    return w,float(chi2.sf(w,len(coef)))


def _cell(job):
    ci,model,df,cv,draws=job; rng=np.random.default_rng(20261128+ci)
    n=145; started=time.monotonic(); reject=0; power=0; failures=0
    trials=np.maximum(1,np.rint(rng.lognormal(np.log(3900),1,n))) if model=='binomial' else None
    for _ in range(draws):
        truth=rng.normal(size=n); z=rng.normal(size=n)
        se=np.full(n,cv); observed=truth+rng.normal(0,se)
        reps=make_replicates(observed[:,None],se[:,None],rng)[:,0,:]
        formula=f'1 + cr(x, df={df}, constraints="center") + z'
        X=patsy.dmatrix(formula,{'x':observed,'z':z},return_type='dataframe')
        R=patsy.build_design_matrices([X.design_info],{'x':reps.T.ravel(),'z':np.tile(z,80)})[0]
        designs=np.concatenate([np.asarray(X)[None,:,:],np.asarray(R).reshape(80,n,-1)])
        use=np.arange(1,df+1)
        noise=rng.normal(size=n)
        ys=[]
        if model=='linear':
            ys=[1+.5*z+noise,1+.5*z+noise+.3*np.sin(truth)]
        else:
            # Outcomes are independent conditional on the shared area effect.
            for effect in (np.zeros(n),.3*np.sin(truth)):
                p=expit(-2.6+.3*z+.5*noise+effect)
                ys.append(rng.binomial(trials.astype(int),p)/trials)
        for j,y in enumerate(ys):
            try:
                coefs,model_cov=fit_batch(designs,y,model,trials)
                delta=coefs[1:]-coefs[0]
                covariance=model_cov+.05*delta.T@delta
                _,p=joint_stat(coefs[0,use],covariance[np.ix_(use,use)])
                if j==0:
                    reject+=int(p<.10)
                else:
                    power+=int(p<.10)
            except (ValueError,RuntimeError,np.linalg.LinAlgError):
                if j==0:
                    failures+=1
    out=dict(cell=ci,model=model,df=df,x_cv=cv,n=n,draws=draws,seed=20261128+ci,
             size=reject/draws,power=power/draws,null_failures=failures,seconds=round(time.monotonic()-started,2))
    print(json.dumps(out),flush=True); return out


def main():
    p=argparse.ArgumentParser();p.add_argument('--smoke-draws',type=int);p.add_argument('--criterion-commit');p.add_argument('--workers',type=int,default=4)
    args=p.parse_args()
    if args.smoke_draws is not None and not 1<=args.smoke_draws<=20:
        p.error('smoke draws must be 1..20')
    if args.smoke_draws is None:
        if not args.criterion_commit:
            p.error('full run requires --criterion-commit (committed AND pushed first)')
        for path in ('scripts/joint_wald_validation.py','scripts/joint_wald_validation_criterion.md'):
            if subprocess.check_output(['git','show',f'{args.criterion_commit}:{path}'],cwd=ROOT)!=(ROOT/path).read_bytes():
                p.error('criterion/script differs from pre-run commit')
    draws=args.smoke_draws or 2000
    jobs=[(i,m,df,cv,draws) for i,(m,df,cv) in enumerate((m,d,c) for m in ('linear','binomial') for d in (3,5) for c in (0.,.15))]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        cells=list(pool.map(_cell,jobs))
    passed=all(.07<=c['size']<=.13 and c['null_failures']==0 for c in cells)
    if args.smoke_draws is not None:
        print('SMOKE ONLY, no audit written',passed);return
    report=dict(criterion=CRITERION,criterion_commit=args.criterion_commit,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),passed=passed,cells=cells)
    base=ROOT/'docs/audits/joint_wald_validation';base.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
    lines=['# Round 27: natural splines and joint Wald validation','',CRITERION,'',f"Pre-run criterion: `{args.criterion_commit}`. Passed: **{passed}**.",'','| Model | Spline df | x CV | Null size | Power | Null failures |','| :-- | :-- | :-- | :-- | :-- | :-- |']
    for c in cells:
        lines.append(f"| {c['model']} | {c['df']} | {c['x_cv']} | {c['size']:.4f} | {c['power']:.4f} | {c['null_failures']} |")
    lines+=['','2,000 draws/cell, n=145, nominal .10; centered natural splines with df 3/5, full-sample quantile knots frozen in every replicate. HC3 plus 4/80 times the uncentered replicate-deviation outer products; chi-squared reference. Power is informational at .3 sin(x). Independent areas, fixed binomial trials, constant-scale x sampling SE .15 on the standardized scale; no spatial or reference-rate uncertainty is asserted.','', 'WLS, Poisson, df=4 and categorical multi-column terms are supported computationally but not separately simulation-validated by these cells. See the frozen criterion for the complete DGP and failure convention.']
    base.with_suffix('.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':
    main()
