# SPDX-License-Identifier: AGPL-3.0-or-later
"""Independent scientific references, failure paths and offline Round 27 bundles."""
import copy
import importlib.util
import json
from pathlib import Path
from unittest import mock
import numpy as np
import pandas as pd
import patsy
import pytest
import statsmodels.api as sm
from scipy.optimize._numdiff import approx_derivative
from scipy.special import gammainc
from scipy.stats import nbinom, chi2
from census import rate_smoothing as eb
from census import splines
from census.models import fit_replicate, fit_eiv, _fit
from census.manifest import validate_manifest,run_manifest,methods_section
from census.simulation import make_replicates,replicate_long


def reference(name):
    path=Path(__file__).resolve().parents[1]/f'scripts/{name}.py'
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def count_data():
    ids=pd.Index(['01001','01003','01005','01007','01009'],name='GEOID')
    return (pd.Series([0.,2.,np.nan,28.,0.],index=ids),pd.Series([2.,5.,9.,12.,18.],index=ids),
            pd.Series([np.nan,np.nan,1.,np.nan,np.nan],index=ids),pd.Series([np.nan,np.nan,9.,np.nan,np.nan],index=ids))


def test_nb_likelihood_and_analytic_derivatives_independent():
    o,e,l,u=count_data();counts=o.fillna(0).to_numpy(int)[None,:];low=l.fillna(-1).to_numpy(int)[None,:];up=u.fillna(-1).to_numpy(int)[None,:]
    x=np.log([7.,6.]);v,g,h=eb._likelihood(x[None,:],counts,e.to_numpy(),low,up)
    expected=sum(nbinom.logpmf(o.iloc[j],7.,6/(6+e.iloc[j])) if j!=2
                 else np.log(nbinom.cdf(9,7.,6/(6+e.iloc[j]))-nbinom.cdf(0,7.,6/(6+e.iloc[j]))) for j in range(5))
    assert v[0]==pytest.approx(expected,abs=1e-12)
    ng=approx_derivative(lambda a:eb._likelihood(a[None,:],counts,e.to_numpy(),low,up,False),x)
    nh=approx_derivative(lambda a:eb._likelihood(a[None,:],counts,e.to_numpy(),low,up)[1][0],x)
    np.testing.assert_allclose(g[0],ng,rtol=1e-7)
    np.testing.assert_allclose(h[0],nh,rtol=1e-7)


def test_posterior_mixture_mean_and_quantiles_independent():
    o,e,l,u=count_data();a,b=7.,6.;ks,w=eb._mixture_weights(np.array([a]),np.array([b]),np.array([9.]),1,9)
    expected=nbinom.pmf(np.arange(1,10),a,b/(b+9));expected/=expected.sum()
    np.testing.assert_allclose(w[0],expected,rtol=1e-12);assert w.sum()==pytest.approx(1.)
    mean,lo,hi=eb._posterior(a,b,o.fillna(0).to_numpy(),e.to_numpy(),l.fillna(-1).to_numpy(int),u.fillna(-1).to_numpy(int))
    assert mean[1]==pytest.approx((a+2)/(b+5))
    assert mean[2]==pytest.approx((a+expected@ks)/(b+9))
    for q,val in [(.05,lo[2]),(.95,hi[2])]:
        assert expected@gammainc(a+ks,(b+9)*val)==pytest.approx(q,abs=1e-10)


@pytest.mark.parametrize('change', ['negative','fractional','zero_E','negative_E','missing','infinite','bad_bounds','wrong_index','duplicate_index','disclosed_censored'])
def test_eb_invalid_inputs_refused(change):
    o,e,l,u=count_data()
    if change=='negative':o.iloc[0]=-1
    elif change=='fractional':o.iloc[0]=.5
    elif change=='zero_E':e.iloc[0]=0
    elif change=='negative_E':e.iloc[0]=-1
    elif change=='missing':o.iloc[0]=np.nan
    elif change=='infinite':o.iloc[0]=np.inf
    elif change=='bad_bounds':u.iloc[2]=.5
    elif change=='wrong_index':e=e.iloc[::-1]
    elif change=='duplicate_index':o.index=['a','a','b','c','d']
    elif change=='disclosed_censored':o.iloc[2]=5
    with pytest.raises(ValueError):eb.eb_poisson_gamma(o,e,l,u)


