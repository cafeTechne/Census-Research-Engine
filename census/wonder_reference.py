# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pinned WONDER age/sex references and matching ACS B01001 bands; offline only."""
import re
import numpy as np

BANDS=('0-4','5-14','15-24','25-34','35-44','45-54','55-64','65-74','75-84','85+')
MALE_CELLS=((3,),(4,5),(6,7,8,9,10),(11,12),(13,14),(15,16),(17,18,19),(20,21,22),(23,24),(25,))


def band_order(ages_under=None):
    if ages_under not in (None,75):raise ValueError('ages_under supports only the preregistered under-75 standard')
    selected=BANDS if ages_under is None else BANDS[:8]
    return [(sex,band) for sex in ('M','F') for band in selected]


def band_name(sex,band,prefix='age'):
    return f'{prefix}_{sex.lower()}_{band.replace("-","_").replace("+","_plus")}'


def acs_age_sex_bands(release=2022,prefix='age'):
    """Return a manifest template (46 B01001 cells, 20 disjoint sum derivations).

    Fixed order: male bands youngest to oldest, then female. No age/sex count
    cell is omitted or counted twice. The study's reference bands use this order.
    """
    if type(release) is not int or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',prefix):raise ValueError('invalid release or template prefix')
    variables=[];derivations=[]
    for sex,offset in (('M',0),('F',24)):
        for band,cells in zip(BANDS,MALE_CELLS):
            names=[]
            for cell in cells:
                code=f'B01001_{cell+offset:03}'
                name=f'{prefix}_cell_{cell+offset:03}';names.append(name)
                variables.append(dict(name=name,ref=f'{release}:{code}'))
            derivations.append(dict(name=band_name(sex,band,prefix),op='sum',num=names))
    return dict(variables=variables,derivations=derivations,
                population_bands=[band_name(s,b,prefix) for s,b in band_order()])


def validate_band_order(names,ages_under=None):
    expected=band_order(ages_under);actual=[]
    for name in names:
        match=re.search(r'_(m|f)_(\d+_\d+|85_plus)$',str(name))
        if not match:raise ValueError('reference_export populations must use the acs_age_sex_bands template names/order')
        actual.append((match[1].upper(),match[2].replace('_plus','+').replace('_','-')))
    if actual!=expected:raise ValueError('population band order differs from the fixed ACS age/sex template')


def resolve_reference_export(spec,period_years,names,*,validate_only=False):
    from .health_sources import resolve_external_file
    from .vital_records import read_wonder_reference
    if not isinstance(spec,dict) or set(spec)-{'file','sha256','ages_under','state'} or not isinstance(spec.get('file'),str) or not re.fullmatch(r'[0-9a-fA-F]{64}',str(spec.get('sha256',''))):
        raise ValueError('reference_export requires file and SHA-256, with optional ages_under=75 or state')
    validate_band_order(names,spec.get('ages_under'))
    result=read_wonder_reference(resolve_external_file(spec['file']),expected_sha256=spec['sha256'],state=spec.get('state'),validate_only=validate_only)
    years=result['years']
    if type(period_years) is not int or period_years<=0 or period_years!=len(years):
        raise ValueError('period_years must equal the number of reference footer years')
    rows=result['rows'].set_index(['sex','band']).loc[band_order(spec.get('ages_under'))]
    return rows.rate.to_numpy(float),rows.deaths.to_numpy(float),result


def expected_count_weights(entry,*,validate_only=False):
    names=entry.get('population_bands')
    if not isinstance(names,list) or not names or not all(isinstance(n,str) for n in names) or len(set(names))!=len(names):raise ValueError('expected_count needs distinct population_bands')
    period=entry.get('period_years',1)
    rates,_,info=resolve_reference_export(entry.get('reference_export'),period,names,validate_only=validate_only)
    if not np.isfinite(rates).all() or (rates<0).any():raise ValueError('reference rates unavailable for expected counts')
    return period*rates,info
