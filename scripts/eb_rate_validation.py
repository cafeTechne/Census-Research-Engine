#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Frozen Round 27 EB experiment; see eb_rate_validation_criterion.md.

The vectorised likelihood/Newton kernel also fits bootstrap samples in batches.
It is copied, with numerical-parity tests, into the delivered library only after
this experiment. No application code is needed to pre-register this experiment.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import time

import numpy as np
from scipy.special import gammainc, gammaincinv, gammaln, digamma, polygamma

ROOT = Path(__file__).resolve().parents[1]
CRITERION = "Area-averaged 90% coverage >= 0.86 in every gamma cell and both lognormal CV .15 cells, separately for posterior and laird_louis."


def _likelihood(log_ab, counts, expected, lower, upper, derivatives=True):
    """NB marginal log likelihood, gradient and Hessian in log(alpha, beta).

    Integer-shape recurrences avoid millions of digamma/trigamma calls. Censored
    contributions use log-sum-exp and the variance-of-scores Hessian identity.
    Rows are independent fits; columns are areas. Bounds -1 mean observed.
    """
    ab = np.exp(np.asarray(log_ab, float))
    a, b = ab[:, 0, None], ab[:, 1, None]
    m = int(max(np.max(counts), np.max(upper), 1))
    large = m > 4096
    t = a + np.arange(max(int(np.max(upper)), 1) if large else m)[None, :]
    log_prefix = np.pad(np.cumsum(np.log(t), axis=1), ((0, 0), (1, 0)))
    logden = np.log(b + expected)
    numerator = gammaln(a+counts)-gammaln(a) if large else np.take_along_axis(log_prefix, counts, axis=1)
    logp = numerator - gammaln(counts+1) + a*np.log(b) + counts*np.log(expected) - (a+counts)*logden
    if derivatives:
        psi = np.pad(np.cumsum(1/t, axis=1), ((0, 0), (1, 0)))
        tri = np.pad(np.cumsum(-1/t**2, axis=1), ((0, 0), (1, 0)))
        ga = (digamma(a+counts)-digamma(a) if large else np.take_along_axis(psi, counts, axis=1)) + np.log(b) - logden
        gb = a/b - (a+counts)/(b+expected)
        haa = polygamma(1,a+counts)-polygamma(1,a) if large else np.take_along_axis(tri, counts, axis=1)
        hab = np.broadcast_to(1/b-1/(b+expected), counts.shape).copy()
        hbb = -a/b**2 + (a+counts)/(b+expected)**2
    mask = lower >= 0
    if mask.any():
        ii, jj = np.where(mask)
        ks = np.arange(int(lower[mask].min()), int(upper[mask].max())+1)
        aa, bb, ee = a[ii, 0, None], b[ii, 0, None], expected[jj, None]
        lp = log_prefix[ii[:, None], ks] - gammaln(ks+1) + aa*np.log(bb) + ks*np.log(ee) - (aa+ks)*np.log(bb+ee)
        lp = np.where((ks >= lower[ii, jj, None]) & (ks <= upper[ii, jj, None]), lp, -np.inf)
        peak = lp.max(axis=1)
        probs = np.exp(lp-peak[:, None]); total = probs.sum(axis=1)
        w = probs/total[:, None]
        logp[ii, jj] = peak+np.log(total)
        if derivatives:
            sa = psi[ii[:, None], ks]+np.log(bb)-np.log(bb+ee)
            sb = aa/bb-(aa+ks)/(bb+ee)
            ma, mb = (w*sa).sum(axis=1), (w*sb).sum(axis=1)
            ga[ii,jj], gb[ii,jj] = ma, mb
            haa[ii,jj] = (w*(tri[ii[:, None], ks]+sa**2)).sum(axis=1)-ma**2
            hab[ii,jj] = (w*(1/bb-1/(bb+ee)+sa*sb)).sum(axis=1)-ma*mb
            hbb[ii,jj] = (w*(-aa/bb**2+(aa+ks)/(bb+ee)**2+sb**2)).sum(axis=1)-mb**2
    ll = logp.sum(axis=1)
    if not derivatives:
        return ll
    g = np.stack([(a*ga).sum(axis=1), (b*gb).sum(axis=1)], axis=1)
    h = np.empty((len(ab), 2, 2))
    h[:,0,0] = (a*a*haa+a*ga).sum(axis=1)
    h[:,0,1] = h[:,1,0] = (a*b*hab).sum(axis=1)
    h[:,1,1] = (b*b*hbb+b*gb).sum(axis=1)
    return ll, g, h


