# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fixed Round 22 Conley validation: six cells, 2,000 draws each, seed 20261122+cell."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
import statsmodels.api as sm
from census.boundaries import get_boundaries
from census.spatial_hac import conley_covariance, haversine_matrix, unit_coordinates

SIMS = 2000
CUTOFFS = (50, 100, 150, 200)
MIN_COVERAGE = .86


def simulation_setup(design, range_km, dist, seed):
    """Original Round 22 setup, extracted without changing RNG order for Round 26."""
    rng = np.random.default_rng(seed)
    n = len(dist)
    L = np.linalg.cholesky((np.eye(n) if range_km==0 else np.exp(-dist/range_km))+1e-10*np.eye(n))
    trials = np.maximum(50,np.rint(rng.lognormal(np.log(3900),1,n))) if design=='binomial' else None
    return rng, L, trials


def simulation_draw(design, L, trials, rng):
    """Original covariate/error fields and outcome draw (including binomial RNG order)."""
    n = len(L)
    x = L@rng.standard_normal(n)
    error = L@rng.standard_normal(n)
    X = np.column_stack((np.ones(n),x))
    if design=='linear':
        y = 1+.5*x+error
    else:
        p = 1/(1+np.exp(-(-2.6+.3*x+.15*error)))
        y = rng.binomial(trials.astype(int),p)/trials
    return X, y


def main():
    geoids = sorted(g for state in ('26','36') for g in get_boundaries('county',2020,state).GEOID.astype(str))
    if len(geoids) != 145:
        raise ValueError(f'expected 145 MI/NY counties, got {len(geoids)}')
    coords, provenance = unit_coordinates(geoids,'county',2020)
    provenance = json.loads(json.dumps(provenance).replace(str(Path.cwd())+'/', ''))  # no local home paths
    dist = haversine_matrix(coords.lon,coords.lat)
    n = len(dist)
    rows = []
    cells = [(design,r) for design in ('linear','binomial') for r in (0,50,100)]
    for index,(design,r) in enumerate(cells):
        rng, L, trials = simulation_setup(design, r, dist, 20261122+index)
        values = {str(c):{'se':[],'cover':0,'non_psd':0,'failed':0} for c in ('independent',)+CUTOFFS}
        estimates = []
        beta = .5 if design=='linear' else .3
        for draw in range(SIMS):
            X, y = simulation_draw(design, L, trials, rng)
            if design=='linear':
                bread = np.linalg.inv(X.T@X)
                b = bread@X.T@y
                scores = X*(y-X@b)[:,None]
                se_i = np.sqrt((bread@(scores.T@scores)@bread)[1,1])
            else:
                fit = sm.GLM(y,X,family=sm.families.Binomial(),var_weights=trials).fit(scale='X2')
                b = np.asarray(fit.params)
                mu = np.asarray(fit.fittedvalues)
                bread = np.linalg.inv(X.T@((trials*mu*(1-mu))[:,None]*X))
                scores = X*(trials*(y-mu))[:,None]
                se_i = float(fit.bse[1])
            estimates.append(b[1])
            values['independent']['se'].append(se_i)
            values['independent']['cover'] += int(abs(b[1]-beta)<=1.6448536269514722*se_i)
            for cutoff in CUTOFFS:
                v = values[str(cutoff)]
                try:
                    cov,info = conley_covariance(scores,bread,dist,cutoff)
                    se = np.sqrt(cov[1,1])
                    v['se'].append(se)
                    v['cover'] += int(abs(b[1]-beta)<=1.6448536269514722*se)
                    v['non_psd'] += int(not info['psd'])
                except ValueError:
                    v['failed'] += 1  # counted as noncoverage, never silently discard
        empirical = float(np.std(estimates,ddof=1))
        for cutoff,v in values.items():
            coverage = v['cover']/SIMS
            rows.append({'design':design,'range_km':r,'cutoff_km':cutoff,'sims':SIMS,'seed':20261122+index,
                         'coverage':coverage,'mc_se':float(np.sqrt(coverage*(1-coverage)/SIMS)),
                         'mean_se_over_empirical_sd':float(np.mean(v['se'])/empirical),
                         'non_psd_share':v['non_psd']/SIMS,'failed_covariances':v['failed']})
        print(design,r,'coverage at 150:',values['150']['cover']/SIMS,flush=True)
    passed = all(r['coverage']>=MIN_COVERAGE for r in rows if r['cutoff_km']=='150')
    result = {'passed':passed,'criterion':'coverage >= 0.86 at 150 km in all six cells',
              'coordinates':provenance,'rows':rows}
    folder = Path('docs/audits')
    (folder/'spatial_hac_validation.json').write_text(json.dumps(result,indent=2)+'\n')
    lines = ['# Spatial HAC validation (Round 22)','',
             'Fixed design: 145 Michigan/New York county representative points (2020 boundaries); '
             '2,000 simulations per cell, seed 20261122 + cell index (linear then binomial, ranges 0/50/100 km). '
             'Independent Gaussian covariate/error fields with exponential covariance and diagonal jitter 1e-10. '
             'Linear y=1+0.5x+e; binomial logit(p)=-2.6+0.3x+u, SD(u)=0.15, lognormal trials drawn once per cell '
             '(median 3900, log-SD 1, minimum 50). 90% normal Wald intervals.','',
             'The linear estimator calls the internal sandwich directly: fit_eiv requires ACS replicates even '
             'when measurement error is zero. The GLM uses the same explicitly tested binomial scores/bread '
             'as fit_replicate, fitting once per draw. Independent comparators: OLS HC0 and GLM Pearson X2. '
             'Invalid covariance fits count as noncoverage. PSD failures with positive diagonal are retained.','',
             '**Pre-set acceptance:** coverage >= 0.86 at cutoff 150 km in all six cells. '
             f'**{"PASSED" if passed else "FAILED"}**. No seeds, design or criteria changed.','',
             ('**Consequence:** recommended county cutoff 150 km; confirmatory manifests permitted.' if passed else
              '**Consequence:** spatial_se is exploratory only; confirmatory manifests refuse it. '
              'The low birth weight study must be registered without spatial SEs.'),'',
             '| Design | Range km | Cutoff km | Coverage | MC SE | Mean SE / empirical SD | Non-PSD share | Failed |',
             '| :--- | ---: | :--- | ---: | ---: | ---: | ---: | ---: |']
    for row in rows:
        lines.append('| {design} | {range_km} | {cutoff_km} | {coverage:.4f} | {mc_se:.4f} | '
                     '{mean_se_over_empirical_sd:.4f} | {non_psd_share:.4f} | {failed_covariances} |'.format(**row))
    lines += ['','Boundary provenance: `'+json.dumps(provenance,sort_keys=True)+'`.','',
              'Reproduce: `OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/spatial_hac_validation.py`.','']
    (folder/'spatial_hac_validation.md').write_text('\n'.join(lines))


if __name__=='__main__':
    main()
