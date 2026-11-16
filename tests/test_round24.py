# SPDX-License-Identifier: AGPL-3.0-or-later
"""Independent numerical and integration checks for Round 24 (offline)."""
import copy
import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from scipy.stats import chi2

from census.inequality import (ridits, slope_index, concentration_index, inequality_replicate,
                               _indices, TERMS)
from census.standardize import indirect_standardize
from census.variance import REPLICATE_COLUMNS
from census.results import IncompleteReplicatesError


def sample():
    w = np.array([1, 2, 3, 4, 5, 6.])
    x = np.array([3, 1, 2, 2, 5, 4.])
    y = np.array([.08, .05, .11, .07, .12, .09])
    return y, x, w


def test_ridits_hand_ties_and_direction():
    _, x, w = sample()
    expected = np.array([9.5, 1, 5.5, 5.5, 18.5, 13.])/21
    np.testing.assert_allclose(ridits(x, w, True), expected)
    np.testing.assert_allclose(ridits(x, w, False), 1-expected)
    np.testing.assert_allclose(ridits(np.ones(6), w, True), .5)


@pytest.mark.parametrize("bad", [None, 0, "true"])
def test_direction_is_required_boolean(bad):
    with pytest.raises(ValueError):
        ridits([1, 2], [1, 1], bad)


@pytest.mark.parametrize("weights", [[1, 0], [1, -1], [1, np.nan]])
def test_bad_weights(weights):
    with pytest.raises(ValueError):
        ridits([1, 2], weights, True)


def test_indices_and_hc3_independently():
    y, x, w = sample(); r = ridits(x, w, True)
    X = sm.add_constant(r)
    fit = sm.WLS(y, X, weights=w).fit(cov_type="HC3")
    a, b = fit.params
    g = np.array([1/(a+b)-1/a, 1/(a+b)])
    s = slope_index(y, x, w, True)
    assert s["sii"] == pytest.approx(b)
    assert s["log_rii"] == pytest.approx(np.log((a+b)/a))
    assert s["se_sii"] == pytest.approx(fit.bse[1])
    assert s["se_log_rii"] == pytest.approx(np.sqrt(g@fit.cov_params()@g))
    rm, ym = np.average(r, weights=w), np.average(y, weights=w)
    vr = np.average((r-rm)**2, weights=w)
    truth = 2*np.average((y-ym)*(r-rm), weights=w)/ym
    conv = sm.WLS(2*vr*y/ym, X, weights=w).fit(cov_type="HC3")
    c = concentration_index(y, x, w, True)
    assert c["concentration_index"] == pytest.approx(truth)
    assert c["se_concentration_index"] == pytest.approx(conv.bse[1])
    # Direct normal-equation solution is independent of the centered implementation.
    np.testing.assert_allclose(np.linalg.solve(X.T@(w[:, None]*X), X.T@(w*y)), [s['intercept'], s['sii']])
    reverse = slope_index(y, x, w, False)
    assert reverse['sii'] == pytest.approx(-s['sii'])
    assert reverse['log_rii'] == pytest.approx(-s['log_rii'])
    assert concentration_index(y,x,w,False)['concentration_index'] == pytest.approx(-truth)
    assert "reverse sign" in c['notes'][0]


def test_log_rii_nonpositive_endpoint():
    s = slope_index([-1, 0, 1, 2], [1, 2, 3, 4], [1]*4, True)
    assert np.isnan(s['log_rii'])
    assert any('undefined' in n for n in s['notes'])


def frames():
    y, x, w = sample()
    f = pd.DataFrame({'GEOID':list('abcdef'), 'y':y, 'x':x, 'w':w, 'x_se':.1*x})
    rep = pd.DataFrame(np.repeat(x[:,None],80,axis=1), columns=REPLICATE_COLUMNS)
    rep.insert(0,'variable','x'); rep.insert(0,'GEOID',f.GEOID)
    return f,rep