def test_eb_frozen_kernel_parity_and_suppression_preserved():
    o,e,l,u=count_data();ref=reference('eb_rate_validation')
    out=eb.eb_poisson_gamma(o,e,l,u,interval='laird_louis',seed=31,reference_rate=123.)
    fit=ref._intervals(o.fillna(0).to_numpy(),e.to_numpy(),l.fillna(-1).to_numpy(int),u.fillna(-1).to_numpy(int),seed=31)
    np.testing.assert_array_equal(out.eb_ratio,fit['point'])
    np.testing.assert_array_equal(out.eb_lower,fit['laird_louis_lower'])
    assert out.index.equals(o.index) and np.isnan(out.loc['01005','observed']) and np.isnan(out.loc['01005','raw_ratio'])
    assert out.attrs['beta_convention']=='rate' and out.attrs['descriptive_only']
    np.testing.assert_allclose(out.eb_rate,out.eb_ratio*123)
    np.testing.assert_allclose(out.shrinkage,fit['beta']/(fit['beta']+e))


def test_wonder_parser_exact_bounds_are_not_censored():
    o,e,l,u=count_data();l=l.fillna(o);u=u.fillna(o)
    out=eb.eb_poisson_gamma(o,e,l,u)
    assert out.censored.sum()==1 and out.loc['01003','raw_ratio']==pytest.approx(.4)


def test_ml_and_bootstrap_failures_never_fall_back(monkeypatch):
    o,e,l,u=count_data()
    monkeypatch.setattr(eb,'_fit_batch',mock.Mock(side_effect=RuntimeError('ML failed')))
    with pytest.raises(RuntimeError,match='ML failed'):eb.eb_poisson_gamma(o,e,l,u)
    fit=np.array([[7.,6.]])
    monkeypatch.setattr(eb,'_fit_batch',mock.Mock(side_effect=[fit,RuntimeError('bootstrap failed')]))
    with pytest.raises(RuntimeError,match='bootstrap failed'):eb.eb_poisson_gamma(o,e,l,u,interval='laird_louis',seed=1)


def test_eb_validation_note_gate_and_nondefault_level(monkeypatch):
    o,e,l,u=count_data()
    monkeypatch.setitem(eb.EB_VALIDATED,'posterior',False)
    out=eb.eb_poisson_gamma(o,e,l,u,interval='posterior')
    assert not out.attrs['validated'] and 'NOT VALIDATED' in out.attrs['validation_note']
    monkeypatch.setitem(eb.EB_VALIDATED,'posterior',True)
    assert not eb.eb_poisson_gamma(o,e,l,u,level=.95).attrs['validated']


def sample():
    rng=np.random.default_rng(93);n=145;x=rng.normal(size=n);z=rng.normal(size=n)
    f=pd.DataFrame({'GEOID':[str(i) for i in range(n)],'x':x,'z':z,'y':1+.5*z+rng.normal(size=n)})
    reps=make_replicates(x[:,None],np.full((n,1),.15),rng)[:,0,:]
    r=replicate_long(f.GEOID,['x'],x[:,None],reps[:,None,:])
    return f,r,reps


