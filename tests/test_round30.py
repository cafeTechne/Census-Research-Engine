# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 30 numerical candidates and validation discipline; entirely offline."""
import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from scipy.special import expit
from scipy.stats import t
from census.im_acs import constant_columns, cluster_coefficients, summarize


def sample():
    rng = np.random.default_rng(71)
    labels = np.repeat(np.arange(8),20)
    X = np.column_stack((np.ones(160),rng.normal(size=(160,2))))
    y = 1+X[:,1]*.5+X[:,2]*.5+rng.normal(size=160)
    return rng,labels,X,y


@pytest.mark.parametrize('model',['linear','binomial','poisson'])
def test_c1_matches_independent_cluster_fits(model):
    rng,labels,X,y = sample();trials=np.full(160,100);exposure=np.full(160,50.)
    if model=='binomial':y=rng.binomial(trials,expit(-2+X[:,1]*.3+X[:,2]*.3))/trials
    elif model=='poisson':y=rng.poisson(exposure*np.exp(X[:,1]*.3+X[:,2]*.3))
    result=cluster_coefficients(X,y,labels,model,trials=trials,exposure=exposure)
    independent=[]
    for g in range(8):
        keep=labels==g
        if model=='linear':fit=sm.OLS(y[keep],X[keep]).fit()
        elif model=='binomial':fit=sm.GLM(y[keep],X[keep],family=sm.families.Binomial(),var_weights=trials[keep]).fit()
        else:fit=sm.GLM(y[keep],X[keep],family=sm.families.Poisson(),offset=np.log(exposure[keep])).fit()
        independent.append(fit.params)
    np.testing.assert_allclose(result,independent,atol=1e-10)
    z=summarize(result);mean=np.mean(independent,axis=0);se=np.std(independent,axis=0,ddof=1)/np.sqrt(8)
    np.testing.assert_allclose(z['estimate'],mean);np.testing.assert_allclose(z['se'],se)
    np.testing.assert_allclose(z['lower'],mean-t.ppf(.95,7)*se)
    np.testing.assert_allclose(z['p_two_sided']/2,t.sf(np.abs(mean/se),7))


def test_c2_equals_cluster_only_fuller_and_refuses_one_bad_cluster():
    from census.models import fit_eiv
    from census.simulation import make_replicates,replicate_long
    rng,labels,X,y=sample();ids=[f'{i:05}' for i in range(160)]
    se=np.full((160,2),.05);rep=make_replicates(X[:,1:],se,rng,corr=np.array([[1.,.3],[.3,1.]]))
    d=np.zeros((160,3,80));d[:,1:]=rep-X[:,1:,None]
    cov=.05*np.einsum('nir,njr->nij',d,d)
    result=cluster_coefficients(X,y,labels,'linear',covariance=cov)
    frame=pd.DataFrame({'GEOID':ids,'x1':X[:,1],'x2':X[:,2],'y':y,'x1_se':.05,'x2_se':.05})
    reps=replicate_long(ids,['x1','x2'],X[:,1:],rep)
    for g in range(8):
        f=frame.loc[labels==g].copy()
        direct=fit_eiv('y ~ x1 + x2',f,reps[reps.GEOID.isin(f.GEOID)],replicate_policy='strict',fixed_variables=('y',))
        np.testing.assert_allclose(result[g],direct.coefficients.estimate.to_numpy(),rtol=1e-10)
    broken=cov.copy();broken[labels==3,1,1]=10000
    with pytest.raises(np.linalg.LinAlgError):cluster_coefficients(X,y,labels,'linear',covariance=broken)


def test_constant_term_rule_requires_uniform_constancy():
    _,labels,X,y=sample();state=(labels>=4).astype(float)
    design=np.column_stack((X,state));terms=['Intercept','x1','x2','state']
    keep,dropped=constant_columns(design,labels,terms)
    assert keep.tolist()==[True,True,True,False] and dropped==['state']
    bad=design.copy();bad[labels==1,3]=np.arange(20)
    with pytest.raises(ValueError,match='some clusters'):constant_columns(bad,labels,terms)
    with pytest.raises(ValueError,match='intercept'):constant_columns(design[:,1:],labels,terms[1:])


def test_full_run_requires_exact_preregistered_bytes(monkeypatch,tmp_path):
    from scripts import im_acs_validation as validation
    monkeypatch.setattr(validation,'ROOT',tmp_path)
    monkeypatch.setattr(validation,'FROZEN',('candidate.py',))
    (tmp_path/'candidate.py').write_bytes(b'new')
    monkeypatch.setattr(validation.subprocess,'run',lambda *a,**kw:None)
    monkeypatch.setattr(validation.subprocess,'check_output',lambda *a,**kw:b'frozen')
    with pytest.raises(ValueError,match='differs from criterion'):validation.validate_pins('criterion')