def test_replicate_refits_recompute_ranks_and_fixed():
    f, rep = frames()
    # Half the replicates reverse the ordering completely.
    rep.loc[:, REPLICATE_COLUMNS[:40]] = -rep[REPLICATE_COLUMNS[:40]].to_numpy()
    result = inequality_replicate(f,'y','x','w',True,rep,fixed=('y','w'))
    b = slope_index(f.y,f.x,f.w,True)['sii']
    assert result.coefficients.iloc[0].se_sampling == pytest.approx(np.sqrt(.05*40*(2*b)**2))
    assert result.diagnostics['rank_cv_median'] == pytest.approx(10)
    assert result.diagnostics['interval_target'] == 'conservative'


@pytest.mark.parametrize('kind',['missing_variable','missing_row','nonfinite','bad_weight'])
def test_strict_replicate_policy(kind):
    f,rep = frames()
    if kind=='missing_variable': rep=None
    if kind=='missing_row': rep=rep.iloc[1:]
    if kind=='nonfinite': rep.loc[0,REPLICATE_COLUMNS[3]]=np.nan
    if kind=='bad_weight':
        bad=rep.copy(); bad['variable']='w'; bad.loc[:,REPLICATE_COLUMNS]=-1.
        rep=pd.concat([rep,bad],ignore_index=True)
    with pytest.raises(IncompleteReplicatesError):
        inequality_replicate(f,'y','x','w',True,rep)


def test_rank_cv_warning_and_population_target():
    f,rep=frames(); f['x_se']=.3*f.x
    r=inequality_replicate(f,'y','x','w',True,rep,target='population')
    assert any('attenuated' in n for n in r.notes)
    assert r.to_dict()['interval_se_column']=='se_model'


def test_garwood_zero_and_pooled():
    obs=pd.Series([0,10],index=['001','002']); pop=pd.DataFrame([[100.,200.],[300.,400.]],index=obs.index)
    rates=np.array([.01,.02]); r=indirect_standardize(obs,pop,rates)
    np.testing.assert_allclose(r.expected,[5,11,16]); np.testing.assert_allclose(r.smr,[0,10/11,10/16])
    assert r.iloc[0].smr_exact_lower==0
    assert np.isnan(r.iloc[0].smr_lower) and np.isnan(r.iloc[0].p_value)
    assert r.iloc[1].smr_exact_lower==pytest.approx(chi2.ppf(.05,20)/(2*11))
    assert r.iloc[1].smr_exact_upper==pytest.approx(chi2.ppf(.95,22)/(2*11))
    assert r.iloc[0].smr_exact_upper==pytest.approx(chi2.ppf(.95,2)/(2*5))
    assert any('No band replicates' in n for n in r.iloc[1].notes)


def test_smr_replicate_variance_pools_before_refit():
    obs=pd.Series([10,20],index=['a','b']); pop=pd.DataFrame([[100.,200.],[300.,400.]],index=obs.index)
    rep=np.repeat(pop.to_numpy()[:,:,None],80,axis=2)
    rep[0,:,0:40]*=1.1; rep[1,:,0:40]*=.9
    r=indirect_standardize(obs,pop,[.01,.02],rep)
    er=np.einsum('abr,b->ar',rep,[.01,.02]).sum(axis=0)
    expected=np.sqrt(1/30+.05*np.sum((np.log(er)-np.log(16))**2))
    assert r.iloc[-1].se_log_smr==pytest.approx(expected)


@pytest.mark.parametrize('bad',['alignment','counts','rates','replicates','reserved','collision'])
def test_smr_rejects_silent_data_loss(bad):
    obs=pd.Series([1,2],index=['a','b']); pop=pd.DataFrame([[10.,20.],[30.,40.]],index=obs.index)
    rates=[.01,.02]; rep=None
    if bad=='alignment': pop=pop.iloc[::-1]
    if bad=='counts': obs.iloc[0]=-1
    if bad=='rates': rates=[0,.02]
    if bad=='replicates': rep=np.zeros((2,2,80))
    if bad=='reserved': obs.index=pop.index=['all','b']
    if bad=='collision': obs.index=pop.index=[1,'1']
    with pytest.raises(ValueError): indirect_standardize(obs,pop,rates,rep)