@pytest.mark.parametrize('model',['linear','binomial'])
def test_frozen_validation_kernel_matches_statsmodels_and_full_covariance(model):
    f,r,reps=sample();ref=reference('joint_wald_validation');n=len(f)
    if model=='binomial':
        rng=np.random.default_rng(94);f['trials']=1000.;f['y']=rng.binomial(1000,1/(1+np.exp(2-.3*f.z-.5*rng.normal(size=n))))/1000
    formula='y ~ cr(x, df=3) + z';X=patsy.dmatrix('1+cr(x,df=3,constraints="center")+z',f,return_type='dataframe')
    R=patsy.build_design_matrices([X.design_info],{'x':reps.T.ravel(),'z':np.tile(f.z,80)})[0]
    designs=np.concatenate([np.asarray(X)[None,:,:],np.asarray(R).reshape(80,n,-1)])
    b,cov=ref.fit_batch(designs,f.y.to_numpy(),model,np.full(n,1000.))
    result=fit_replicate(formula,f,r,model='ols' if model=='linear' else model,trials='trials' if model=='binomial' else None,
                         scale='robust' if model=='binomial' else None,target='conservative',replicate_policy='strict')
    np.testing.assert_allclose(result.coefficients.estimate,b[0],rtol=1e-7,atol=1e-9)
    np.testing.assert_allclose(result.diagnostics['joint_model_covariance'],cov,rtol=1e-7,atol=1e-10)
    delta=b[1:]-b[0];sampling=.05*delta.T@delta
    np.testing.assert_allclose(result.diagnostics['sampling_covariance'],sampling,rtol=1e-6,atol=1e-10)
    # Off-diagonal entries matter: the joint test must use the whole matrix.
    W,p=ref.joint_stat(b[0,1:4],(cov+sampling)[1:4,1:4]);j=splines.joint_wald(result,'x')
    assert j['estimate']==pytest.approx(W,rel=1e-6) and j['p_two_sided']==pytest.approx(p,rel=1e-6)
    assert j['df']==3 and j['ci_lower'] is None
    saved=result.to_dict()['diagnostics']['sampling_covariance']
    assert saved['index']==result.coefficients.term.tolist() and saved['columns']==saved['index']


def test_knots_and_centering_fixed_in_every_replicate():
    f,_,_=sample();formula=splines.spline_formula('y~cr(x,df=4)+z');full=_fit(formula,f,'ols')
    perturbed=f.copy();perturbed.x=2*f.x+.3
    info=full.model.data.orig_exog.design_info
    fixed=np.asarray(patsy.build_design_matrices([info],perturbed)[0])
    fresh=np.asarray(patsy.dmatrix(formula.split('~')[1],perturbed))
    assert not np.allclose(fixed,fresh)
    expected=np.linalg.lstsq(fixed,perturbed.y,rcond=None)[0]
    np.testing.assert_allclose(splines.frozen_refit(full,perturbed,'ols'),expected,rtol=1e-12,atol=1e-12)
    # Keyword names and string constants must not become stochastic inputs.
    f['df']=np.nan;f['center']=np.nan
    assert fit_replicate('y~cr(x,df=4)+z',f).n_obs==len(f)


@pytest.mark.parametrize('bad',['cr(x)','cr(x,df=2)','cr(x,df=6)','cr(x,df=True)','cr(x,df=3,knots=[1,2])','cr(np.log(x),df=3)'])
def test_invalid_spline_rules(bad):
    with pytest.raises((ValueError,patsy.PatsyError)):splines.spline_formula('y~'+bad)


def manifest():
    from tests.test_round24 import manifest as base
    m=base();m.pop('exploratory',None)
    m['analyses']=[dict(id='m1',method='fit_replicate',formula='income ~ cr(pop, df=4)',args={'target':'conservative'})]
    m['hypotheses']=[dict(id='H1',analysis='m1',statistic='joint_wald',variable='pop',direction='two_sided')]
    return m


@pytest.mark.parametrize('method',['fit_eiv','fh_regression','fay_herriot','simex','regression_calibration'])
def test_spline_outside_replicate_registry_refused(method):
    m=manifest();m['analyses'][0]['method']=method
    assert any('cr splines are supported only' in e for e in validate_manifest(m,resolve=False))


def test_library_spline_exclusions():
    from census.sae import fh_regression
    from census.spatial import spatial_regression
    f,r,_=sample()
    with pytest.raises(ValueError,match='cr splines'):fit_eiv('y~cr(x,df=3)',f,r)
    with pytest.raises(ValueError,match='cr splines'):fh_regression('y~cr(x,df=3)',f,se_col='y_se')
    with pytest.raises(ValueError,match='cr splines'):spatial_regression('y~cr(x,df=3)',f,weights=None)
    with pytest.raises(ValueError,match='cr splines'):fit_replicate('y~cr(x,df=3)',f,spatial_clusters={'method':'im','k':8})