def _fit_batch(counts, expected, lower, upper):
    """Damped Newton ML, Marshall-style exposure-weighted moment starts.

    Midpoint counts initialise censored rows ONLY; the likelihood always sums
    their entire integer interval. Precision above exp(18) is the Poisson limit.
    A failed fit raises, including any bootstrap fit; none is discarded.
    """
    counts = np.atleast_2d(np.asarray(counts, int))
    lower = np.broadcast_to(lower, counts.shape)
    upper = np.broadcast_to(upper, counts.shape)
    expected = np.asarray(expected, float)
    initial = np.where(lower >= 0, (lower+upper)/2, counts)
    mean = np.maximum(initial.sum(axis=1)/expected.sum(), 1e-8)
    denom = expected.sum()-(expected**2).sum()/expected.sum()
    variance = ((expected*(initial/expected-mean[:,None])**2).sum(axis=1) - (len(expected)-1)*mean)/denom
    shape = np.clip(mean**2/np.maximum(variance, mean**2/1e4), 1e-3, 1e4)
    x = np.column_stack([np.log(shape), np.log(shape/mean)])
    active = np.ones(len(x), bool)
    for _ in range(150):
        idx = np.flatnonzero(active)
        if not len(idx):
            return np.exp(x)
        ll, g, h = _likelihood(x[idx], counts[idx], expected, lower[idx], upper[idx])
        eig, vec = np.linalg.eigh(-h)
        eig = np.maximum(eig, np.maximum(np.abs(eig).max(axis=1)*1e-6, 1e-7)[:,None])
        step = np.einsum('bij,bj->bi', vec, np.einsum('bji,bj->bi', vec, g)/eig)
        step /= np.maximum(1, np.abs(step).max(axis=1)/2)[:,None]
        rate = np.ones(len(idx)); accepted = np.zeros(len(idx), bool)
        proposal = x[idx].copy(); newll = ll.copy()
        for _ in range(35):
            todo = np.flatnonzero(~accepted)
            if not len(todo):
                break
            p = x[idx[todo]]+rate[todo,None]*step[todo]
            p[:,0] = np.clip(p[:,0], -12, 18)
            p[:,1] = np.clip(p[:,1], -24, 36)
            val = _likelihood(p, counts[idx[todo]], expected, lower[idx[todo]], upper[idx[todo]], False)
            good = val >= ll[todo]-1e-10*(1+np.abs(ll[todo]))
            sel = todo[good]; proposal[sel] = p[good]; newll[sel] = val[good]; accepted[sel] = True
            rate[todo[~good]] *= .5
        # A flat likelihood or a vanishing Newton step is numerical convergence,
        # not a moment fallback. Precision-bound optima are recorded by callers.
        done = (np.abs(newll-ll) < 1e-9*(1+np.abs(ll))) | (np.max(np.abs(g),axis=1) < 1e-6*len(expected))
        if not accepted.all():
            raise RuntimeError("negative-binomial ML line search failed")
        x[idx] = proposal
        active[idx[done]] = False
    raise RuntimeError("negative-binomial ML did not converge in 150 iterations")


def _mixture_weights(alpha, beta, expected, lower, upper):
    ks = np.arange(int(lower), int(upper)+1)
    logp = (gammaln(alpha[...,None]+ks)-gammaln(alpha[...,None])-gammaln(ks+1)
            + alpha[...,None]*np.log(beta[...,None]/(beta[...,None]+expected[...,None]))
            + ks*np.log(expected[...,None]/(beta[...,None]+expected[...,None])))
    w = np.exp(logp-logp.max(axis=-1,keepdims=True))
    return ks, w/w.sum(axis=-1,keepdims=True)


