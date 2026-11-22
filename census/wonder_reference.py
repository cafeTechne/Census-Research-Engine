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


def acs_band_populations(b01001, prefix='age'):
    """ACS B01001 rows (columns B01001_xxxE, index GEOID) -> the 20 age/sex band columns in ``band_order()``."""
    import pandas as pd
    out = {}
    for sex, offset in (('M', 0), ('F', 24)):
        for band, cells in zip(BANDS, MALE_CELLS):
            out[band_name(sex, band, prefix)] = sum(pd.to_numeric(b01001[f'B01001_{c+offset:03}E']) for c in cells)
    return pd.DataFrame(out, index=b01001.index)


def expected_counts(band_populations, reference_path, *, expected_sha256=None, person_years=None, period_years=None):
    """Expected counts from a national WONDER age x sex reference file (Round 73, backlog N51).

    ``band_populations``: the 20 ACS age/sex band columns in ``band_order()`` (``acs_band_populations``).
    The reference rates are per person-year (``read_wonder_reference``: under-one and 1-4 pooled before division,
    Not Stated excluded). Either
    - ``period_years``: expected = period x sum_b rate_b x population_b (the manifest ``expected_count`` rule), or
    - ``person_years``: the ACS gives only the age x sex mix; expected = person_years x sum_b rate_b x share_b, where
      ``person_years`` is e.g. the county's WONDER population summed over the study years (Round 69).
    No suppressed or hidden count is read or produced.
    """
    import pandas as pd
    from .vital_records import read_wonder_reference
    validate_band_order(list(band_populations.columns))
    if (person_years is None) == (period_years is None):
        raise ValueError('give exactly one of person_years or period_years')
    ref = read_wonder_reference(reference_path, expected_sha256=expected_sha256)
    rates = ref['rows'].set_index(['sex', 'band']).loc[band_order()].rate.to_numpy(float)
    pops = band_populations.to_numpy(float)
    base = pops @ rates
    if period_years is not None:
        return pd.Series(base*float(period_years), index=band_populations.index, name='expected')
    py = pd.Series(person_years).reindex(band_populations.index).to_numpy(float)
    return pd.Series(base/pops.sum(axis=1)*py, index=band_populations.index, name='expected')
