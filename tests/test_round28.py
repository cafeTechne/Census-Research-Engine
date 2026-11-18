# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 28 independent definitions, covariance contracts and offline bundles."""
import copy
import importlib.util
import json
from pathlib import Path
from unittest import mock
import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm
from census import segregation as sg
from census.standardize import indirect_standardize
from census.manifest import validate_manifest,manifest_hash,run_manifest,methods_section
from census.simulation import make_replicates,replicate_long
from census.variance import REPLICATE_COLUMNS


def reference(name):
    path=Path(__file__).resolve().parents[1]/f'scripts/{name}.py'
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m


def test_four_tract_indices_independent_hand_reference():
    counts=np.array([[30.,10.],[10.,30.],[20.,20.],[40.,0.]])
    area_entropy=-(100/160*np.log(100/160)+60/160*np.log(60/160))
    local_entropy=[-(.75*np.log(.75)+.25*np.log(.25)),-(.25*np.log(.25)+.75*np.log(.75)),np.log(2),0.]
    H=1-np.dot([40,40,40,40],local_entropy)/(160*area_entropy)
    out=sg.segregation_indices(counts)
    assert out['dissimilarity']==pytest.approx(8/15)
    assert out['isolation']==pytest.approx(.75)
    assert out['theil_h']==pytest.approx(H)
    assert sg.segregation_indices([[10,20],[20,40],[30,60],[40,80]])['theil_h']==pytest.approx(0,abs=1e-15)
    assert sg.segregation_indices([[10,0],[20,0],[0,30],[0,40]])['dissimilarity']==1.


def test_zero_tract_and_absent_group_notes_and_multigroup_entropy():
    x=np.array([[20,10,10],[10,20,10],[10,10,20],[0,0,0]],float)
    out=sg.segregation_indices(x)
    E=np.log(3);Et=-(.5*np.log(.5)+2*.25*np.log(.25))
    assert out['theil_h']==pytest.approx((E-Et)/E)
    assert np.isnan(out['dissimilarity']) and any('zero-total' in n for n in out['notes'])
    absent=sg.segregation_indices([[1,0],[2,0]])
    assert all(np.isnan(absent[k]) for k in sg.INDICES) and any('zero area total' in n for n in absent['notes'])


def sample(two=False,years=(2019,)):
    counts=np.array([[30.,10.],[10.,30.],[20.,20.],[35.,5.]])
    f=[];parts=[];rng=np.random.default_rng(282)
    for year in years:
        for j,county in enumerate(['36061','36063'] if two else ['36061']):
            x=counts.copy();x[:,0]+=j*np.array([1,3,2,1])+((year-years[0])/5)*np.array([1,0,0,1])
            ids=[county+f'{i:06}' for i in range(1,5)]
            f.append(pd.DataFrame({'GEOID':ids,'Year':year,'a':x[:,0],'b':x[:,1]}))
            reps=make_replicates(x,.05*x,rng)
            rep=replicate_long(ids,['a','b'],x,reps);rep['Year']=year;parts.append(rep)
    return pd.concat(f,ignore_index=True),pd.concat(parts,ignore_index=True)


def test_replicate_se_and_correction_with_fixed_array_and_frozen_kernel():
    f,r=sample();result=sg.segregation_replicate(f,['a','b'],r,bias_correction=True)
    x=f[['a','b']].to_numpy();batches=[]
    for col in REPLICATE_COLUMNS:
        a=r[r.variable=='a'][col].to_numpy();b=r[r.variable=='b'][col].to_numpy();batches.append(np.column_stack((a,b)))
    raw=.5*np.abs(x[:,0]/sum(x[:,0])-x[:,1]/sum(x[:,1])).sum()
    reps=np.array([.5*np.abs(v[:,0]/sum(v[:,0])-v[:,1]/sum(v[:,1])).sum() for v in batches])
    row=result[result.statistic=='dissimilarity'].iloc[0]
    assert row.se==pytest.approx(np.sqrt(.05*sum((reps-raw)**2)))
    assert row.estimate==pytest.approx(raw-4*(np.mean(reps)-raw))
    ref=reference('segregation_validation');np.testing.assert_array_equal(sg._indices(np.stack(batches)),ref.indices(np.stack(batches)))
    assert not row.validated # Corrected D failed; default must remain naive.
    default=sg.segregation_replicate(f,['a','b'],r).set_index('statistic')
    assert not default.loc['dissimilarity','bias_correction'] and default.loc['isolation','bias_correction'] and default.loc['theil_h','bias_correction']


