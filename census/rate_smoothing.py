# SPDX-License-Identifier: AGPL-3.0-or-later
"""Descriptive Poisson–Gamma empirical-Bayes rates with interval-censored counts.

Beta is a RATE, E is a fixed expected count, not a population denominator. The
frozen Round 27 validation kernel is retained in scripts/eb_rate_validation.py.
"""
import numpy as np
import pandas as pd
from scipy.special import gammainc, gammaincinv, gammaln, digamma, polygamma

# Fixed criterion d4dec47; results docs/audits/eb_rate_validation.md.
EB_VALIDATED = {"posterior": True, "laird_louis": True}
DEFAULT_INTERVAL = "posterior"

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


def _intervals(observed, expected, lower, upper, level=.90, n_boot=200, seed=None, bootstrap=True, bootstrap_bounds=(1,9)):

    a,b = _fit_batch(np.where(lower>=0,0,observed).astype(int), expected,lower,upper)[0]
    point,lo,hi = _posterior(a,b,observed,expected,lower,upper,level)
    result = dict(alpha=a,beta=b,point=point,posterior_lower=lo,posterior_upper=hi,
                  precision_boundary=bool(np.log(a)>17.99))
    if not bootstrap:
        return result
    rng = np.random.default_rng(seed)
    sim = rng.negative_binomial(a,b/(b+expected),size=(n_boot,len(expected)))
    bounds = bootstrap_bounds
    suppressed = np.zeros_like(sim,dtype=bool) if bounds is None else (sim>=bounds[0])&(sim<=bounds[1])
    sl = np.where(suppressed,bounds[0] if bounds else -1,-1); su = np.where(suppressed,bounds[1] if bounds else -1,-1)
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