def manifest(method='inequality', external=False):
    from census.manifest import load_manifest
    from pathlib import Path
    m=load_manifest(Path(__file__).resolve().parents[1]/'examples/manifests/income_population_tracts.json')
    m['authors']=['human:example-researcher']
    m['exploratory']=True
    if method=='inequality':
        a=dict(id='ineq',method=method,outcome='income',rank_by='pop',weights='pop',
               args={'higher_is_more_deprived':True})
        hyps=[dict(id=t,analysis='ineq',statistic=t,direction='two-sided') for t in TERMS]
        if external:
            a.update(outcome='lbw',weights='lbw_denominator')
    else:
        a=dict(id='smr',method=method,observed='income',population_bands=['pop'],reference_rates=[.01],
               reference_source='Synthetic fixed rate per person; no rate uncertainty')
        hyps=[dict(id='h',analysis='smr',statistic='log_smr',geoid='all',direction='two-sided')]
        if external: a['observed']='lbw_numerator'
    m['analyses']=[a];m['hypotheses']=hyps
    if external:
        m['releases']=[2024]
        m['variables']=[{'name':'income','ref':'2024:B19013_001'},{'name':'pop','ref':'2024:B01003_001'}]
        m['geography']={'level':'county','states':['26','36']}
        m['external']=[{'name':'lbw','source':'chr','release':2025,'measure':'v037'}]
    return m


@pytest.mark.parametrize('method',['inequality','smr'])
def test_registered_metadata_and_valid_manifest(method):
    from census.manifest import validate_manifest, methods_section
    from census.manifest.methods import METHODS
    from census.health_sources import EXTERNAL_OUTCOME_METHODS
    m=manifest(method)
    assert validate_manifest(m,resolve=False)==[]
    assert METHODS[method].external_outcome and method in EXTERNAL_OUTCOME_METHODS
    text=methods_section(m)
    assert 'Target: conservative' in text if method=='inequality' else 'Synthetic fixed rate' in text


@pytest.mark.parametrize('method',['inequality','smr'])
def test_failed_validation_refuses_confirmatory(method,monkeypatch):
    from census.manifest import validate_manifest
    import census.inequality as iq
    import census.standardize as st
    monkeypatch.setattr(iq if method=='inequality' else st,
                        'INEQUALITY_VALIDATED' if method=='inequality' else 'SMR_VALIDATED',False)
    m=manifest(method); m.pop('exploratory')
    assert any('failed validation; exploratory only' in e for e in validate_manifest(m,resolve=False))
    m['exploratory']=True
    assert not validate_manifest(m,resolve=False)


@pytest.mark.parametrize('mutate,fragment',[
    (lambda a,h:a['args'].pop('higher_is_more_deprived'),'explicit boolean'),
    (lambda a,h:a['args'].update(higher_is_more_deprived='true'),'explicit boolean'),
    (lambda a,h:a['args'].update(target='invalid'),'target must'),
    (lambda a,h:a['args'].update(scale='robust'),'does not take'),
    (lambda a,h:a.update(outcome='missing'),'outcome'),
    (lambda a,h:a.update(rank_by='missing'),'rank_by'),
    (lambda a,h:a.update(weights='missing'),'weights'),
    (lambda a,h:h.update(term='pop'),'no term'),
])
def test_inequality_manifest_rules(mutate,fragment):
    from census.manifest import validate_manifest
    m=manifest(); mutate(m['analyses'][0],m['hypotheses'][0])
    errors=validate_manifest(m,resolve=False)
    assert any(fragment in e and ('ineq' in e or 'analyses[0]' in e) for e in errors),errors


