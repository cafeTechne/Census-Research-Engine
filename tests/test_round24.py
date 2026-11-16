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
