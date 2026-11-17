# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pre-specified Round 26 cluster validation. No full run before criterion commit/push.

Six cells, 2000 draws each; seeds 20261126+cell (linear then binomial, 0/50/100 km).
Imports the exact Round 22 generators. Bootstrap RNG is independent SeedSequence
[20261126, cell, draw, 3], so candidate evaluation cannot alter outcome draws.
C3 linear is studentized WCR with restricted OLS residuals; binomial is the
Kline-Santos Score2-Wald variant (restricted numerator, unrestricted studentization).
Reference: https://eml.berkeley.edu/~pkline/papers/ScoreFinal_web.pdf (appendix).
999 Webb weights, common within each draw for test inversion. 90% C3 intervals
are numerical inversion of the two-sided bootstrap test, not normal approximations.
See docs/audits/spatial_cluster_validation_criterion.md for every fixed convention.
"""
import argparse
import hashlib
import json
import subprocess
import sys
import warnings
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'scripts'))
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.cluster.vq import kmeans2
from scipy.special import expit
from scipy.stats import norm, t
from pyproj import Transformer
from spatial_hac_validation import (get_boundaries, unit_coordinates, haversine_matrix,
                                    simulation_setup, simulation_draw)

CANDIDATES = {'C1-8':('cr1_t',8), 'C1-12':('cr1_t',12), 'C2-8':('im',8), 'C3-12':('wcr',12)}
WEBB = np.array([-np.sqrt(1.5), -1., -np.sqrt(.5), np.sqrt(.5), 1., np.sqrt(1.5)])


def cluster_points(coords, k, seed=20261126):
    """50 kmeans++ restarts, lowest SSE among solutions with >=5 members/group.

    Coordinates are the same representative points as the Round 22 generator,
    projected to EPSG:5070. Labels canonicalized by centroid x then y. No outcomes.
    """
    xy = np.column_stack(Transformer.from_crs(4326,5070,always_xy=True).transform(coords.lon,coords.lat))
    if type(k) is not int or k<2 or len(xy)<5*k or not np.isfinite(xy).all():
        raise ValueError('k needs at least five finite points per cluster')
    rng = np.random.default_rng(seed); choices=[]
    for restart in range(50):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            centers, labels = kmeans2(xy,k,iter=100,minit='++',rng=rng)
        counts=np.bincount(labels,minlength=k)
        if np.min(counts)<5: continue
        sse=float(np.sum((xy-centers[labels])**2))
        order=np.lexsort((centers[:,1],centers[:,0])); relabel=np.empty(k,int);relabel[order]=np.arange(k)
        choices.append((sse,restart,relabel[labels]))
    if not choices: raise ValueError(f'no admissible k={k} solution among 50 fixed restarts')
    return min(choices,key=lambda c:(c[0],c[1]))[2]


def group_sums(values, labels):
    values=np.asarray(values,float);labels=np.asarray(labels)
    _,inv=np.unique(labels,return_inverse=True)
    result=np.zeros((int(inv.max())+1,)+values.shape[1:])
    np.add.at(result,inv,values)
    return result


def cluster_covariance(scores, bread_inv, labels):
    scores=np.asarray(scores,float);bread_inv=np.asarray(bread_inv,float)
    n,k=scores.shape; grouped=group_sums(scores,labels);g=len(grouped)
    if g<2 or n<=k or not np.isfinite(scores).all(): raise ValueError('invalid cluster covariance design')
    factor=g/(g-1)*(n-1)/(n-k)
    return factor*bread_inv@(grouped.T@grouped)@bread_inv.T


def fit_components(X,y,design,trials=None):
    if design=='linear':
        bread=np.linalg.inv(X.T@X);b=bread@X.T@y;mu=X@b
        scores=X*(y-mu)[:,None];h=np.einsum('ij,jk,ik->i',X,bread,X)
        hc3=bread@((scores/(1-h[:,None])).T@(scores/(1-h[:,None])))@bread
    else:
        fit=sm.GLM(y,X,family=sm.families.Binomial(),var_weights=trials).fit(scale='X2')
        if not fit.converged: raise ValueError('binomial fit did not converge')
        b=np.asarray(fit.params);mu=np.asarray(fit.fittedvalues)
        w=trials*mu*(1-mu);bread=np.linalg.inv(X.T@(w[:,None]*X))
        scores=X*(trials*(y-mu))[:,None];h=w*np.einsum('ij,jk,ik->i',X,bread,X)
        hc3=bread@((scores/(1-h[:,None])).T@(scores/(1-h[:,None])))@bread
    if not np.isfinite(b).all() or not np.isfinite(hc3).all(): raise ValueError('nonfinite fit')
    return b,bread,scores,hc3


def im_test(X,y,labels,design,trials=None,term=1,level=.90):
    betas=[]
    for label in np.unique(labels):
        keep=labels==label
        b,_,_,_=fit_components(X[keep],y[keep],design,None if trials is None else trials[keep])
        betas.append(b[term])
    est=float(np.mean(betas));se=float(np.std(betas,ddof=1)/np.sqrt(len(betas)))
    critical=t.ppf((1+level)/2,len(betas)-1)
    return est,se,est-critical*se,est+critical*se


def _restricted_scores(X,y,design,trials,term,null):
    nuisance=np.delete(X,term,axis=1)
    offset=X[:,term]*null
    if design=='linear':
        resid=y-offset-nuisance@np.linalg.lstsq(nuisance,y-offset,rcond=None)[0]
        return X*resid[:,None]
    # Offset GLM nuisance MLE, with a stable one-intercept Newton solve for validation.
    if nuisance.shape[1]==1 and np.all(nuisance[:,0]==1):
        mean=np.clip(np.average(y,weights=trials),1e-10,1-1e-10)
        a=float(np.log(mean/(1-mean))-np.average(offset,weights=trials))
        for _ in range(100):
            mu=expit(a+offset);information=np.sum(trials*mu*(1-mu))
            if information<=0: raise ValueError('restricted fit singular')
            step=np.clip(np.sum(trials*(y-mu))/information,-5,5);a+=step
            if abs(step)<1e-10:break
        else:raise ValueError('restricted fit did not converge')
        mu=expit(a+offset)
    else:
        f=sm.GLM(y,nuisance,family=sm.families.Binomial(),var_weights=trials,offset=offset).fit()
        if not f.converged:raise ValueError('restricted fit did not converge')
        mu=np.asarray(f.fittedvalues)
    return X*(trials*(y-mu))[:,None]


def wild_cluster_test(X,y,labels,design,trials=None,term=1,null=0.,weights=None,
                      components=None,interval=False,level=.90):
    """Restricted WCR / Score2-Wald; supports one coefficient, no ACS sampling SE."""
    labels=np.asarray(labels);g=len(np.unique(labels));n,k=X.shape
    if weights is None: raise ValueError('explicit frozen bootstrap weights required')
    weights=np.asarray(weights,float)
    if weights.shape!=(999,g):raise ValueError('999 cluster weight draws required')
    b,bread,scores,_=components or fit_components(X,y,design,trials)
    cov=cluster_covariance(scores,bread,labels);se=float(np.sqrt(cov[term,term]));est=float(b[term])
    if not np.isfinite(se) or se<=0:raise ValueError('bootstrap has no finite positive SE')
    c=bread[:,term];factor=g/(g-1)*(n-1)/(n-k)
    if design=='linear':
        info_groups=group_sums(X[:,:,None]*X[:,None,:],labels)
        correction=info_groups@c
    else:
        # Score2-Wald studentizes restricted perturbations with unrestricted scores.
        projection=group_sums(scores,labels)@c
        denominator=np.sqrt(factor*((weights*projection[None,:])**2).sum(axis=1))
    def pvalue(value):
        grouped=group_sums(_restricted_scores(X,y,design,trials,term,value),labels)
        rhs=weights@grouped;delta=rhs@bread.T
        if design=='linear':
            influences=weights*(grouped@c)[None,:]-delta@correction.T
            denom=np.sqrt(factor*np.sum(influences**2,axis=1))
        else:denom=denominator
        if not np.isfinite(denom).all() or (denom<=0).any():raise ValueError('invalid bootstrap studentization')
        ts=delta[:,term]/denom;obs=(est-value)/se
        return float((1+np.count_nonzero(np.abs(ts)>=abs(obs)))/(len(weights)+1))
    p=pvalue(null);lo=hi=None
    if interval:
        # Invert endpoints of the same restricted test about the estimate.
        # Fixed brackets/tolerance; disconnected confidence sets are not characterized.
        ends=[]
        for direction in (-1,1):
            inside=est;step=se*t.ppf((1+level)/2,g-1);outside=est+direction*step
            for _ in range(20):
                if pvalue(outside)<1-level:break
                step*=2;outside=est+direction*step
            else:raise ValueError('bootstrap CI not bracketed in 20 doublings')
            for _ in range(24):
                middle=(inside+outside)/2
                if pvalue(middle)>=1-level:inside=middle
                else:outside=middle
            ends.append((inside+outside)/2)
        lo,hi=ends
    return {'estimate':est,'p_value':p,'ci_lower':lo,'ci_upper':hi,'se_cr1':se,'df':g-1}


def county_points():
    with patch('requests.sessions.Session.request',side_effect=RuntimeError('Round 26 uses cached boundaries only')):
        ids=sorted(g for st in ('26','36') for g in get_boundaries('county',2020,st).GEOID.astype(str))
        if len(ids)!=145:raise ValueError(f'expected 145 cached counties, got {len(ids)}')
        coords,provenance=unit_coordinates(ids,'county',2020)
    return coords,provenance


def run(draws):
    coords,provenance=county_points();dist=haversine_matrix(coords.lon,coords.lat)
    labels={g:cluster_points(coords,g) for g in (8,12)}
    records=[]
    for cell,(design,r) in enumerate((d,r) for d in ('linear','binomial') for r in (0,50,100)):
        rng,L,trials=simulation_setup(design,r,dist,20261126+cell)
        accum={name:{'cover':0,'failed':0,'widths':[]} for name in CANDIDATES};hc3_width=[]
        beta=.5 if design=='linear' else .3
        for draw in range(draws):
            X,y=simulation_draw(design,L,trials,rng)
            try:
                comp=fit_components(X,y,design,trials);b,bread,scores,hc3=comp
                hc3_width.append(float(2*norm.ppf(.95)*np.sqrt(hc3[1,1])))
            except (ValueError,np.linalg.LinAlgError):
                for v in accum.values():v['failed']+=1
                continue
            for name,(method,g) in CANDIDATES.items():
                v=accum[name]
                try:
                    if method=='cr1_t':
                        se=np.sqrt(cluster_covariance(scores,bread,labels[g])[1,1]);critical=t.ppf(.95,g-1)
                        lo,hi=b[1]-critical*se,b[1]+critical*se;covered=lo<=beta<=hi
                    elif method=='im':
                        _,_,lo,hi=im_test(X,y,labels[g],design,trials);covered=lo<=beta<=hi
                    else:
                        brng=np.random.default_rng(np.random.SeedSequence([20261126,cell,draw,3]))
                        weights=WEBB[brng.integers(0,6,size=(999,g))]
                        z=wild_cluster_test(X,y,labels[g],design,trials,null=beta,weights=weights,components=comp,interval=True)
                        lo,hi=z['ci_lower'],z['ci_upper'];covered=z['p_value']>=.10
                    if not np.isfinite([lo,hi]).all() or hi<lo:raise ValueError('invalid interval')
                    v['widths'].append(float(hi-lo));v['cover']+=int(covered)
                except (ValueError,RuntimeError,np.linalg.LinAlgError):v['failed']+=1
        for name,v in accum.items():
            coverage=v['cover']/draws
            records.append({'candidate':name,'design':design,'range_km':r,'draws':draws,'seed':20261126+cell,
                            'coverage':coverage,'mc_se':float(np.sqrt(coverage*(1-coverage)/draws)),
                            'failed_draws':v['failed'],'mean_width':float(np.mean(v['widths'])) if v['widths'] else None,
                            'hc3_mean_width':float(np.mean(hc3_width)) if hc3_width else None})
        print(design,r,' '.join(f"{name}={v['cover']/draws:.4f} failed={v['failed']}" for name,v in accum.items()),flush=True)
    for row in records:
        baseline=next(r['hc3_mean_width'] for r in records if r['design']==row['design'] and r['range_km']==0)
        row['width_relative_to_hc3_range0']=row['mean_width']/baseline if row['mean_width'] is not None else None
    passed={name:all(r['coverage']>=.86 for r in records if r['candidate']==name) for name in CANDIDATES}
    eligible=[r for r in records if r['design']=='binomial' and r['range_km']==100 and passed[r['candidate']]]
    chosen=min(eligible,key=lambda r:(r['mean_width'],0 if r['candidate'].startswith('C1') else 1,r['candidate']))['candidate'] if eligible else None
    return {'criterion':'90% coverage >=0.86 in all six cells, each candidate separately','passed':passed,
            'default':chosen,'rows':records,'assignments':{str(g):dict(zip(coords.GEOID.astype(str),map(int,lab))) for g,lab in labels.items()},
            'coordinates':json.loads(json.dumps(provenance).replace(str(ROOT)+'/', '').replace(str(Path.home())+'/', '<home>/'))}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--smoke-draws',type=int);p.add_argument('--criterion-commit')
    args=p.parse_args()
    if args.smoke_draws is not None:
        if not 1<=args.smoke_draws<=20:p.error('smoke draws must be 1..20; no audits written')
        run(args.smoke_draws);return
    if not args.criterion_commit:p.error('full run requires --criterion-commit')
    prereg=('scripts/spatial_cluster_validation.py','scripts/spatial_hac_validation.py',
            'docs/audits/spatial_cluster_validation_criterion.md')
    for rel in prereg:
        committed=subprocess.check_output(['git','show',args.criterion_commit+':'+rel],cwd=ROOT)
        if committed!=(ROOT/rel).read_bytes():raise SystemExit('script/design differs from pre-run commit')
    result=run(2000);result['criterion_commit']=args.criterion_commit
    result['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    out=ROOT/'docs/audits/spatial_cluster_validation'
    out.with_suffix('.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    lines=['# Spatial cluster validation (Round 26)','',result['criterion'],
           '',f"Criterion commit: `{args.criterion_commit}`. No seeds, designs or criteria changed.",
           '', '| Candidate | Design | Range km | Coverage | MC SE | Mean width / HC3 range 0 | Failed |',
           '|:---|:---|---:|---:|---:|---:|---:|']
    for r in result['rows']:
        width='undefined' if r['width_relative_to_hc3_range0'] is None else f"{r['width_relative_to_hc3_range0']:.3f}"
        lines.append(f"| {r['candidate']} | {r['design']} | {r['range_km']} | {r['coverage']:.4f} | {r['mc_se']:.4f} | {width} | {r['failed_draws']} |")
    lines+=['','Candidate outcomes: '+', '.join(f"{k}: {'PASS' if v else 'FAIL'}" for k,v in result['passed'].items())+'.',
            '', 'Default: '+(result['default'] or '**none; all candidates exploratory only**')+'.',
            '', 'Clusters: fixed 50-restart projected-point k-means, minimum five counties. Assignments and boundary provenance in JSON.',
            'C3 uses bracketed endpoint inversion of the restricted test for widths; disconnected confidence sets are not characterized.',
            'Failed fits, singular covariance or unbracketed bootstrap intervals count as non-coverage; none are dropped from the denominator.',
            '', 'References: Bester, Conley & Hansen (2011), J Econometrics 165:137–151; Ibragimov & Müller (2010), JBES 28:453–468;',
            '[Kline & Santos (2012), Score2-Wald](https://eml.berkeley.edu/~pkline/papers/ScoreFinal_web.pdf).']
    out.with_suffix('.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':main()