def test_smoke_limit_and_absent_criterion_refuse_without_simulation(monkeypatch):
    import sys
    from scripts import im_acs_validation as validation
    monkeypatch.setattr(validation,'run',lambda *a:pytest.fail('must not run'))
    for args in (['--smoke-draws','21'],[]):
        monkeypatch.setattr(sys,'argv',['validation',*args])
        with pytest.raises(SystemExit):validation.main()


@pytest.mark.parametrize('model',['ols','binomial','poisson'])
def test_engine_c1_uses_replicates_state_rule_and_fixed_offsets(model):
    from tests.test_round26 import sample as geo_sample
    from census import spatial_clusters as sc
    from census.models import fit_replicate
    from census.simulation import make_replicates,replicate_long
    from census.manifest.run import _statistic
    f,coords=geo_sample();labels=sc.cluster_points(coords,8);rng=np.random.default_rng(91)
    f['state']=(labels>=4).astype(float);f['y']+=f.state*.3
    f['trials']=1000.;f['E']=np.exp(rng.normal(4,.3,len(f)))
    if model=='binomial':f['y']=rng.binomial(1000,expit(-2+.3*f.x+.2*f.state))/1000
    if model=='poisson':f['y']=rng.poisson(f.E*np.exp(.3*f.x+.2*f.state))
    values=f[['x']].to_numpy();reps=make_replicates(values,np.full_like(values,.02),rng)
    long=replicate_long(f.GEOID,['x'],values,reps);long['Year']=2019
    extra={'trials':'trials'} if model=='binomial' else {'exposure':'E'} if model=='poisson' else {}
    result=fit_replicate('y ~ x + state',f,long,model=model,coords=coords,
                         spatial_clusters={'k':8,'method':'im'},replicate_policy='strict',**extra)
    info=result.diagnostics['spatial_clusters'];assert info['not_estimable_terms']==['state']
    expected=cluster_coefficients(np.column_stack((np.ones(len(f)),f.x)),f.y.to_numpy(),labels,
                                  'linear' if model=='ols' else model,trials=f.trials,exposure=f.E)
    np.testing.assert_allclose(info['cluster_estimates'],expected,atol=1e-9)
    row=result.coefficients.set_index('term').loc['x'];z=summarize(expected)
    assert row.estimate==pytest.approx(z['estimate'][1]) and row.se_cluster_mean==pytest.approx(z['se'][1])
    assert np.isnan(result.coefficients.set_index('term').loc['state','estimate'])
    with pytest.raises(ValueError,match='not estimable'):_statistic({'statistic':'coefficient','term':'state'},result)
    assert 'as observed' in ' '.join(result.notes) and 'between-cluster spread' in ' '.join(result.notes)


@pytest.mark.parametrize('model',['ols','binomial','poisson'])
def test_c1_audit_gate_restores_unvalidated_refusal(monkeypatch,model):
    from tests.test_round26 import sample as geo_sample,manifest
    from census import spatial_clusters as sc
    from census.models import fit_replicate
    from census.manifest import validate_manifest
    monkeypatch.setitem(sc.IM_ACS_VALIDATED,model,False)
    frame,coords=geo_sample()
    with pytest.raises(ValueError,match='not validated'):
        fit_replicate('y ~ x',frame,pd.DataFrame({'variable':['x']}),model=model,coords=coords,
                      spatial_clusters={'k':8,'method':'im'})
    m=manifest();m['analyses'][0]['args']['model']=model;m['analyses'][0]['replicates']='required'
    assert any('not validated' in e for e in validate_manifest(m,resolve=False))


@pytest.mark.parametrize('extra',[{}, {'weights':'w'}, {'cluster':'group'}, {'cluster_se':'jackknife'},
                                  {'spatial_se':{'cutoff_km':100}}, {'model':'binomial'}])
def test_failed_eiv_is_refused_without_fallback(extra):
    from census.models import fit_eiv
    from tests.test_round26 import sample as geo_sample
    f,c=geo_sample()
    with pytest.raises(ValueError,match='IM EIV'):
        fit_eiv('y ~ x',f,coords=c,spatial_clusters={'k':8,'method':'im'},**extra)