@pytest.mark.parametrize('mutate,fragment',[
    (lambda a,h:a.update(observed='missing'),'observed'),
    (lambda a,h:a.update(population_bands=[]),'population_bands'),
    (lambda a,h:a.update(population_bands=['missing']),'population_bands'),
    (lambda a,h:a.update(population_bands=['pop','pop'],reference_rates=[.01,.02]),'repeat'),
    (lambda a,h:a.update(reference_rates=[0]),'reference_rates'),
    (lambda a,h:a.update(reference_rates=[float('nan')]),'reference_rates'),
    (lambda a,h:a.update(reference_rates=[True]),'reference_rates'),
    (lambda a,h:a.update(reference_rates=[.01,.02]),'reference_rates'),
    (lambda a,h:a.update(reference_source='  '),'reference_source'),
    (lambda a,h:a.update(args={'scale':'X2'}),'does not take'),
    (lambda a,h:a.update(args={'target':'these_areas'}),'target must'),
    (lambda a,h:h.pop('geoid'),'requires geoid'),
    (lambda a,h:h.update(geoid=['36061']),'requires geoid'),
    (lambda a,h:h.update(term='pop'),'not term'),
])
def test_smr_manifest_rules(mutate,fragment):
    from census.manifest import validate_manifest
    m=manifest('smr'); mutate(m['analyses'][0],m['hypotheses'][0])
    errors=validate_manifest(m,resolve=False)
    assert any(fragment in e and ('smr' in e or 'analyses[0]' in e) for e in errors),errors


@pytest.mark.parametrize('method',['inequality','smr'])
def test_reference_values_and_direction_are_hashed(method):
    from census.manifest import manifest_hash
    m=manifest(method); before=manifest_hash(m)
    if method=='inequality': m['analyses'][0]['args']['higher_is_more_deprived']=False
    else: m['analyses'][0]['reference_source']='Different standard'
    assert manifest_hash(m)!=before
    if method=='smr':
        m=manifest(method);m['analyses'][0]['reference_rates']=[.02]
        assert manifest_hash(m)!=before


@pytest.mark.parametrize('method',['inequality','smr'])
def test_external_roles(method):
    from census.manifest import validate_manifest
    m=manifest(method,True)
    assert not validate_manifest(m,resolve=False)
    a=m['analyses'][0]
    if method=='inequality':
        a['rank_by']='lbw';fragment='rank_by'
    else:
        a['population_bands']=['lbw'];fragment='population_bands'
    assert any(fragment in e for e in validate_manifest(m,resolve=False))


def test_external_inequality_fixed_target():
    from census.manifest import validate_manifest
    m=manifest('inequality',True);m['analyses'][0]['args']['target']='these_areas'
    assert any('omits its uncertainty' in e for e in validate_manifest(m,resolve=False))


@pytest.mark.parametrize('placement',['top','args'])
def test_circularity_rank_is_tested_term(placement):
    from census.manifest import validate_manifest
    m=manifest('inequality',True)
    m['external']=[dict(name='diabetes',source='places',release=2024,measure='DIABETES')]
    m['variables']=[dict(name='rank',ref='2024:B17001_002'),dict(name='pop',ref='2024:B01003_001')]
    a=m['analyses'][0];a.update(outcome='diabetes',rank_by='rank',weights='pop')
    if placement=='args':
        for k in ('outcome','rank_by','weights'): a['args'][k]=a.pop(k)
    errors=validate_manifest(m,resolve=False)
    assert any('CIRCULARITY R2' in e and "'rank'" in e for e in errors),errors
    for h in m['hypotheses']: h['circularity_justification']='Sensitivity check of published model input association only.'
    assert not any('CIRCULARITY R2' in e for e in validate_manifest(m,resolve=False))


@pytest.mark.parametrize('method',['inequality','smr'])
def test_circularity_r1_applies_to_nonformula_outcome(method):
    from census.manifest import validate_manifest
    m=manifest(method,True)
    m['external']=[dict(name='disability',source='places',release=2024,measure='DISABILITY')]
    m['analyses'][0]['outcome' if method=='inequality' else 'observed']='disability' if method=='inequality' else 'disability_numerator'
    if method=='inequality':m['analyses'][0]['weights']='pop'
    assert any('CIRCULARITY R1' in e for e in validate_manifest(m,resolve=False))


