# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fixed Round 30 validation. Prepare targets, commit/push, then run once.

Smoke <=20 draws/cell writes NO files. Full runs require byte equality to the
criterion commit. Frozen numerical candidates are in census.im_acs.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'scripts'))
import numpy as np
import statsmodels.api as sm
from scipy.special import expit
from census.im_acs import constant_columns, cluster_coefficients, summarize
from census.simulation import make_replicates
from spatial_cluster_validation import county_points
from spatial_hac_validation import simulation_setup, simulation_draw, haversine_matrix

SEED = 20261201
CELLS = [(model, distance, reliability) for model in ('linear','binomial','poisson')
         for distance in (0,100) for reliability in (.9,.7)]
TARGETS = 'docs/audits/im_acs_beta_star.json'
FROZEN = ('scripts/im_acs_validation.py', 'census/im_acs.py', 'census/simulation.py',
          'scripts/spatial_hac_validation.py', 'scripts/spatial_cluster_validation.py',
          'census/spatial_hac.py', 'docs/audits/spatial_cluster_validation.json',
          'docs/audits/im_acs_validation_criterion.md', TARGETS)


def setup(cell, coords):
    model, distance, reliability = CELLS[cell]
    dist = haversine_matrix(coords['lon'],coords['lat'])
    rng, L, trials = simulation_setup('binomial' if model=='binomial' else 'linear', distance, dist, SEED+cell)
    n = len(L)
    exposure = np.maximum(5, np.rint(rng.lognormal(np.log(100),1,n))) if model=='poisson' else None
    se = rng.lognormal(0,.5,(n,2))
    se *= np.sqrt(((1-reliability)/reliability) / np.mean(se**2,axis=0))
    return rng, L, trials, exposure, se


def outcome(model, true, state, error, rng, trials, exposure, null=False, single=False):
    b = .5 if model=='linear' else .3
    signal = (0 if null else b)*true[:,0] + (0 if single else b)*true[:,1]
    if model=='linear': return 1+signal+.3*state+error
    eta = signal+.2*state+.15*error
    if model=='binomial': return rng.binomial(trials.astype(int),expit(-2.6+eta))/trials
    return rng.poisson(exposure*np.exp(eta))


def prepare_targets():
    path = ROOT/TARGETS
    if path.exists(): raise ValueError('refusing to replace committed beta-star values')
    coords, provenance = county_points()
    frozen = json.loads((ROOT/'docs/audits/spatial_cluster_validation.json').read_text())['assignments']['8']
    labels = np.array([frozen[g] for g in coords.GEOID.astype(str)])
    state = coords.GEOID.str.startswith('36').to_numpy(float)
    assert all(len(set(state[labels==g]))==1 for g in range(8))
    records = []
    for cell,(model,distance,reliability) in enumerate(CELLS):
        _,_,trials,exposure,se = setup(cell,coords)
        rng = np.random.default_rng(np.random.SeedSequence([SEED,cell,400000,7]))
        n = 400000
        index = rng.integers(0,len(coords),n)
        z = rng.standard_normal((n,2));true = np.column_stack((z[:,0],.5*z[:,0]+np.sqrt(.75)*z[:,1]))
        e = rng.standard_normal((n,2));u = np.column_stack((e[:,0],.3*e[:,0]+np.sqrt(.91)*e[:,1]))*se[index]
        observed = true+u; st = state[index]
        tr = None if trials is None else trials[index]; ex = None if exposure is None else exposure[index]
        y = outcome(model,true,st,rng.standard_normal(n),rng,tr,ex)
        X = np.column_stack((np.ones(n),observed,st))
        if model=='linear':
            beta = np.linalg.lstsq(X,y,rcond=None)[0][1]
            sigma = np.array([[1,.5],[.5,1.]])
            error_cov = np.array([[np.mean(se[:,0]**2),.3*np.mean(se[:,0]*se[:,1])],
                                  [.3*np.mean(se[:,0]*se[:,1]),np.mean(se[:,1]**2)]])
            closed = np.linalg.solve(sigma+error_cov,sigma@np.array([.5,.5]))[0]
            if abs(beta-closed)>.005: raise ValueError('reference linear target differs from closed form by >.005')
        else:
            kw = ({'family':sm.families.Binomial(),'var_weights':tr} if model=='binomial' else
                  {'family':sm.families.Poisson(),'offset':np.log(ex)})
            fit = sm.GLM(y,X,**kw).fit()
            if not fit.converged: raise ValueError('reference GLM did not converge')
            beta = fit.params[1]; closed = None
        records.append(dict(cell=cell,model=model,range_km=distance,reliability=reliability,
                            beta_star=float(beta),closed_form=None if closed is None else float(closed),reference_n=n))
        print('reference',cell,model,distance,reliability,float(beta),flush=True)
    value = dict(seed=SEED,rows=records,coordinates=coords.to_dict('list'),
                 assignment=dict(zip(coords.GEOID.astype(str),map(int,labels))),
                 geometry='Round 22/26 cached 2020 representative points; fixed Round 26 k=8 assignment')
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def validate_pins(commit):
    subprocess.run(['git','merge-base','--is-ancestor',commit,'HEAD'],cwd=ROOT,check=True)
    for rel in FROZEN:
        committed = subprocess.check_output(['git','show',commit+':'+rel],cwd=ROOT)
        if committed != (ROOT/rel).read_bytes(): raise ValueError('script/design differs from criterion commit: '+rel)