@pytest.mark.parametrize('bad',['missing_column','missing_row','missing_group','duplicate','negative','missing_year','none'])
def test_strict_replicate_policy_refuses_incomplete(bad):
    f,r=sample(years=(2014,2019) if bad=='missing_year' else (2019,))
    if bad=='missing_column':r=r.drop(columns='rep_80')
    elif bad=='missing_row':r=r.iloc[1:]
    elif bad=='missing_group':r=r[r.variable=='a']
    elif bad=='duplicate':r=pd.concat([r,r.iloc[[0]]])
    elif bad=='negative':r.loc[0,'rep_1']=-1.
    elif bad=='missing_year':r=r.drop(columns='Year')
    elif bad=='none':r=None
    from census.results import IncompleteReplicatesError
    with pytest.raises(IncompleteReplicatesError):sg.segregation_replicate(f,['a','b'],r)


@pytest.mark.parametrize('bad',['negative','missing','bad_geoid','duplicate','groups','within'])
def test_invalid_full_inputs(bad):
    f,r=sample();groups=['a','b'];within='county'
    if bad=='negative':f.loc[0,'a']=-1
    elif bad=='missing':f.loc[0,'a']=np.nan
    elif bad=='bad_geoid':f.loc[0,'GEOID']='36061'
    elif bad=='duplicate':f=pd.concat([f,f.iloc[[0]]])
    elif bad=='groups':groups=[['a'],'b']
    elif bad=='within':within='cbsa'
    with pytest.raises(ValueError):sg.segregation_replicate(f,groups,r,within=within)


def test_cross_county_contrast_uses_shared_replication_covariance():
    f,r=sample(two=True)
    # Deliberately share a tract-specific error pattern across both counties.
    a=r[(r.GEOID.str.startswith('36061'))&(r.variable=='a')].copy()
    ix=r.index[(r.GEOID.str.startswith('36063'))&(r.variable=='a')]
    original=f[f.GEOID.str.startswith('36063')].a.to_numpy()[:,None]
    delta=a[list(REPLICATE_COLUMNS)].to_numpy()-f[f.GEOID.str.startswith('36061')].a.to_numpy()[:,None]
    r.loc[ix,list(REPLICATE_COLUMNS)]=original+delta
    out=sg.segregation_replicate(f,['a','b'],r);a=out[(out.GEOID=='36061')&(out.statistic=='dissimilarity')].iloc[0];b=out[(out.GEOID=='36063')&(out.statistic=='dissimilarity')].iloc[0]
    test=sg.segregation_test(out,'dissimilarity','36061',compare_geoid='36063')
    dr=(a[list(REPLICATE_COLUMNS)].to_numpy(float)-b[list(REPLICATE_COLUMNS)].to_numpy(float))-(a.naive_estimate-b.naive_estimate)
    assert test['se']==pytest.approx(np.sqrt(.05*np.sum(dr**2)))
    assert not np.isclose(test['se'],np.hypot(a.se,b.se))
    assert test['estimate']==pytest.approx(a.estimate-b.estimate)


def test_independent_release_variances_add_and_replicate_mapping_agrees():
    f,r=sample(years=(2014,2019));out=sg.segregation_replicate(f,['a','b'],r)
    mapped=sg.segregation_replicate(f,['a','b'],{year:part for year,part in r.groupby('Year')})
    pd.testing.assert_frame_equal(out,mapped)
    h=sg.segregation_test(out,'theil_h','36061',release=2014,compare_release=2019)
    selected=out[out.statistic=='theil_h'];assert h['se']==pytest.approx(np.sqrt(np.sum(selected.se**2)))
    with pytest.raises(ValueError,match='specify release'):sg.segregation_test(out,'theil_h','36061',null_value=.1)
    f.loc[f.Year==2014,'Year']=2015
    with pytest.raises(ValueError,match='overlapping'):sg.segregation_replicate(f,['a','b'],r)


def segregation_manifest(stat='dissimilarity'):
    from tests.test_round24 import manifest
    m=manifest();m.pop('exploratory');m['analyses']=[dict(id='seg',method='segregation',groups=['income','pop'],within='county',replicates='required')]
    m['hypotheses']=[dict(id='H',analysis='seg',statistic=stat,geoid='36061',null_value=.2,direction='two-sided')]
    return m


