#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fixed Round 28 SMR reference-rate experiment; see adjacent criterion."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from scipy.stats import norm
from census.simulation import make_replicates
CRITERION='Combined nominal 90% true-SMR coverage >= .86 in all six cells with the Poisson reference term. Zeros and invalid draws count as noncoverage; no-reference coverage informational.'


def interval(observed,pop,rates,reps,reference_counts=None,period_years=5):
    pop=np.asarray(pop,float);rates=np.asarray(rates,float);reps=np.asarray(reps,float)
    if not np.isfinite(pop).all() or (pop<0).any() or not np.isfinite(reps).all() or (reps<0).any() or (rates<=0).any():
        raise ValueError('invalid populations, replicates or reference rates')
    components=period_years*pop*rates;e=float(components.sum());er=period_years*np.einsum('br,b->r',reps,rates)
    if e<=0 or (er<=0).any():raise ValueError('nonpositive expected counts')
    sampling=.05*np.sum((np.log(er)-np.log(e))**2)
    reference=0.
    if reference_counts is not None:
        deaths=np.asarray(reference_counts,float)
        if (deaths<=0).any():raise ValueError('zero reference deaths')
        reference=float(np.sum((components/e)**2/deaths))
    if observed<=0:return np.nan,np.nan,np.nan,sampling,reference
    point=np.log(observed/e);se=np.sqrt(1/observed+sampling+reference);z=norm.ppf(.95)
    return np.exp(point-z*se),np.exp(point+z*se),se,sampling,reference


def run(draws):
    cells=[];true_rates=np.array([.0005,.001,.003,.01,.04]);period=5
    for ci,(D,E) in enumerate((d,e) for d in (50,500,5000) for e in (10,100)):
        rng=np.random.default_rng(20261130+ci)
        pop=np.repeat(E/(period*true_rates.sum()),5);reference_py=D/true_rates
        counts_with=counts_without=invalid=zeros=0
        for _ in range(draws):
            observed=int(rng.poisson(1.2*E));zeros+=int(observed==0)
            noisy_pop=pop*(1+rng.normal(0,.05,5));reps=make_replicates(noisy_pop[None,:],(.05*pop)[None,:],rng)[0]
            reference=rng.poisson(np.full(5,D));rates=reference/reference_py
            try:
                lo,hi,*_=interval(observed,noisy_pop,rates,reps,reference,period)
                counts_with+=int(np.isfinite(lo) and lo<=1.2<=hi)
                lo,hi,*_=interval(observed,noisy_pop,rates,reps,None,period)
                counts_without+=int(np.isfinite(lo) and lo<=1.2<=hi)
            except ValueError:invalid+=1
        cell=dict(cell=ci,reference_deaths_per_band=D,expected=E,band_cv=.05,period_years=period,
                  draws=draws,seed=20261130+ci,coverage_with_reference=counts_with/draws,
                  coverage_without_reference=counts_without/draws,invalid_draws=invalid,zero_observed=zeros)
        cells.append(cell);print(json.dumps(cell),flush=True)
    return dict(criterion=CRITERION,passed=all(c['coverage_with_reference']>=.86 for c in cells),cells=cells)


def main():
    p=argparse.ArgumentParser();p.add_argument('--smoke-draws',type=int);p.add_argument('--criterion-commit');a=p.parse_args()
    if a.smoke_draws is not None:
        if not 1<=a.smoke_draws<=20:p.error('smoke draws must be 1..20')
        run(a.smoke_draws);print('SMOKE ONLY, no audit written');return
    if not a.criterion_commit:p.error('full run requires --criterion-commit (commit and push first)')
    for path in ('scripts/smr_reference_validation.py','scripts/smr_reference_validation_criterion.md'):
        if subprocess.check_output(['git','show',a.criterion_commit+':'+path],cwd=ROOT)!=(ROOT/path).read_bytes():p.error('criterion/script differs from pre-run commit')
    report=run(2000);report.update(criterion_commit=a.criterion_commit,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    base=ROOT/'docs/audits/smr_reference_validation';base.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
    lines=['# Round 28 SMR reference-rate uncertainty validation','',CRITERION,'',f"Criterion commit: `{a.criterion_commit}`. Passed: **{report['passed']}**.",'',
           '| Reference deaths/band | E | With reference uncertainty | Without reference uncertainty | Invalid | O=0 |','| :-- | :-- | :-- | :-- | :-- | :-- |']
    for c in report['cells']:lines.append(f"| {c['reference_deaths_per_band']} | {c['expected']} | {c['coverage_with_reference']:.4f} | {c['coverage_without_reference']:.4f} | {c['invalid_draws']} | {c['zero_observed']} |")
    lines+=['','2,000 draws/cell; true SMR 1.2, five independent bands; fixed true rates (.0005,.001,.003,.01,.04) per person-year; five-year study period. Each band has known reference person-years D/rate; its observed reference deaths are Poisson(D). Observed rates use those deaths divided by those known person-years. The delta term uses the observed reference deaths.','', 'Gaussian ACS band errors CV .05 and 80 replicates, without clipping/redraws. Both coverage denominators include all draws. Reference denominators, spatial dependence and covariance with an internal reference were not simulated. Internal-standardization warnings are conditional because membership cannot be inferred from rates/counts alone. See the frozen criterion.']
    base.with_suffix('.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':main()