def eb_poisson_gamma(observed, expected, censored_lower=None, censored_upper=None,
                     level=.90, interval=None, n_boot=200, seed=None, *, reference_rate=None):
    """Return descriptive EB ratios, preserving a Series' unique GEOID index.

    Censored counts must be missing, with finite integer bounds (upper <=4096); neither missing
    uncensored counts nor non-positive expected counts are silently dropped.
    Series inputs must have identical indexes in identical order. Arrays are
    positional and receive a RangeIndex. Pass expected=exposure*reference_rate
    in consistent units; optional reference_rate also produces rate columns.
    No ACS, reference-rate, spatial or causal uncertainty is incorporated.

    Laird–Louis refits 200 simulated datasets by default and uses 200 equal-weight
    posterior-mixture draws for its interval. A common censoring rule is reapplied
    to simulated datasets; with no censoring, simulated counts remain observed.
    ML failures raise, including bootstrap failures. All-zero inputs
    without positive count information are refused (unidentified/boundary fit).
    Validation notes in DataFrame.attrs are essential output metadata.
    """
    if isinstance(observed,dict): observed=pd.Series(observed)
    if isinstance(expected,dict): expected=pd.Series(expected)
    series=[v for v in (observed,expected,censored_lower,censored_upper) if isinstance(v,pd.Series)]
    index=series[0].index.copy() if series else pd.RangeIndex(len(observed))
    if not index.is_unique or index.hasnans or any(not v.index.equals(index) for v in series):
        raise ValueError('Series must have identical, unique, nonmissing GEOID indexes in the same order')
    def array(v,name):
        try: out=np.asarray(pd.to_numeric(pd.Series(v) if not isinstance(v,pd.Series) else v,errors='raise'),float)
        except (ValueError,TypeError) as exc: raise ValueError(f'{name} must be numeric') from exc
        if out.ndim!=1 or len(out)!=len(index): raise ValueError(f'{name} must have one value per GEOID')
        return out
    o=array(observed,'observed');e=array(expected,'expected')
    if len(o)<3 or not np.isfinite(e).all() or np.any(e<=0):
        raise ValueError('at least three areas and finite expected counts E > 0 are required')
    if (censored_lower is None)!=(censored_upper is None): raise ValueError('both censoring bounds are required')
    l=np.full(len(o),np.nan) if censored_lower is None else array(censored_lower,'censored_lower')
    u=np.full(len(o),np.nan) if censored_upper is None else array(censored_upper,'censored_upper')
    if not np.array_equal(np.isnan(l),np.isnan(u)): raise ValueError('censoring bounds must occur in pairs')
    bounded=~np.isnan(l)
    exact_bounds=bounded & np.isfinite(o) & (l==u) & (o==l)
    censored=bounded & ~exact_bounds
    if (not np.isfinite(l[censored]).all() or not np.isfinite(u[censored]).all()
        or np.any(l[censored]<0) or np.any(u[censored]<l[censored])
        or np.any(l[censored]!=np.floor(l[censored])) or np.any(u[censored]!=np.floor(u[censored]))):
        raise ValueError('censoring bounds must be ordered nonnegative finite integers')
    if np.any(censored & ~np.isnan(o)): raise ValueError('censored observed counts must be missing, never disclosed or imputed')
    exact=o[~censored]
    if not np.isfinite(exact).all() or np.any(exact<0) or np.any(exact!=np.floor(exact)):
        raise ValueError('observed counts must be nonnegative finite integers; only censored counts may be missing')
    if not np.any(exact>0) and not np.any(l[censored]>0): raise ValueError('positive count information is required for an identifiable finite ML fit')
    if not np.isfinite(level) or not 0<level<1: raise ValueError('level must be between zero and one')
    interval=DEFAULT_INTERVAL if interval is None else interval
    if interval not in EB_VALIDATED: raise ValueError('interval must be posterior or laird_louis')
    if isinstance(n_boot,bool) or not isinstance(n_boot,(int,np.integer)) or n_boot<2:
        raise ValueError('n_boot must be an integer >= 2')
    pairs=set(zip(l[censored].astype(int),u[censored].astype(int)))
    if interval=='laird_louis' and len(pairs)>1:
        raise ValueError('bootstrap requires a single common count-suppression rule')
    if np.any(u[censored]>4096): raise ValueError('censored upper bounds above 4096 counts are not supported')
    bounds=next(iter(pairs)) if pairs else None
    ll=np.where(censored,l,-1).astype(int);uu=np.where(censored,u,-1).astype(int)
    fit=_intervals(np.where(censored,0,o),e,ll,uu,level,n_boot,seed,interval=='laird_louis',bootstrap_bounds=bounds)
    out=pd.DataFrame(dict(observed=o,censored=censored,expected=e,raw_ratio=o/e,
                          eb_ratio=fit['point'],shrinkage=fit['beta']/(fit['beta']+e),
                          eb_lower=fit[interval+'_lower'],eb_upper=fit[interval+'_upper'],interval=interval),index=index)
    out.index.name=index.name or 'GEOID'
    if reference_rate is not None:
        if not np.isscalar(reference_rate) or not np.isfinite(reference_rate) or reference_rate<=0:
            raise ValueError('reference_rate must be finite and positive, in the desired rate units')
        for source,dest in [('raw_ratio','raw_rate'),('eb_ratio','eb_rate'),('eb_lower','eb_rate_lower'),('eb_upper','eb_rate_upper')]:
            out[dest]=out[source]*reference_rate
    matched=bool(EB_VALIDATED[interval] and level==.90 and (interval!='laird_louis' or n_boot==200))
    note=('Passed fixed Round 27 90% area-average coverage criterion under its independent-area simulation assumptions.'
          if matched else 'NOT VALIDATED for this interval/level/bootstrap configuration; descriptive exploratory output only.')
    out.attrs.update(alpha=float(fit['alpha']),beta=float(fit['beta']),beta_convention='rate',
                     validated=matched,validation_note=note,descriptive_only=True,
                     precision_boundary=fit['precision_boundary'],
                     bootstrap_precision_boundary_fits=fit.get('bootstrap_precision_boundary',0),
                     interval=interval,confidence_level=level,reference_rate=reference_rate,
                     assumptions='Fixed known expected counts and reference rate; independent areas; Gamma risk distribution. No hypothesis tests.',
                     n_boot=n_boot if interval=='laird_louis' else None,seed=seed)
    return out