@pytest.mark.parametrize('case',['groups','two_groups','within','county_input','null','term','geoid','compare_self','overlap','missing_release','wrong_release','multigroup_confirmatory'])
def test_manifest_rules(case):
    m=segregation_manifest();a=m['analyses'][0];h=m['hypotheses'][0]
    if case=='groups':a['groups']=['pop','pop']
    elif case=='two_groups':a['groups']=['pop','income','extra']
    elif case=='within':a['within']='cbsa'
    elif case=='county_input':m['geography']['level']='county'
    elif case=='null':h.pop('null_value')
    elif case=='term':h['term']='pop'
    elif case=='geoid':h['geoid']='36061000100'
    elif case=='compare_self':h['compare_geoid']='36061'
    elif case=='overlap':m['releases']=[2018,2019]
    elif case=='missing_release':m['releases']=[2014,2019]
    elif case=='wrong_release':h['release']=2024
    elif case=='multigroup_confirmatory':
        m['variables'].append({'name':'extra','ref':'2019:B01003_001'});a['groups']=['pop','income','extra'];h['statistic']='theil_h'
    assert validate_manifest(m,resolve=False)


def test_per_index_variant_gate_patches_imported_flag(monkeypatch):
    m=segregation_manifest();assert validate_manifest(m,resolve=False)==[]
    monkeypatch.setitem(sg.SEGREGATION_VALIDATED['dissimilarity'],'naive',False)
    assert any('exploratory only' in e for e in validate_manifest(m,resolve=False))
    m['exploratory']=True;assert not any('exploratory only' in e for e in validate_manifest(m,resolve=False))
    m=segregation_manifest();m['analyses'][0]['args']={'bias_correction':True}
    assert any('dissimilarity/bias_corrected' in e for e in validate_manifest(m,resolve=False))
    m=segregation_manifest('isolation');m['analyses'][0]['args']={'bias_correction':False}
    assert any('isolation/naive' in e for e in validate_manifest(m,resolve=False))


def populations():
    ids=pd.Index(['36061','36063']);o=pd.Series([12.,21.],index=ids)
    pop=pd.DataFrame([[100.,200.],[300.,100.]],index=ids,columns=['young','old'])
    return o,pop


def test_period_arithmetic_and_reference_variance_hand_pooled_covariance():
    o,pop=populations();rates=np.array([.01,.02]);counts=[50,100]
    out=indirect_standardize(o,pop,rates,period_years=5,reference_counts=counts)
    components=5*pop.to_numpy()*rates
    for i in (0,1):
        e=components[i].sum();variance=sum((components[i]/e)**2/np.array(counts))
        assert out.iloc[i].expected==pytest.approx(e)
        assert out.iloc[i].variance_log_reference==pytest.approx(variance)
        assert out.iloc[i].se_log_smr==pytest.approx(np.sqrt(1/o.iloc[i]+variance))
    pooled=components.sum(axis=0);expected=pooled.sum();variance=sum((pooled/expected)**2/np.array(counts))
    assert out.iloc[2].expected==pytest.approx(expected) and out.iloc[2].variance_log_reference==pytest.approx(variance)
    incorrect=sum((out.expected.iloc[:2]/expected)**2*out.variance_log_reference.iloc[:2])
    assert not np.isclose(variance,incorrect)
    assert any('internal standardization' in n and 'conservative' in n for n in out.iloc[0].notes)


@pytest.mark.parametrize('period',[0,-1,1.5,True])
def test_period_refuses_invalid(period):
    o,pop=populations()
    with pytest.raises(ValueError,match='period_years'):indirect_standardize(o,pop,[.01,.02],period_years=period)


@pytest.mark.parametrize('counts',[[0,50],[-1,50],[1.5,50],[True,50],[10],[np.inf,50]])
def test_reference_counts_refuse_invalid(counts):
    o,pop=populations()
    with pytest.raises(ValueError,match='reference_counts'):indirect_standardize(o,pop,[.01,.02],reference_counts=counts)


def test_reference_frozen_kernel_numerical_parity_and_fixed_exact_limits():
    ref=reference('smr_reference_validation');o,pop=populations();rates=np.array([.01,.02]);rng=np.random.default_rng(29)
    reps=make_replicates(pop.to_numpy(),.05*pop.to_numpy(),rng)
    result=indirect_standardize(o,pop,rates,reps,period_years=5,reference_counts=[50,100])
    lo,hi,se,_,vref=ref.interval(o.iloc[0],pop.iloc[0].to_numpy(),rates,reps[0],[50,100],5)
    row=result.iloc[0];np.testing.assert_allclose([row.smr_lower,row.smr_upper,row.se_log_smr,row.variance_log_reference],[lo,hi,se,vref],rtol=1e-12)
    fixed=indirect_standardize(o,pop,rates,reps,period_years=5)
    np.testing.assert_array_equal(result.smr_exact_lower,fixed.smr_exact_lower)
    np.testing.assert_array_equal(result.smr_exact_upper,fixed.smr_exact_upper)
    assert (result.smr_upper>fixed.smr_upper).all()