def test_joint_hand_calculation_categorical_and_singular():
    f,_,_=sample();f['region']=np.where(np.arange(len(f))%3==0,'a',np.where(np.arange(len(f))%3==1,'b','c'))
    result=fit_replicate('y~C(region)+z',f);cols=result.diagnostics['joint_columns']['region']
    assert len(cols)==2
    covariance=np.array([[4.,1.],[1.,9.]])
    b=np.array([2.,3.]);idx=result.coefficients.term.isin(cols)
    result.coefficients.loc[idx,'estimate']=b;result.diagnostics['joint_model_covariance'].loc[cols,cols]=covariance
    j=splines.joint_wald(result,'region');W=float(b@np.linalg.solve(covariance,b))
    assert j['estimate']==pytest.approx(W) and j['p_two_sided']==pytest.approx(chi2.sf(W,2))
    result.diagnostics['joint_model_covariance'].loc[cols,cols]=1.
    with pytest.raises(ValueError,match='singular'):splines.joint_wald(result,'region')


@pytest.mark.parametrize('extra',[{'term':'pop'},{'direction':'greater'},{'direction':'less'},{'variable':'absent'}])
def test_joint_hypothesis_validation(extra):
    m=manifest();m['hypotheses'][0].update(extra)
    assert any('joint_wald' in e for e in validate_manifest(m,resolve=False))


def test_confirmatory_gate_checks_actual_import_target(monkeypatch):
    m=manifest();monkeypatch.setattr(splines,'JOINT_WALD_VALIDATED',False)
    errors=validate_manifest(m,resolve=False)
    assert any('cr spline failed' in e for e in errors) and any('joint_wald failed' in e for e in errors)
    m['exploratory']=True
    assert not any('exploratory only' in e for e in validate_manifest(m,resolve=False))


def test_circularity_r2_applies_to_joint_variable():
    from census.manifest.external import circularity_errors
    m=manifest();m['hypotheses'][0]['variable']='poverty'
    m['variables']=[{'name':'poverty','table':'B17001','variable':'B17001_002'}]
    m['analyses'][0]['formula']='diabetes ~ cr(poverty,df=3)'
    c={'analysis':'m1','has_equivalent':False,'kind':'model','outcome':'diabetes','source':'places','overlap':{'poverty':{'Poverty':['B17001']}}}
    with mock.patch('census.manifest.external.external_circularity',return_value=[c]):
        assert any('CIRCULARITY R2' in e for e in circularity_errors(m))
        m['hypotheses'][0]['circularity_justification']='This association includes reused modeled poverty inputs.'
        assert circularity_errors(m)==[]


def test_offline_manifest_joint_bundle_and_singular_deviation(tmp_path,monkeypatch):
    import tests.test_manifest as fixtures
    monkeypatch.setattr(fixtures,'N_TRACTS',96)
    m=manifest();m['exploratory']=True
    m['data_source']={'synthetic':True,'description':'offline Round 27 spline example'}
    client=fixtures.FakeClient();client.synthetic=True
    out=run_manifest(m,tmp_path/'ok',client=client,use_cache=False)
    assert out['success'],out.get('deviations',out.get('errors'))
    h=out['hypotheses'].iloc[0]
    assert h.status=='tested' and h['df']==4 and pd.isna(h.ci_lower) and pd.isna(h.ci_upper)
    assert 'odds_ratio' not in h.index
    assert 'chi-squared(q)' in (tmp_path/'ok/bundle/methods.md').read_text()
    from census.manifest import methods
    with mock.patch.object(methods,'_stat_joint_wald',side_effect=ValueError('singular joint covariance')):
        # Extractor registry holds function objects, so patch its actual lookup.
        with mock.patch.dict(methods.STATISTIC_EXTRACTORS,{'joint_wald':methods._stat_joint_wald}):
            bad=run_manifest(m,tmp_path/'singular',client=client,use_cache=False)
    assert bad['hypotheses'].iloc[0].status=='not_tested'
    assert any(d['kind']=='hypothesis_not_tested' and 'singular' in d['detail'] for d in bad['deviations'])