def run(draws):
    targets = json.loads((ROOT/TARGETS).read_text());coords = targets['coordinates']
    ids = coords['GEOID'];state = np.array([float(g.startswith('36')) for g in ids])
    labels = np.array([targets['assignment'][g] for g in ids]);rows=[]
    for cell,(model,distance,reliability) in enumerate(CELLS):
        rng,L,trials,exposure,se = setup(cell,coords)
        target = targets['rows'][cell]['beta_star'];true_beta = .5 if model=='linear' else .3
        accum = {c:dict(cover=0,true_cover=0,failed=0,widths=[],null_reject=0,null_failed=0)
                 for c in (('C1','C2') if model=='linear' else ('C1',))}
        for draw in range(draws):
            # Reuse the exact Round 22 Gaussian spatial-field generator.
            base, old_y = simulation_draw('linear',L,None,rng)
            x1 = base[:,1];error = old_y-1-.5*x1
            true = np.column_stack((x1,.5*x1+np.sqrt(.75)*(L@rng.standard_normal(len(L)))))
            z = rng.standard_normal((len(L),2))
            u = np.column_stack((z[:,0],.3*z[:,0]+np.sqrt(.91)*z[:,1]))*se
            observed = true+u
            y = outcome(model,true,state,error,rng,trials,exposure)
            aux = np.random.default_rng(np.random.SeedSequence([SEED,cell,draw,7]))
            rep = make_replicates(observed,se,aux,corr=np.array([[1.,.3],[.3,1.]]))
            delta = np.zeros((len(L),4,80));delta[:,1:3,:] = rep-observed[:,:,None]
            covariance = .05*np.einsum('nir,njr->nij',delta,delta)
            X = np.column_stack((np.ones(len(L)),observed,state))
            keep,_ = constant_columns(X,labels,['Intercept','x1','x2','NY'])
            cov = covariance[:,keep][:,:,keep]
            for candidate,v in accum.items():
                try:
                    b = cluster_coefficients(X[:,keep],y,labels,model,trials=trials,exposure=exposure,
                                             covariance=cov if candidate=='C2' else None)
                    z = summarize(b);lo,hi = z['lower'][1],z['upper'][1]
                    if not np.isfinite([lo,hi]).all(): raise ValueError('nonfinite interval')
                    goal = true_beta if candidate=='C2' else target
                    v['cover'] += int(lo<=goal<=hi);v['true_cover'] += int(lo<=true_beta<=hi)
                    v['widths'].append(float(hi-lo))
                except (ValueError,RuntimeError,np.linalg.LinAlgError,FloatingPointError): v['failed']+=1
            # Null variants: C2 retains the noisy control; C1 has ONE covariate.
            for candidate,v in accum.items():
                single = candidate=='C1'
                null_y = outcome(model,true,state,error,aux,trials,exposure,null=True,single=single)
                cols = [0,1] if single else [0,1,2]
                try:
                    b = cluster_coefficients(X[:,cols],null_y,labels,model,trials=trials,exposure=exposure,
                                             covariance=cov[:,cols][:,:,cols] if candidate=='C2' else None)
                    z = summarize(b)
                    # One-sided greater test at .05, t(7).
                    from scipy.stats import t
                    v['null_reject'] += int(t.sf(z['estimate'][1]/z['se'][1],7)<.05)
                except (ValueError,RuntimeError,np.linalg.LinAlgError,FloatingPointError):v['null_failed']+=1
        for candidate,v in accum.items():
            coverage = v['cover']/draws
            rows.append(dict(candidate=candidate,cell=cell,model=model,range_km=distance,reliability=reliability,
                             draws=draws,seed=SEED+cell,target=true_beta if candidate=='C2' else target,
                             coverage=coverage,mc_se=float(np.sqrt(coverage*(1-coverage)/draws)),
                             coverage_true_beta=v['true_cover']/draws,failed_draws=v['failed'],
                             mean_width=float(np.mean(v['widths'])) if v['widths'] else None,
                             null_one_sided_size=v['null_reject']/draws,null_failed_draws=v['null_failed']))
        print('cell',cell,model,distance,reliability,
              ' '.join(f"{c}={v['cover']/draws:.4f} failed={v['failed']}" for c,v in accum.items()),flush=True)
    passed = {candidate:{model:all(r['coverage']>=.86 for r in rows if r['candidate']==candidate and r['model']==model)
                         for model in (('linear',) if candidate=='C2' else ('linear','binomial','poisson'))}
              for candidate in ('C1','C2')}
    return dict(criterion='90% coverage >=0.86 in every cell, separately by candidate/model; failures are non-coverage',
                passed=passed,rows=rows,draws_per_cell=draws)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepare-targets',action='store_true');p.add_argument('--smoke-draws',type=int)
    p.add_argument('--criterion-commit');args = p.parse_args()
    with patch('requests.sessions.Session.request',side_effect=RuntimeError('Round 30: HTTP blocked')):
        if args.prepare_targets:
            if args.smoke_draws or args.criterion_commit:p.error('prepare targets is a separate pre-run action')
            prepare_targets();return
        if args.smoke_draws is not None:
            if not 1<=args.smoke_draws<=20:p.error('smoke draws must be 1..20; no audits written')
            run(args.smoke_draws);return
        if not args.criterion_commit:p.error('full run requires --criterion-commit')
        validate_pins(args.criterion_commit)
        out = ROOT/'docs/audits/im_acs_validation'
        if out.with_suffix('.json').exists() or out.with_suffix('.md').exists():p.error('refusing to rerun/overwrite full audit')
        result = run(2000);result['criterion_commit']=args.criterion_commit
        result['frozen_sha256']={rel:hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() for rel in FROZEN}
        out.with_suffix('.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
        lines = ['# IM with ACS sampling error validation (Round 30)','',result['criterion'],'',
                 f"Criterion commit: `{args.criterion_commit}`. Exactly 2,000 draws per cell; nothing retuned.",'',
                 '| Candidate | Model | Range km | Reliability | Coverage | True-beta coverage | Failed | Width | Null size (.05) | Null failed |',
                 '| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
        for r in result['rows']:
            width='unavailable' if r['mean_width'] is None else f"{r['mean_width']:.4f}"
            lines.append(f"| {r['candidate']} | {r['model']} | {r['range_km']} | {r['reliability']} | {r['coverage']:.4f} | {r['coverage_true_beta']:.4f} | {r['failed_draws']} | {width} | {r['null_one_sided_size']:.4f} | {r['null_failed_draws']} |")
        lines += ['', 'Outcomes: `'+json.dumps(result['passed'],sort_keys=True)+'`.','',
                  'C1 targets the committed observed-estimate probability limit, not the true slope. C2 targets the true slope.',
                  'Null size and interval widths are informational. Null failures are reported separately and remain in the size denominator.',
                  'Eight fixed MI/NY clusters; state factor absorbed by the cluster intercept. Failed clusters are never dropped.',
                  'ACS uncertainty enters between-cluster variation; no additive replicate SE. No criterion, seed or target changed.']
        out.with_suffix('.md').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':main()
