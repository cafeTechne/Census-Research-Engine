# SPDX-License-Identifier: AGPL-3.0-or-later
"""Opt-in dominant policy after the fixed held-out re-test passed."""
import numpy as np
import pandas as pd
from census.health_sources import apportion_rates, validate_external


def test_dominant_threshold_and_unchanged_default():
    values = pd.DataFrame({'GEOID':['a','b','c'],'v':[10.,20.,30.],'v_se':[1.,2.,3.]})
    cw = pd.DataFrame({'source_geoid':['a','a','b','b','c'],
                       'target_geoid':['A','B','C','D','E'],'mass':[95.,5.,94.999,5.001,100.]})
    default,_ = apportion_rates(values,'v',cw)
    assert default.set_index('GEOID').loc[['A','B','C','D'],'v'].isna().all()
    result,info = apportion_rates(values,'v',cw,split='dominant')
    r = result.set_index('GEOID')
    assert r.loc['A','v']==10 and r.loc['A','v_se']==1
    assert r.loc[['B','C','D'],'v'].isna().all()
    assert r.loc['E','v']==30
    assert info['split_targets_left_missing']==3
    assert 'rate_apportionment_retest.md' in info['method']


def test_manifest_accepts_opt_in_only_with_apportionment():
    entry = {'name':'le','source':'usaleep','release':2018,'measure':'E0','apportion_to':2020,'split':'dominant'}
    assert validate_external([entry],{'level':'tract','state':'26'},[2022],['x'])==[]
    entry.pop('apportion_to')
    assert any('needs apportion_to' in e for e in validate_external([entry],{'level':'tract','state':'26'},[2022],['x']))
