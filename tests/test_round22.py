# SPDX-License-Identifier: AGPL-3.0-or-later
"""Offline Round 22 identities and registered-analysis controls."""
import json
from unittest import mock

import numpy as np
import pandas as pd
import pytest

from census.manifest import create_manifest, run_manifest, validate_manifest
from census.models import fit_eiv, fit_replicate
from census.spatial_hac import conley_covariance, conley_meat, haversine_matrix
from tests.test_round20 import FakeClient, _manifest


class TestExploratoryFlag:
    def test_flag_validation_and_hash(self):
        m = _manifest()
        m['exploratory'] = 'yes'
        assert 'exploratory must be true or false' in validate_manifest(m, resolve=False)
        m['exploratory'] = True
        out = create_manifest(m)
        assert out['valid'] and 'registered as exploratory' in out['notes']

    def test_blocking_deviation_keeps_exploratory_tags(self, tmp_path):
        m = create_manifest(_manifest())['manifest']
        m['exploratory'] = True
        result = run_manifest(m, tmp_path, client=FakeClient(), use_cache=False)
        assert result['analysis_status'] == 'exploratory'
        assert result['deviations']
        run = json.loads((tmp_path/'bundle/results/run.json').read_text())
        assert run['analysis_status'] == 'exploratory'
        assert 'This analysis was registered as exploratory' in (tmp_path/'bundle/methods.md').read_text()

    def test_successful_exploratory_run_tags_every_analysis(self,tmp_path):
        from tests.test_round20 import _replicates
        m = create_manifest(_manifest(exploratory=True))["manifest"]
        probe = run_manifest(m,tmp_path/'probe',client=FakeClient(),use_cache=False)
        reps = _replicates(probe['frame'],['d0','n0','d1','n1','pov_tot','pov_n'])
        result = run_manifest(m,tmp_path/'run',client=FakeClient(),use_cache=False,replicates=reps)
        assert result['success'] and result['analysis_status']=='exploratory'
        assert all(r.provenance['analysis_status']=='exploratory' for r in result['results'].values())
        saved = json.loads((tmp_path/'run/bundle/results/m1.json').read_text())
        assert saved['provenance']['analysis_status']=='exploratory'
        assert set(result['hypotheses']['analysis_status'])=={'exploratory'}


class TestConley:
    def test_known_distances(self):
        assert haversine_matrix([0, 0], [0, 1])[0, 1] == pytest.approx(111.195, abs=.01)
        assert haversine_matrix([-83.0458, -74.006], [42.3314, 40.7128])[0, 1] == pytest.approx(775, abs=5)

    def test_independence_and_cluster_identity(self):
        rng = np.random.default_rng(42)
        scores = rng.normal(size=(80, 3))
        groups = np.repeat(np.arange(20), 4)
        dist = np.abs(groups[:, None] - groups) * 100.
        sums = np.array([scores[groups == g].sum(axis=0) for g in range(20)])
        np.testing.assert_allclose(conley_meat(scores, dist, 1), sums.T@sums, atol=1e-10)
        apart = haversine_matrix(np.linspace(-90, -70, 80), np.repeat(40.,80))
        np.testing.assert_allclose(conley_meat(scores, apart, .01), scores.T@scores, atol=1e-12)

    def test_errors(self):
        for c in (0, -1, np.nan, np.inf):
            with pytest.raises(ValueError):
                conley_meat(np.ones((3,1)), np.zeros((3,3)), c)
        with pytest.raises(ValueError, match='not positive'):
            conley_covariance(np.zeros((3,1)), np.ones((1,1)), np.zeros((3,3)), 1)
        d = pd.DataFrame({'GEOID':['01','02','03'], 'x':[1,2,3], 'y':[.1,.3,.4], 't':[100]*3})
        with pytest.raises(ValueError, match='binomial and poisson'):
            fit_replicate('y ~ x',d,spatial_se={'cutoff_km':1})
        with pytest.raises(ValueError, match='mutually exclusive'):
            fit_eiv('y ~ x',d,cluster='GEOID',spatial_se={'cutoff_km':1})

    def test_eiv_and_binomial_cluster_limits(self):
        rng = np.random.default_rng(721)
        n = 100
        groups = np.repeat(np.arange(25),4)
        x = rng.normal(size=n)
        y = 1 + .5*x + rng.normal(size=n)
        df = pd.DataFrame({'GEOID':[f'{i:05}' for i in range(n)],'group':groups,'x':x,'y':y,'t':np.repeat(500,n)})
        coords = df[['GEOID']].assign(lon=-100+groups,lat=40.)
        # Exactly error-free synthetic replicates reduce EIV to the OLS sandwich.
        from census.variance import REPLICATE_COLUMNS
        reps = pd.concat([pd.DataFrame({'GEOID':df.GEOID,'variable':v, **{c:df[v] for c in REPLICATE_COLUMNS}})
                          for v in ('x','y')],ignore_index=True)
        cr = fit_eiv('y ~ x',df,reps,cluster='group')
        co = fit_eiv('y ~ x',df,reps,spatial_se={'cutoff_km':1},coords=coords)
        # Same cluster meat, distinct prescribed small-sample factors.
        ratio = (n/(n-2))/((25/24)*((n-1)/(n-2)))
        np.testing.assert_allclose(co.coefficients.se_total**2, cr.coefficients.se_total**2*ratio,rtol=1e-10)
        df['y'] = rng.binomial(500, 1/(1+np.exp(2-.4*x)))/500
        res = fit_replicate('y ~ x',df,model='binomial',trials='t',spatial_se={'cutoff_km':1},coords=coords)
        import statsmodels.api as sm
        X = sm.add_constant(x)
        full = sm.GLM(df.y,X,family=sm.families.Binomial(),var_weights=df.t).fit()
        mu = np.asarray(full.fittedvalues)
        score = X*(500*(df.y.to_numpy()-mu))[:,None]
        sums = np.array([score[groups==g].sum(axis=0) for g in range(25)])
        bread = np.linalg.inv(X.T@((500*mu*(1-mu))[:,None]*X))
        expected = bread@(sums.T@sums)@bread*n/(n-2)
        np.testing.assert_allclose(res.coefficients.se_model**2,np.diag(expected),rtol=1e-9)

    def test_manifest_spatial_rules(self):
        for spec in ({'cutoff_km':0},{'cutoff_km':150,'kernel':'x'},'150'):
            m = _manifest(exploratory=True)
            m['analyses'][0]['args']={'spatial_se':spec}
            assert any('exactly cutoff_km' in e for e in validate_manifest(m,resolve=False))