def test_existing_map_helper_accepts_eb_ratio_without_fabricated_moe(tmp_path):
    from census.maps import choropleth
    from tests.test_maps import _grid
    o,e,l,u=count_data();out=eb.eb_poisson_gamma(o,e,l,u)
    g=_grid(5);g['eb_ratio']=out.eb_ratio.to_numpy()
    fig=choropleth(g,'eb_ratio',k=3,insets=False,out_dir=tmp_path,formats=('svg',),
                   data_source='Descriptive empirical Bayes; fixed expected counts.')
    values=pd.read_csv(tmp_path/'choropleth.csv')
    np.testing.assert_allclose(values.estimate,out.eb_ratio)
    assert values.moe90.isna().all() # EB posterior limits are not ACS margins of error.


def test_joint_standalone_columns_exclude_interactions():
    f,_,_=sample();r=fit_replicate('y~x*z',f)
    assert r.diagnostics['joint_columns']['x']==['x']
    with pytest.raises(ValueError,match='no standalone'):
        splines.joint_wald(fit_replicate('y~x:z',f),'x')


@pytest.mark.parametrize('target',['population','these_areas','conservative'])
def test_joint_uses_requested_target_covariance(target):
    f,r,_=sample();result=fit_replicate('y~x+z',f,r,target=target)
    smat=result.diagnostics['sampling_covariance'];m=result.diagnostics['joint_model_covariance']
    V=smat if target=='these_areas' else m+smat if target=='conservative' else m
    b=result.coefficients.set_index('term').loc['x','estimate']
    assert splines.joint_wald(result,'x')['estimate']==pytest.approx(b*b/V.loc['x','x'])


def test_large_exact_counts_do_not_allocate_count_sized_recurrences():
    counts=np.array([[0,80000,140000,90000,160000]])
    expected=np.array([1.,80000.,110000.,130000.,160000.]);bounds=np.full((1,5),-1)
    ll=eb._likelihood(np.log([[5.,4.]]),counts,expected,bounds,bounds,False)[0]
    expected_ll=nbinom.logpmf(counts[0],5.,4/(4+expected)).sum()
    assert ll==pytest.approx(expected_ll,abs=1e-8)


@pytest.mark.parametrize('model',['wls','poisson'])
def test_spline_replicate_weights_and_exposure_match_independent_refits(model):
    f,r,reps=sample();rng=np.random.default_rng(69);f['w']=rng.uniform(.5,2,len(f))
    if model=='poisson':
        f['e']=rng.uniform(3,12,len(f));f['y']=rng.poisson(f.e*np.exp(.1+.2*f.z))
    result=fit_replicate('y~cr(x,df=4)+z',f,r,model=model,weights='w' if model=='wls' else None,
                         exposure='e' if model=='poisson' else None,scale='robust' if model=='poisson' else None)
    design=patsy.dmatrix('1+cr(x,df=4,constraints="center")+z',f,return_type='dataframe')
    def fit(X):
        return sm.WLS(f.y,X,weights=f.w).fit() if model=='wls' else sm.GLM(f.y,X,family=sm.families.Poisson(),exposure=f.e).fit()
    full=fit(design);coefs=[]
    for j in range(80):
        d=f.copy();d.x=reps[:,j]
        X=patsy.build_design_matrices([design.design_info],d)[0]
        coefs.append(np.asarray(fit(X).params))
    delta=np.asarray(coefs)-np.asarray(full.params)
    np.testing.assert_allclose(result.diagnostics['sampling_covariance'],.05*delta.T@delta,rtol=1e-7,atol=1e-10)


def test_nb_ml_matches_independent_scipy_optimizer():
    from scipy.optimize import minimize
    o,e,l,u=count_data();c=o.fillna(0).to_numpy(int);low=l.fillna(-1).to_numpy(int);up=u.fillna(-1).to_numpy(int)
    fitted=eb._fit_batch(c,e.to_numpy(),low,up)[0]
    def negative_log_likelihood(x):
        a,b=np.exp(x)
        terms=nbinom.logpmf(c,a,b/(b+e.to_numpy()))
        terms[2]=np.log(nbinom.cdf(9,a,b/(b+e.iloc[2]))-nbinom.cdf(0,a,b/(b+e.iloc[2])))
        return -terms.sum()
    independent=minimize(negative_log_likelihood,np.log([1.,1.]),method='BFGS',tol=1e-7)
    np.testing.assert_allclose(np.log(fitted),independent.x,atol=2e-4)
