# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 26 reference, inference-contract and offline integration checks."""
import copy
import importlib.util
from pathlib import Path
from unittest import mock
import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from scipy.stats import t
from census import spatial_clusters as sc
from census.models import fit_replicate
from census.manifest import validate_manifest, manifest_hash, run_manifest, methods_section
from census.results import interval_description
from census.variance import REPLICATE_COLUMNS


def sample(n=96):
    rng=np.random.default_rng(26)
    x=rng.normal(size=n);y=1+.5*x+rng.normal(size=n)
    ids=[f'36061{(i+1)*100:06}' for i in range(n)]
    f=pd.DataFrame({'GEOID':ids,'Year':2019,'y':y,'x':x})
    coords=pd.DataFrame({'GEOID':ids,'lon':-85+np.arange(n)%12*.12,'lat':40+np.arange(n)//12*.12})
    return f,coords


def manifest(method='im',k=8):
    from tests.test_round24 import manifest as base
    m=base();m.pop('exploratory',None)
    m['analyses']=[dict(id='m1',method='fit_replicate',formula='income ~ pop',args={'spatial_clusters':{'method':method,'k':k}})]
    m['hypotheses']=[dict(id='H1',analysis='m1',statistic='coefficient',term='pop',direction='greater')]
    return m


def test_assignment_deterministic_minimum_and_order():
    f,coords=sample()
    a=sc.cluster_points(coords,8);b=sc.cluster_points(coords,8)
    np.testing.assert_array_equal(a,b)
    assert len(np.unique(a))==8 and np.bincount(a).min()>=5
    with mock.patch.object(sc,'unit_coordinates',side_effect=lambda ids,*args:(coords.set_index('GEOID').loc[ids].reset_index(),{})):
        aa=sc.spatial_clusters(f.GEOID,'tract',2019,8)
        bb=sc.spatial_clusters(f.GEOID.iloc[::-1],'tract',2019,8)
    pd.testing.assert_frame_equal(aa,bb)


def test_cr1_matches_independent_statsmodels():
    f,_=sample();X=sm.add_constant(f.x).to_numpy();labels=np.repeat(np.arange(8),12)
    fit=sm.OLS(f.y,X).fit(cov_type='cluster',cov_kwds={'groups':labels})
    bread=np.linalg.inv(X.T@X);scores=X*(f.y.to_numpy()-X@fit.params)[:,None]
    np.testing.assert_allclose(sc.cluster_covariance(scores,bread,labels),fit.cov_params(),rtol=1e-12,atol=1e-12)


def test_binomial_scores_hand_calculation():
    X=np.column_stack((np.ones(12),np.linspace(-1,1,12)))
    trials=np.arange(40,52);y=np.array([2,4,3,5,4,8,7,9,10,10,14,13])/trials
    b,bread,scores,hc3=sc.fit_components(X,y,'binomial',trials)
    mu=1/(1+np.exp(-X@b));expected=np.array([X[i]*trials[i]*(y[i]-mu[i]) for i in range(12)])
    np.testing.assert_allclose(scores,expected,atol=1e-12)
    expected_bread=np.linalg.inv(sum(trials[i]*mu[i]*(1-mu[i])*np.outer(X[i],X[i]) for i in range(12)))
    np.testing.assert_allclose(bread,expected_bread)


def test_frozen_reference_kernels_match_production():
    path=Path(__file__).resolve().parents[1]/'scripts/spatial_cluster_validation.py'
    spec=importlib.util.spec_from_file_location('r26_reference',path);reference=importlib.util.module_from_spec(spec);spec.loader.exec_module(reference)
    f,coords=sample();labels=sc.cluster_points(coords,8);X=sm.add_constant(f.x).to_numpy()
    np.testing.assert_array_equal(labels,reference.cluster_points(coords,8))
    a=sc.im_test(X,f.y.to_numpy(),labels,'linear');b=reference.im_test(X,f.y.to_numpy(),labels,'linear')
    np.testing.assert_array_equal(a,b)
    weights=sc.WEBB[np.random.default_rng(3).integers(0,6,(999,8))]
    a=sc.wild_cluster_test(X,f.y.to_numpy(),labels,'linear',weights=weights,interval=True)
    b=reference.wild_cluster_test(X,f.y.to_numpy(),labels,'linear',weights=weights,interval=True)
    assert a==b


def test_im_t_interval_and_distinct_se_contract():
    f,c=sample();r=fit_replicate('y ~ x',f,coords=c,spatial_clusters={'k':8,'method':'im'})
    row=r.coefficients.set_index('term').loc['x']
    assert row.ci_upper-row.estimate==pytest.approx(t.ppf(.95,7)*row.se_cluster_mean)
    assert np.isnan(row.se_model) and np.isnan(row.se_total)
    info=interval_description(r)
    assert info['basis_column']=='se_cluster_mean' and info['distribution']=='t' and info['df']['x']==7
    assert info['undefined_terms']==[]
    assert 'between-cluster spread' in ' '.join(r.notes)
    assert len(r.diagnostics['spatial_clusters']['assignment'])==96


def test_cr1_combined_acs_interval_uses_t():
    f,c=sample();rng=np.random.default_rng(9);parts=[]
    for var in ('x','y'):
        rep=pd.DataFrame(f[var].to_numpy()[:,None]+rng.normal(0,.02,(len(f),80)),columns=REPLICATE_COLUMNS)
        rep['GEOID']=f.GEOID;rep['variable']=var;rep['Year']=2019;parts.append(rep)
    r=fit_replicate('y ~ x',f,replicates=pd.concat(parts),coords=c,target='conservative',spatial_clusters={'k':8,'method':'cr1_t'})
    row=r.coefficients.iloc[1]
    assert row.se_total==pytest.approx(np.hypot(row.se_model,row.se_sampling))
    assert row.ci_upper-row.estimate==pytest.approx(t.ppf(.95,7)*row.se_total)
    assert any('EXPLORATORY ONLY' in n for n in r.notes)


def test_wcr_reports_inverted_interval_without_scalar_se():
    f,c=sample();r=fit_replicate('y ~ x',f,coords=c,spatial_clusters={'k':12,'method':'wcr'})
    info=interval_description(r)
    assert info['distribution']=='wild_cluster_bootstrap' and info['basis_column']=='bootstrap_test'
    assert not info['undefined_terms']
    assert r.coefficients.se_model.isna().all() and r.coefficients.p_value.between(0,1).all()
    from census.manifest.run import _statistic
    h=_statistic({'statistic':'coefficient','term':'x'},r)
    assert h['se'] is None and h['ci_lower']<h['ci_upper']


@pytest.mark.parametrize('bad',[{}, {'k':8}, {'k':True,'method':'im'}, {'k':1,'method':'im'}, {'k':8.,'method':'im'}, {'k':8,'method':'no'}, {'k':8,'method':[]}, {'k':8,'method':'im','seed':3}])
def test_manifest_argument_validity(bad):
    m=manifest();m['analyses'][0]['args']['spatial_clusters']=bad
    errors=validate_manifest(m,resolve=False)
    assert any('spatial_clusters' in e and 'm1' in e for e in errors),errors


@pytest.mark.parametrize('extra',[{'scale':'robust'},{'spatial_se':{'cutoff_km':100}}])
def test_mutual_exclusions(extra):
    m=manifest();m['analyses'][0]['args'].update(extra)
    assert any('mutually exclusive' in e for e in validate_manifest(m,resolve=False))
    f,c=sample()
    with pytest.raises(ValueError,match='mutually exclusive'):
        fit_replicate('y ~ x',f,coords=c,spatial_clusters={'k':8,'method':'im'},**extra)


def test_exploratory_gate_import_target_and_validated_k(monkeypatch):
    m=manifest();assert validate_manifest(m,resolve=False)==[]
    monkeypatch.setitem(sc.SPATIAL_CLUSTERS_VALIDATED,'im',False)
    assert any('exploratory only' in e for e in validate_manifest(m,resolve=False))
    m['exploratory']=True;assert validate_manifest(m,resolve=False)==[]
    monkeypatch.setitem(sc.SPATIAL_CLUSTERS_VALIDATED,'im',True)
    m=manifest(k=12)
    assert any('exploratory only' in e for e in validate_manifest(m,resolve=False))


@pytest.mark.parametrize('method,k',[('cr1_t',8),('cr1_t',12),('wcr',12)])
def test_failed_candidates_not_promoted(method,k):
    m=manifest(method,k)
    assert any('exploratory only' in e for e in validate_manifest(m,resolve=False))
    m['exploratory']=True;assert validate_manifest(m,resolve=False)==[]


@pytest.mark.parametrize('method',['im','wcr'])
def test_incompatible_target_and_acs_replicates_refused(method,monkeypatch):
    monkeypatch.setitem(sc.IM_ACS_VALIDATED,'ols',False)
    f,c=sample()
    with pytest.raises(ValueError,match="target='population'"):
        fit_replicate('y ~ x',f,target='conservative',coords=c,spatial_clusters={'k':8,'method':method})
    reps=pd.DataFrame({'variable':['x']})
    with pytest.raises(ValueError,match='ACS replicates'):
        fit_replicate('y ~ x',f,replicates=reps,coords=c,spatial_clusters={'k':8,'method':method})
    m=manifest(method);m['analyses'][0]['replicates']='required'
    assert any('declared ACS replicates' in e for e in validate_manifest(m,resolve=False))


def test_hash_includes_cluster_spec_and_methods_prose():
    m=manifest();before=manifest_hash(m);m['analyses'][0]['args']['spatial_clusters']['k']=12
    assert manifest_hash(m)!=before
    text=methods_section(manifest())
    assert 'Ibragimov-Müller' in text and 't(7)' in text and 'between-cluster spread' in text


def test_im_rank_deficiency_refused(monkeypatch):
    monkeypatch.setitem(sc.IM_ACS_VALIDATED,'ols',False)
    f,c=sample();labels=sc.cluster_points(c,8);f['group_indicator']=(labels==0).astype(float)
    with pytest.raises(ValueError,match='full-rank design'):
        fit_replicate('y ~ x + group_indicator',f,coords=c,spatial_clusters={'k':8,'method':'im'})


def test_offline_manifest_bundle(tmp_path,monkeypatch):
    import tests.test_manifest as fixtures
    monkeypatch.setattr(fixtures,'N_TRACTS',96)
    client=fixtures.FakeClient();client.synthetic=True
    m=manifest();m['data_source']={'synthetic':True,'description':'Frozen offline cluster example'}
    _,coords=sample()
    with mock.patch.object(sc,'unit_coordinates',side_effect=lambda ids,*args:(coords.set_index('GEOID').loc[ids].reset_index(),{})):
        out=run_manifest(m,tmp_path,client=client,use_cache=False)
    assert out['success'],out.get('deviations',out.get('errors'))
    assert out['hypotheses'].iloc[0].status=='tested'
    model=out['results']['m1']
    assert model.diagnostics['spatial_clusters']['k']==8
    import json
    saved=json.loads((tmp_path/'bundle/results/m1.json').read_text(encoding='utf-8'))
    assert len(saved['diagnostics']['spatial_clusters']['assignment'])==96
    text=(tmp_path/'bundle/methods.md').read_text(encoding='utf-8')
    assert 'Ibragimov-Müller' in text and 'between-cluster spread' in text


@pytest.mark.parametrize('model',['poisson','wls'])
def test_unvalidated_model_families_refused(model,monkeypatch):
    monkeypatch.setitem(sc.IM_ACS_VALIDATED,'poisson',False)
    f,c=sample()
    with pytest.raises(ValueError,match='not validated'):
        fit_replicate('y ~ x',f,model=model,coords=c,spatial_clusters={'k':8,'method':'im'})
    m=manifest();m['analyses'][0]['args']['model']=model
    assert any('not validated' in e for e in validate_manifest(m,resolve=False))


def test_binomial_im_matches_explicit_cluster_fits():
    f,c=sample();rng=np.random.default_rng(826)
    f['births']=2000.;mu=1/(1+np.exp(-(-2.6+.3*f.x)))
    f['y']=rng.binomial(2000,mu)/2000
    r=fit_replicate('y ~ x',f,model='binomial',trials='births',coords=c,spatial_clusters={'k':8,'method':'im'})
    labels=sc.cluster_points(c,8);fits=[]
    for g in np.unique(labels):
        sub=f[labels==g]
        fits.append(sm.GLM(sub.y,sm.add_constant(sub.x),family=sm.families.Binomial(),var_weights=sub.births).fit().params.to_numpy())
    np.testing.assert_allclose(r.coefficients.estimate,np.mean(fits,axis=0),rtol=1e-10,atol=1e-10)
    np.testing.assert_allclose(r.coefficients.se_cluster_mean,np.std(fits,axis=0,ddof=1)/np.sqrt(8),rtol=1e-10)
    from tests.test_round22 import count_manifest
    m=count_manifest();m['analyses'][0]['args'].pop('scale')
    m['analyses'][0]['args']['spatial_clusters']={'k':8,'method':'im'}
    assert validate_manifest(m,resolve=False)==[]


def test_assignment_not_recomputed_after_outcome_filtering():
    f,c=sample();labels=sc.cluster_points(c,8);group=np.flatnonzero(labels==0)
    f.loc[group[4:],'y']=np.nan
    with pytest.raises(ValueError,match='>=5 analysed'):
        fit_replicate('y ~ x',f,coords=c,spatial_clusters={'k':8,'method':'im'})


def test_posthoc_comparisons_verify_cached_result_hashes(tmp_path):
    import json,hashlib
    path=Path(__file__).resolve().parents[1]/'scripts/r26_posthoc_spatial_clusters.py'
    spec=importlib.util.spec_from_file_location('r26_posthoc',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    inventory={}
    for rel in ('results/run.json','results/m2.json','tables/hypotheses.csv'):
        p=tmp_path/'bundle'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('frozen fixture\n')
        inventory[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
    (tmp_path/'bundle/bundle.json').write_text(json.dumps({'files':inventory}))
    assert len(module.verify_bundle_assets(tmp_path))==3
    (tmp_path/'bundle/tables/hypotheses.csv').write_text('changed p-values\n')
    with pytest.raises(ValueError,match='SHA-256 mismatch'):
        module.verify_bundle_assets(tmp_path)