def _posterior(alpha, beta, observed, expected, lower, upper, level=.90):
    observed = np.asarray(observed, float)
    lo = gammaincinv(alpha+observed, (1-level)/2)/(beta+expected)
    hi = gammaincinv(alpha+observed, (1+level)/2)/(beta+expected)
    mean = (alpha+observed)/(beta+expected)
    for l,u in sorted(set(zip(lower[lower>=0],upper[lower>=0]))):
        ix = np.flatnonzero(lower==l); ix = ix[upper[ix]==u]
        ks,w = _mixture_weights(np.full(len(ix),alpha), np.full(len(ix),beta), expected[ix], l,u)
        mean[ix] = (alpha+(w*ks).sum(axis=1))/(beta+expected[ix])
        for p,dest in (((1-level)/2,lo),((1+level)/2,hi)):
            left = np.zeros(len(ix)); right = gammaincinv(alpha+u, p)/(beta+expected[ix])
            for _ in range(38):
                mid = (left+right)/2
                cdf = (w*gammainc(alpha+ks,(beta+expected[ix,None])*mid[:,None])).sum(axis=1)
                left = np.where(cdf<p, mid,left); right = np.where(cdf>=p,mid,right)
            dest[ix] = (left+right)/2
    return mean,lo,hi


def _intervals(observed, expected, lower, upper, level=.90, n_boot=200, seed=None, bootstrap=True):
    a,b = _fit_batch(np.where(lower>=0,0,observed).astype(int), expected,lower,upper)[0]
    point,lo,hi = _posterior(a,b,observed,expected,lower,upper,level)
    result = dict(alpha=a,beta=b,point=point,posterior_lower=lo,posterior_upper=hi,
                  precision_boundary=bool(np.log(a)>17.99))
    if not bootstrap:
        return result
    rng = np.random.default_rng(seed)
    sim = rng.negative_binomial(a,b/(b+expected),size=(n_boot,len(expected)))
    suppressed = (sim>=1)&(sim<=9)
    sl = np.where(suppressed,1,-1); su = np.where(suppressed,9,-1)
    ab = _fit_batch(np.where(suppressed,0,sim),expected,sl,su)
    # One posterior draw per bootstrap hyperparameter pair: 200 equal-weight
    # mixture draws per area, without another unregistered quadrature/tuning grid.
    k = np.broadcast_to(observed,(n_boot,len(expected))).copy()
    for l,u in sorted(set(zip(lower[lower>=0],upper[lower>=0]))):
        ix = np.flatnonzero((lower==l)&(upper==u))
        ks,w = _mixture_weights(np.broadcast_to(ab[:,0,None],(n_boot,len(ix))),
                               np.broadcast_to(ab[:,1,None],(n_boot,len(ix))),expected[ix][None,:],l,u)
        draws = rng.random((n_boot,len(ix)))
        k[:,ix] = ks[np.minimum((np.cumsum(w,axis=2)<draws[:,:,None]).sum(axis=2),len(ks)-1)]
    samples = rng.gamma(ab[:,0,None]+k,1/(ab[:,1,None]+expected))
    result['laird_louis_lower'],result['laird_louis_upper'] = np.quantile(samples,[(1-level)/2,(1+level)/2],axis=0)
    result['bootstrap_precision_boundary'] = int(np.sum(np.log(ab[:,0])>17.99))
    return result


def _cell(job):
    ci,n,distribution,cv,draws = job
    started = time.monotonic(); rng = np.random.default_rng(20261127+ci)
    expected = rng.lognormal(np.log(20),1.2,n)
    small = expected<=np.quantile(expected,.2)
    coverage = {'posterior':[], 'laird_louis':[]}; small_cov={k:[] for k in coverage}
    mse_eb=[]; mse_raw=[]; censor=[]; failures=0; boundary=0; boot_boundary=0
    for d in range(draws):
        if distribution=='gamma':
            theta = rng.gamma(1/cv**2,cv**2,n)
        else:
            v = np.log1p(cv**2); theta = rng.lognormal(-v/2,np.sqrt(v),n)
        counts = rng.poisson(expected*theta)
        mask=(counts>=1)&(counts<=9); lower=np.where(mask,1,-1); upper=np.where(mask,9,-1)
        observed=np.where(mask,0,counts)
        seed=int(rng.integers(0,2**63-1))
        try:
            result=_intervals(observed,expected,lower,upper,n_boot=200,seed=seed)
            boundary+=int(result['precision_boundary']); boot_boundary+=result['bootstrap_precision_boundary']
            for name in coverage:
                cover=(result[name+'_lower']<=theta)&(theta<=result[name+'_upper'])
                coverage[name].append(float(cover.mean())); small_cov[name].append(float(cover[small].mean()))
            mse_eb.append(float(np.mean((result['point'][~mask]-theta[~mask])**2)))
            mse_raw.append(float(np.mean((counts[~mask]/expected[~mask]-theta[~mask])**2)))
        except (RuntimeError,ValueError,FloatingPointError):
            failures+=1
            # Failed draws count as zero coverage, never disappear from denominator.
            for name in coverage:
                coverage[name].append(0.); small_cov[name].append(0.)
        censor.append(float(mask.mean()))
    required=distribution=='gamma' or cv==.15
    out=dict(cell=ci,n=n,distribution=distribution,cv=cv,draws=draws,required=required,
             coverage={k:float(np.mean(v)) for k,v in coverage.items()},
             smallest_expected_quintile_coverage={k:float(np.mean(v)) for k,v in small_cov.items()},
             mse_eb=float(np.mean(mse_eb)) if mse_eb else None,mse_raw=float(np.mean(mse_raw)) if mse_raw else None,
             censored_share=float(np.mean(censor)),failed_draws=failures,precision_boundary_fits=boundary,
             bootstrap_precision_boundary_fits=boot_boundary,seconds=round(time.monotonic()-started,2))
    print(json.dumps(out),flush=True)
    return out