@pytest.mark.parametrize('method',['inequality','smr'])
def test_full_offline_manifest(method,tmp_path):
    from census.manifest import run_manifest, STATUS_EXPLORATORY
    from tests.test_manifest import FakeClient, synthetic_payload
    m=manifest(method)
    m['data_source']={'synthetic':True,'description':'Deterministic offline fixture'}
    # Replicates match the API fixture estimates and years; no real network calls.
    parts=[]
    for v,table in [('income','B19013'),('pop','B01003')]:
        rows=synthetic_payload(table)
        vals=np.array([float(row[2]) for row in rows[1:]])
        ids=['36061'+row[-1] for row in rows[1:]]
        part=pd.DataFrame(np.repeat(vals[:,None],80,axis=1),columns=REPLICATE_COLUMNS)
        part['GEOID']=ids;part['Year']=2019;part['variable']=v;parts.append(part)
    client=FakeClient();client.synthetic=True
    out=run_manifest(m,tmp_path,client=client,use_cache=False,replicates=pd.concat(parts,ignore_index=True))
    assert out['success'],out.get('deviations',out.get('errors'))
    assert out['analysis_status']==STATUS_EXPLORATORY
    assert (out['hypotheses'].status=='tested').all()
    h=out['hypotheses'].set_index('statistic')
    logstat='log_rii' if method=='inequality' else 'log_smr'
    assert h.loc[logstat,'ratio']==pytest.approx(np.exp(h.loc[logstat,'estimate']))
    assert any('ratio' in p.read_text() for p in (tmp_path/'bundle').rglob('*.csv'))


def test_external_quantities_held_fixed_in_runner():
    from census.manifest.run import _run_analysis
    f, rep=frames();f=f.rename(columns={'y':'lbw','w':'lbw_denominator'})
    external_rep=rep.copy();external_rep['variable']='lbw'
    external_rep.loc[:,REPLICATE_COLUMNS]=1.
    reps=pd.concat([rep,external_rep],ignore_index=True)
    a=dict(id='i',method='inequality',outcome='lbw',rank_by='x',weights='lbw_denominator',
           args={'higher_is_more_deprived':True})
    r=_run_analysis(a,f,.90,reps,'holm',external=['lbw'])
    np.testing.assert_allclose(r.coefficients.se_sampling,0,atol=1e-14)
    assert set(r.diagnostics['fixed_variables'])=={'lbw','lbw_denominator'}


def test_undefined_log_statistic_is_not_tested():
    from census.manifest.run import _statistic
    obs=pd.Series([0],index=['36061']);pop=pd.DataFrame([[100]],index=obs.index)
    result=indirect_standardize(obs,pop,[.01])
    with pytest.raises(ValueError,match='undefined'):
        _statistic({'statistic':'log_smr','geoid':'all'},result)


def test_zero_mean_concentration_is_nan():
    c=concentration_index([-1,0,1], [1,2,3], [1,1,1], True)
    assert np.isnan(c['concentration_index'])
    assert any('undefined' in n for n in c['notes'])


def test_replica_alignment_with_single_year_column():
    f,rep=frames();f['Year']=2024
    assert inequality_replicate(f,'y','x','w',True,rep).n_obs==6


def test_manifest_complete_case_exclusions_are_recorded():
    from census.manifest.run import _run_analysis
    f,rep=frames();f.loc[0,'y']=np.nan
    a=dict(id='i',method='inequality',outcome='y',rank_by='x',weights='w',args={'higher_is_more_deprived':True})
    r=_run_analysis(a,f,.9,rep,'holm')
    assert r.n_obs==5 and r.diagnostics['complete_case']['dropped_geoids']==['a']
    assert any('excluded 1' in n for n in r.notes)
    f['observed']=[np.nan,10,20,30,40,50]
    b=dict(id='s',method='smr',observed='observed',population_bands=['w'],reference_rates=[.1],reference_source='test')
    s=_run_analysis(b,f,.9,None,'holm')
    assert set(s.GEOID)==set('bcdef')|{'all'}
    assert any('excluded 1' in n for n in s.iloc[-1].notes)


def test_public_exports_and_recipe():
    import census
    from census.recipes import get_recipe
    for name in ('ridits','slope_index','concentration_index','inequality_replicate','indirect_standardize'):
        assert callable(getattr(census,name)) and name in census.__all__
    recipe=get_recipe('health_inequality')
    assert recipe['success'] and 'reverse sign' in recipe['steps'] and 'reference_source' in recipe['steps']