def smr_manifest():
    from tests.test_round24 import manifest
    m=manifest('smr');m.pop('exploratory');a=m['analyses'][0];a.update(period_years=5,reference_counts=[500]);return m


def test_new_smr_inputs_hashed_and_normalized_and_gated(monkeypatch):
    import census.standardize as standardize
    m=smr_manifest();assert validate_manifest(m,resolve=False)==[]
    before=manifest_hash(m)
    for key,new in [('period_years',4),('reference_counts',[501])]:
        changed=copy.deepcopy(m);changed['analyses'][0][key]=new;assert manifest_hash(changed)!=before
    nested=copy.deepcopy(m);a=nested['analyses'][0];a['args']={key:a.pop(key) for key in ('period_years','reference_counts')}
    assert validate_manifest(nested,resolve=False)==[]
    monkeypatch.setattr(standardize,'SMR_REFERENCE_VALIDATED',False)
    assert any('reference-rate uncertainty' in e for e in validate_manifest(m,resolve=False))
    m['analyses'][0].pop('reference_counts');assert validate_manifest(m,resolve=False)==[]
    nested['exploratory']=True;assert validate_manifest(nested,resolve=False)==[]


def test_offline_smr_reference_bundle(tmp_path):
    from tests.test_manifest import FakeClient
    client=FakeClient();client.synthetic=True;m=smr_manifest();m['data_source']={'synthetic':True,'description':'Offline Round 28 SMR reference example'}
    from census.manifest.run import _prepare,_extract,_build_frame
    state=_prepare(m,tmp_path/'source',client,None,False,None,None);_extract(state);_build_frame(state)
    f=state.frame;x=f[['pop']].to_numpy();rep=make_replicates(x,.03*x,np.random.default_rng(2829))
    r=replicate_long(f.GEOID,['pop'],x,rep);r['Year']=f.Year.iloc[0]
    out=run_manifest(m,tmp_path/'run',client=client,replicates=r,replicates_synthetic=True,use_cache=False)
    assert out['success'],dict(errors=out.get('errors'),deviations=out.get('deviations'),output_error=out.get('output_error'))
    assert out['hypotheses'].iloc[0].status=='tested'
    assert 'variance_log_reference' in out['results']['smr']['rows']
    text=(tmp_path/'run/bundle/methods.md').read_text();assert 'per person-year' in text and 'D_b' in text
    assert 'are not included' not in text


def test_offline_segregation_bundle_and_one_sided_nonzero_null(tmp_path,monkeypatch):
    import tests.test_manifest as fixtures
    client=fixtures.FakeClient();client.synthetic=True;m=segregation_manifest();m['data_source']={'synthetic':True,'description':'Offline Round 28 segregation example'}
    # Construct the same deterministic extraction to supply complete group replicas.
    # Follow the engine's own canonical frame: an exploratory extraction supplies
    # numeric groups but the completed registered run still consumes explicit reps.
    from census.manifest.run import _prepare,_extract,_build_frame
    state=_prepare(m,tmp_path/'source',client,None,False,None,None);_extract(state);_build_frame(state)
    f=state.frame;x=f[['income','pop']].to_numpy();rng=np.random.default_rng(228)
    reps=make_replicates(x,.03*x,rng);r=replicate_long(f.GEOID,['income','pop'],x,reps);r['Year']=f.Year.iloc[0]
    m['hypotheses'][0].update(direction='less',null_value=.9)
    out=run_manifest(m,tmp_path/'run',client=client,replicates=r,replicates_synthetic=True,use_cache=False)
    assert out['success'],dict(errors=out.get('errors'),deviations=out.get('deviations'),output_error=out.get('output_error'))
    h=out['hypotheses'].iloc[0];assert h.status=='tested' and h.estimate<.9
    expected=norm.cdf((h.estimate-.9)/h.se)
    assert h.p_value==pytest.approx(expected) # Sign uses estimate-null, not index itself.
    text=(tmp_path/'run/bundle/methods.md').read_text();assert 'Duncan' in text and 'mean(I_r)' in text