def main():
    p=argparse.ArgumentParser(); p.add_argument('--smoke-draws',type=int); p.add_argument('--criterion-commit'); p.add_argument('--workers',type=int,default=4)
    args=p.parse_args()
    if args.smoke_draws is not None and not 1<=args.smoke_draws<=20:
        p.error('smoke draws must be 1..20')
    if args.smoke_draws is None:
        if not args.criterion_commit:
            p.error('full run requires --criterion-commit (committed AND pushed first)')
        for path in ('scripts/eb_rate_validation.py','scripts/eb_rate_validation_criterion.md'):
            frozen=subprocess.check_output(['git','show',f'{args.criterion_commit}:{path}'],cwd=ROOT)
            if frozen!=(ROOT/path).read_bytes():
                p.error('criterion/script differs from pre-run commit')
    draws=args.smoke_draws or 1000
    jobs=[(i,n,dist,cv,draws) for i,(n,dist,cv) in enumerate((n,d,c) for n in (145,1000) for d in ('gamma','lognormal') for c in (.15,.30))]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        cells=list(pool.map(_cell,jobs))
    passed={name:all(c['coverage'][name]>=.86 and c['failed_draws']==0 for c in cells if c['required']) for name in ('posterior','laird_louis')}
    if args.smoke_draws is not None:
        print('SMOKE ONLY, no audit written',passed); return
    report=dict(criterion=CRITERION,criterion_commit=args.criterion_commit,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),passed=passed,default_interval='posterior' if passed['posterior'] else 'laird_louis' if passed['laird_louis'] else None,cells=cells)
    base=ROOT/'docs/audits/eb_rate_validation'
    base.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
    lines=['# Round 27: empirical-Bayes rate interval validation','',CRITERION,'',f"Pre-run criterion: `{args.criterion_commit}`. 1,000 draws/cell; 200 hyperparameter bootstrap refits/draw.",'',f"Passed: posterior **{passed['posterior']}**, Laird–Louis **{passed['laird_louis']}**. Default: `{report['default_interval']}`.",'','| n | Truth | CV | Posterior coverage | Laird–Louis coverage | Lowest-E posterior / LL | MSE EB / raw (uncensored) | Suppressed share | Failures |','| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |']
    for c in cells:
        lines.append(f"| {c['n']} | {c['distribution']} | {c['cv']} | {c['coverage']['posterior']:.5f} | {c['coverage']['laird_louis']:.5f} | {c['smallest_expected_quintile_coverage']['posterior']:.5f} / {c['smallest_expected_quintile_coverage']['laird_louis']:.5f} | {c['mse_eb']} / {c['mse_raw']} | {c['censored_share']:.4f} | {c['failed_draws']} |")
    lines+=['','Lognormal CV .30 is informational. Failed draws count as zero coverage; any fit failure also fails acceptance. Areas are independent, E is fixed and known, and theta has population mean one. This does not validate causal inference or spatial smoothing.','', 'Bootstrap intervals use 200 equal-weight posterior-mixture draws; the Monte Carlo quantile approximation is part of the assessed procedure. Poisson-limit boundary-fit counts are in the JSON. See the frozen criterion for numerical conventions.']
    base.with_suffix('.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':
    main()