def test_failed_eiv_offline_manifest_with_state_factor_is_unavailable(tmp_path):
    from tests.test_round26 import manifest
    from census.manifest import run_manifest,validate_manifest
    m=manifest();a=m['analyses'][0];a['method']='fit_eiv';a['replicates']='required'
    a['formula']='income ~ pop + C(GEOID.str[:2])'
    errors=validate_manifest(m,resolve=False)
    assert any('C2 failed validation' in e and 'im_acs_validation.md' in e for e in errors)
    out=run_manifest(m,tmp_path)
    assert not out['success'] and any('C2 failed validation' in e for e in out['errors'])


def test_audit_flags_equal_the_fixed_full_run():
    import json
    from pathlib import Path
    from census import spatial_clusters as sc
    audit=json.loads((Path(__file__).resolve().parents[1]/'docs/audits/im_acs_validation.json').read_text())
    assert sc.IM_ACS_VALIDATED=={('ols' if k=='linear' else k):v for k,v in audit['passed']['C1'].items()}
    assert sc.IM_EIV_VALIDATED==audit['passed']['C2']['linear']==False


def test_posthoc_loader_verifies_inputs_and_reference_results(tmp_path,monkeypatch):
    import json,hashlib
    from scripts import r30_posthoc_im_acs as posthoc
    from tests.test_round26 import manifest
    from census.manifest import manifest_hash
    monkeypatch.setattr(posthoc,'ROOT',tmp_path)
    m=manifest();examples=tmp_path/'examples/manifests';examples.mkdir(parents=True)
    (examples/'registered.json').write_text(json.dumps(m))
    folder=tmp_path/'cached';(folder/'bundle/results').mkdir(parents=True);(folder/'bundle/tables').mkdir()
    (folder/'analysed').mkdir();(folder/'manifest.json').write_text(json.dumps(m))
    frame=folder/'analysed/frame.csv';frame.write_text('GEOID,x\n36001,2\n')
    run={'manifest_hash':manifest_hash(m),'analysed_data':{'analysis_frame':{'path':'analysed/frame.csv','sha256':posthoc.digest(frame)}}}
    (folder/'bundle/results/run.json').write_text(json.dumps(run))
    model=folder/'bundle/results/m1.json';model.write_text('{}')
    (folder/'bundle/tables/hypotheses.csv').write_text('id,p_adjusted\nH1,.2\n')
    inventory={str(p.relative_to(folder/'bundle')):posthoc.digest(p) for p in (folder/'bundle').rglob('*') if p.is_file()}
    (folder/'bundle/bundle.json').write_text(json.dumps({'files':inventory}))
    _,_,data,_=posthoc.load_verified(folder,'registered.json');assert data['analysis_frame'].GEOID.iloc[0]=='36001'
    frame.write_text('GEOID,x\n36001,3\n')
    with pytest.raises(ValueError,match='analysed checksum'):posthoc.load_verified(folder,'registered.json')
    frame.write_text('GEOID,x\n36001,2\n');model.write_text('{"changed":true}')
    with pytest.raises(ValueError,match='result checksum'):posthoc.load_verified(folder,'registered.json')


@pytest.mark.parametrize('kind',['traversal','link'])
def test_posthoc_archive_refuses_unsafe_members(tmp_path,kind):
    import io,tarfile
    from scripts.r30_posthoc_im_acs import extract_r29
    path=tmp_path/'bad.tar.gz'
    with tarfile.open(path,'w:gz') as tar:
        member=tarfile.TarInfo('r29/mi_ny/confirmatory/../../escape.json' if kind=='traversal' else 'r29/mi_ny/confirmatory/link')
        if kind=='link':member.type=tarfile.SYMTYPE;member.linkname='/tmp/escape'
        else:member.size=2
        tar.addfile(member,io.BytesIO(b'{}') if kind=='traversal' else None)
    with pytest.raises(ValueError,match='unsafe'):extract_r29(path,tmp_path/'extracted')
    assert not (tmp_path/'extracted').exists()


def test_smoke_writes_no_audit_and_full_refuses_existing_audit(tmp_path,monkeypatch):
    import sys
    from scripts import im_acs_validation as validation
    monkeypatch.setattr(validation,'ROOT',tmp_path)
    called=[];monkeypatch.setattr(validation,'run',lambda draws:called.append(draws))
    monkeypatch.setattr(sys,'argv',['validation','--smoke-draws','2'])
    validation.main();assert called==[2] and list(tmp_path.iterdir())==[]
    (tmp_path/'docs/audits').mkdir(parents=True);(tmp_path/'docs/audits/im_acs_validation.json').write_text('{}')
    monkeypatch.setattr(validation,'validate_pins',lambda commit:None)
    monkeypatch.setattr(sys,'argv',['validation','--criterion-commit','fixed'])
    with pytest.raises(SystemExit):validation.main()
    assert called==[2]