def test_zero_full_tract_can_enter_a_replicate_and_absent_group_undefined():
    f,r=sample();zero=f.GEOID.iloc[0]
    f.loc[0,['a','b']]=0.
    r.loc[r.GEOID==zero,list(REPLICATE_COLUMNS)]=1.
    out=sg.segregation_replicate(f,['a','b'],r)
    row=out[out.statistic=='theil_h'].iloc[0]
    assert row.zero_total_tracts==1 and row.se>0
    assert any('recomputed' in n for n in row.notes)
    f,r=sample();f['b']=0.;r.loc[r.variable=='b',list(REPLICATE_COLUMNS)]=0.
    out=sg.segregation_replicate(f,['a','b'],r)
    assert out.estimate.isna().all() and any('undefined' in n for n in out.iloc[0].notes)
    with pytest.raises(ValueError,match='undefined'):sg.segregation_test(out,'dissimilarity','36061',null_value=.2)


def test_multigroup_h_exploratory_and_nondefault_level_persists():
    f,r=sample();f['c']=f.a+f.b
    extra=r[r.variable=='a'].copy();extra['variable']='c';extra[list(REPLICATE_COLUMNS)]+=r[r.variable=='b'][list(REPLICATE_COLUMNS)].to_numpy()
    r=pd.concat([r,extra],ignore_index=True)
    out=sg.segregation_replicate(f,['a','b','c'],r,level=.95)
    assert out.statistic.tolist()==['theil_h'] and not out.validated.any()
    out.attrs={}
    h=sg.segregation_test(out,'theil_h','36061',null_value=.2)
    assert h['ci_upper']-h['estimate']==pytest.approx(norm.ppf(.975)*h['se'])


def test_corrected_variant_manifest_and_optional_null_defaults_are_consistent():
    m=segregation_manifest('isolation');m['analyses'][0]['args']={'bias_correction':None}
    assert validate_manifest(m,resolve=False)==[]
    m['analyses'][0]['args']['bias_correction']=False
    assert any('exploratory' in e for e in validate_manifest(m,resolve=False))
    m['exploratory']=True;assert validate_manifest(m,resolve=False)==[]


def test_independent_reference_variance_is_retained_when_study_areas_duplicated():
    o,pop=populations();one=indirect_standardize(o.iloc[:1],pop.iloc[:1],[.01,.02],reference_counts=[50,100]).iloc[0]
    ids=pd.Index(['36061','36063']);p=pd.DataFrame(np.repeat(pop.iloc[:1].to_numpy(),2,axis=0),index=ids)
    counts=pd.Series([12,12],index=ids)
    pooled=indirect_standardize(counts,p,[.01,.02],reference_counts=[50,100]).iloc[-1]
    assert pooled.variance_log_reference==pytest.approx(one.variance_log_reference)
    assert pooled.se_log_smr**2==pytest.approx(1/24+one.variance_log_reference)


def test_zero_observed_retains_only_fixed_expected_exact_interval():
    o,pop=populations();o.iloc[0]=0
    row=indirect_standardize(o,pop,[.01,.02],period_years=5,reference_counts=[50,100]).iloc[0]
    assert np.isnan(row.se_log_smr) and np.isnan(row.p_value) and np.isnan(row.smr_lower)
    assert row.smr_exact_lower==0 and np.isfinite(row.smr_exact_upper)


@pytest.mark.parametrize('groups',[None,'pop',{'group':'pop'},[{'name':'pop'},'income']])
def test_malformed_manifest_groups_return_errors_not_exceptions(groups):
    m=segregation_manifest();m['analyses'][0]['groups']=groups
    assert any('groups' in e for e in validate_manifest(m,resolve=False))


def test_optional_smr_inputs_execute_identically_in_top_level_or_args():
    from census.manifest.run import _run_analysis
    f,_=sample();f=f.rename(columns={'a':'pop','b':'income'});m=smr_manifest();a=m['analyses'][0]
    nested=copy.deepcopy(a);nested['args']={key:nested.pop(key) for key in ('period_years','reference_counts')}
    first=_run_analysis(a,f,.9,None,'holm');second=_run_analysis(nested,f,.9,None,'holm')
    pd.testing.assert_frame_equal(first,second)
    nested['period_years']=4;m['analyses'][0]=nested
    assert any("'period_years' given both" in e for e in validate_manifest(m,resolve=False))