def count_manifest(model='binomial'):
    m = _manifest(geography={'level':'county','state':'26'})
    m['external'] = [{'name':'lbw','source':'chr','release':2025,'measure':'v037'}]
    m['analyses'] = [{'id':'m1','method':'fit_replicate','formula':'lbw ~ pov_rate',
                      'args':{'model':model,'scale':'X2','trials':'lbw_denominator'}}]
    m['hypotheses'][0]['term']='pov_rate'
    if model=='poisson':
        m['analyses'][0].update(formula='lbw_numerator ~ pov_rate',
                               args={'model':'poisson','scale':'X2','exposure':'lbw_denominator'})
    return m


class TestCountOutcomes:
    def test_dispersion_scale_and_replicate_invariance(self):
        rng = np.random.default_rng(184)
        n = 90
        x = rng.normal(size=n)
        t = rng.integers(1000,5000,n)
        p = 1/(1+np.exp(2-.2*x-.5*rng.normal(size=n)))
        d = pd.DataFrame({'GEOID':[str(i) for i in range(n)],'x':x,'y':rng.binomial(t,p)/t,'t':t})
        from census.variance import REPLICATE_COLUMNS
        reps = pd.DataFrame({'GEOID':d.GEOID,'variable':'x',**{c:x+rng.normal(0,.01,n) for c in REPLICATE_COLUMNS}})
        a = fit_replicate('y ~ x',d,reps,model='binomial',trials='t')
        b = fit_replicate('y ~ x',d,reps,model='binomial',trials='t',scale='X2')
        np.testing.assert_allclose(a.coefficients.estimate,b.coefficients.estimate,atol=1e-9)
        np.testing.assert_allclose(b.coefficients.se_model/a.coefficients.se_model,
                                   np.sqrt(b.diagnostics['pearson_dispersion']),rtol=1e-7)
        np.testing.assert_allclose(a.coefficients.se_sampling,b.coefficients.se_sampling,rtol=1e-5)
        assert any('model SEs assume no overdispersion' in n for n in a.notes)
        assert not any('model SEs assume no overdispersion' in n for n in b.notes)
        with pytest.raises(ValueError):
            fit_replicate('y ~ x',d,scale='X2')

    def test_count_roles_and_refusals(self):
        for model in ('binomial','poisson'):
            m = count_manifest(model)
            assert validate_manifest(m,resolve=False)==[]
            m['analyses'][0]['args'].pop('scale')
            assert any('overdispersion would be ignored' in e for e in validate_manifest(m,resolve=False))
            m = count_manifest(model)
            role = 'trials' if model=='binomial' else 'exposure'
            m['analyses'][0]['args'][role]='pov_rate'
            assert any('denominator' in e for e in validate_manifest(m,resolve=False))
        for model in ('wls','negbin'):
            m = count_manifest()
            m['analyses'][0]['args']={'model':model}
            assert any('not validated for external outcomes' in e for e in validate_manifest(m,resolve=False))
        for bad in ('lbw_denominator ~ pov_rate','pov_rate ~ lbw_numerator','lbw ~ lbw_denominator'):
            m = count_manifest()
            m['analyses'][0]['formula']=bad
            assert any('not a manifest variable' in e for e in validate_manifest(m,resolve=False))

    def test_registry_parser_and_circularity(self):
        from census import health_sources as hs
        from census.manifest import circularity_errors
        from tests.test_round21_part2 import _chr_csv
        assert hs.measure_kind('chr','v037')=='direct'
        assert '2017–2023' in hs.source_text('chr','v037')
        data = hs.parse_chr(_chr_csv([('26001',.0705,1)],code='v037'),{'v037':'lbw'})
        assert data.lbw.iloc[0]==.0705
        assert data.lbw_numerator.iloc[0]==100
        assert data.lbw_denominator.iloc[0]==30000
        assert circularity_errors(count_manifest())==[]
        m = count_manifest()
        m['external'][0]['measure']='v060'
        assert any('CIRCULARITY R2' in e for e in circularity_errors(m))
        m = count_manifest('poisson')
        m['external'][0]['measure']='v060'
        assert any('CIRCULARITY R2' in e for e in circularity_errors(m))

    def test_offline_external_binomial_manifest(self,tmp_path):
        from tests.test_round20 import _replicates
        from census import health_sources as hs

        class CountyClient(FakeClient):
            def fetch(self,*args,**kwargs):
                raw = super().fetch(*args,**kwargs)
                header = raw[0]
                ci, ti, gi = header.index('county'),header.index('tract'),header.index('GEO_ID')
                rows=[]
                for i,row in enumerate(raw[1:]):
                    row=list(row)
                    row[ci]=f'{2*i+1:03}'
                    row[gi]='0500000US26'+row[ci]
                    rows.append([v for j,v in enumerate(row) if j!=ti])
                return [[v for j,v in enumerate(header) if j!=ti]]+rows

        m = count_manifest()
        rng = np.random.default_rng(420)
        def external(entries,level,states,**kwargs):
            n = len(CountyClient().fetch(2024,'B18101'))-1
            t = np.repeat(3000.,n)
            numerator = rng.integers(150,350,n).astype(float)
            numerator[0]=15
            ext = pd.DataFrame({'GEOID':[f'26{2*i+1:03}' for i in range(n)],'lbw':numerator/t,
                                'lbw_se':.003,'lbw_numerator':numerator,'lbw_denominator':t,'lbw_flag':0})
            return ext,[]
        with mock.patch.object(hs,'load_external',side_effect=external):
            probe=run_manifest(m,tmp_path/'probe',client=CountyClient(),use_cache=False)
            reps=_replicates(probe['frame'],['d0','n0','d1','n1','pov_tot','pov_n'])
            out=run_manifest(m,tmp_path/'run',client=CountyClient(),use_cache=False,replicates=reps)
        assert out['success'],out.get('deviations')
        assert 'odds_ratio' in out['hypotheses']
        assert 'quasi-binomial regression' in (tmp_path/'run/bundle/methods.md').read_text()
        assert '1 counties had fewer than 20' in (tmp_path/'run/bundle/methods.md').read_text()
        from census.manifest import run_variant
        coords = out['frame'][['GEOID']].assign(lon=np.linspace(-95,-75,len(out['frame'])),lat=40.)
        with mock.patch('census.spatial_hac.unit_coordinates',return_value=(coords,{'boundary_year':2024,'files':[]})) as lookup:
            variant = run_variant(tmp_path/'run','m1',args={'spatial_se':{'cutoff_km':1}},out_dir=tmp_path/'variants')
        assert lookup.call_count==1
        assert variant['analysis_status']=='exploratory'
        assert variant['result']['diagnostics']['spatial_se']['cutoff_km']==1


class TestCoordinates:
    def test_boundary_hashes_alignment_and_missing(self):
        import geopandas as gpd
        from shapely.geometry import Point
        from census.spatial_hac import unit_coordinates
        boundary = gpd.GeoDataFrame({'GEOID':['01001','02001']},geometry=[Point(-80,40),Point(-90,45)],crs='EPSG:4269')
        boundary.attrs.update(sha256='a'*64,cache_path='cached.zip',source_url='https://example.invalid/boundary.zip')
        with mock.patch('census.boundaries.get_boundaries',return_value=boundary) as fetch:
            coords, info = unit_coordinates(['02001','01001'],'county',2020)
            assert list(coords.GEOID)==['02001','01001']
            assert list(coords.lon)==[-90,-80]
            assert fetch.call_count==2
            assert info['files'][0]['sha256']=='a'*64
            with pytest.raises(ValueError,match='01003'):
                unit_coordinates(['01003'],'county',2020)
        with pytest.raises(ValueError):
            unit_coordinates(['01'],'state',2020)
