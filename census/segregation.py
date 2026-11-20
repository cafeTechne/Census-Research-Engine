# SPDX-License-Identifier: AGPL-3.0-or-later
"""County segregation from tract counts, strict ACS replicates and fixed correction.

Declared groups must be mutually exclusive. Their sum defines tract population;
no extra total is implicitly joined. Negative replicate group counts are clipped at zero
before the index refits only under the Round 51 policy (``negative_replicates="clip"``,
the default); ``"refuse"`` keeps the strict policy. Nothing else is silently fixed.
"""
import re
from collections.abc import Mapping
import numpy as np
import pandas as pd
from scipy.stats import norm
from .results import IncompleteReplicatesError
from .variance import REPLICATE_COLUMNS

INDICES = ("dissimilarity", "isolation", "theil_h")
# Fixed criterion 4791763; audit docs/audits/segregation_validation.md.
SEGREGATION_VALIDATED = {
    "dissimilarity": {"naive": True, "bias_corrected": False},
    "isolation": {"naive": False, "bias_corrected": True},
    "theil_h": {"naive": False, "bias_corrected": True},
}
# Round 50: the default is the variant with the widest validated range; naive D failed realistic error.
DEFAULT_BIAS_CORRECTION = {"dissimilarity": True, "isolation": True, "theil_h": True}
# The accepted simulation cells had group-count CV .15 in every tract; larger
# errors (CV .30) did not pass, so results beyond this are exploratory only.
MAX_VALIDATED_COUNT_CV = .15
# Round 50 (criterion 686d121; docs/audits/segregation_realistic_validation.md): realistic ACS error
# (2024 MI/NY tract counts and published SEs, non-negative Gamma counts, correlated groups). A county's
# noise level is the largest, over groups, of the median tract CV (replicate SE / count over tracts with
# a positive total; a zero count has infinite CV). Validated noise ranges [low, high) per
# (index, variant, number of groups): the upper ends are the audit's (tests/test_round50.py). Variants
# that failed Round 28 at CV .15 (corrected D, naive isolation and H) start at .15, a conservative
# engine restriction below the first judged bin. Naive D and naive multigroup H failed.
# Round 52 (criterion b19696b; docs/audits/segregation_groups_validation.md): race/ethnicity groups
# (B03002, MI/NY), four and five groups, OH/PA, finer bins above .50. Two-group ranges combine every
# design judging a bin (Round 50 poverty, Black/non-Black and Hispanic/non-Hispanic MI/NY, OH/PA poverty
# and Black/non-Black): a bin counts only if all pass (group-type blind). Bias-corrected D and H now reach
# 1.0, bias-corrected isolation any finite level; naive isolation and H failed race groups at .15-.50 and
# lost their Round 50 range. Four- and five-group bias-corrected H pass at every finite level; three
# groups stay at Round 50 (no income county above .50). An infinite noise level (a group's median tract
# count is zero) is never validated. tests/test_round52.py checks these against the audit.
REALISTIC_AUDIT = "docs/audits/segregation_realistic_validation.md"
GROUPS_AUDIT = "docs/audits/segregation_groups_validation.md"
INF = float("inf")
REALISTIC_RANGES = {
    ("dissimilarity", "naive", 2): None,
    ("dissimilarity", "bias_corrected", 2): (.15, 1.0),
    ("isolation", "naive", 2): None,
    ("isolation", "bias_corrected", 2): (0., INF),
    ("theil_h", "naive", 2): None,
    ("theil_h", "bias_corrected", 2): (0., 1.0),
    ("theil_h", "naive", 3): None,
    ("theil_h", "bias_corrected", 3): (0., .50),
    ("theil_h", "naive", 4): None,
    ("theil_h", "bias_corrected", 4): (0., INF),
    ("theil_h", "naive", 5): None,
    ("theil_h", "bias_corrected", 5): (0., INF),
    # Round 57 (criterion 8bcad0b; docs/audits/segregation_gaps_validation.md): six groups (B03002 split into
    # White, Black, Asian, Hispanic, multiracial and other), bias-corrected H at every finite level.
    ("theil_h", "naive", 6): None,
    ("theil_h", "bias_corrected", 6): (0., INF),
}
MAX_VALIDATED_MEDIAN_CV = INF   # upper end over all validated ranges (finite noise levels only)
# Round 52: contrasts between two non-overlapping releases (independent samples, variances added) passed
# for every two-group variant when the larger of the two noise levels is below .50 (MI/NY poverty 2015-2019
# vs 2020-2024). Both rows must also be validated. Multigroup cross-release contrasts were not tested.
CONTRAST_RANGES = {(name, variant): (0., .50) for name in INDICES for variant in ("naive", "bias_corrected")}
# Round 51 (criterion 2837bfb; docs/audits/negative_replicates_validation.md): Gaussian replicates with
# negative counts clipped at zero before the refits. Bias-corrected D/isolation/H and three-group H kept
# their Round 50 ranges (affected-draw coverage .902-.990); naive isolation and H failed the affected-draw
# check (.847-.860), naive D and naive three-group H had no range. A county with a clipped replicate cell
# is validated only inside these ranges (tests/test_round51.py checks them against the audit).
NEGATIVE_REPLICATE_AUDIT = "docs/audits/negative_replicates_validation.md"
NEGATIVE_REPLICATE_POLICIES = ("clip", "refuse")
DEFAULT_NEGATIVE_REPLICATES = "clip"
# Round 57 (criterion 8bcad0b; docs/audits/segregation_gaps_validation.md): clipped replicates on the Round 52
# race designs extended the ranges above .50: isolation to .75 and H to 1.0 (two groups), H at every finite level
# with four and five groups; corrected D stays at .50 (failed above it with clipped cells).
GAPS_AUDIT = "docs/audits/segregation_gaps_validation.md"
CLIP_RANGES = {
    ("dissimilarity", "naive", 2): None,
    ("dissimilarity", "bias_corrected", 2): (.15, .50),
    ("isolation", "naive", 2): None,
    ("isolation", "bias_corrected", 2): (0., .75),
    ("theil_h", "naive", 2): None,
    ("theil_h", "bias_corrected", 2): (0., 1.0),
    ("theil_h", "naive", 3): None,
    ("theil_h", "bias_corrected", 3): (0., .50),
    ("theil_h", "naive", 4): None,
    ("theil_h", "bias_corrected", 4): (0., INF),
    ("theil_h", "naive", 5): None,
    ("theil_h", "bias_corrected", 5): (0., INF),
    # Round 62 (criterion 8f14e39; docs/audits/leftover_failures_validation.md): clipped six-group H.
    ("theil_h", "naive", 6): None,
    ("theil_h", "bias_corrected", 6): (0., INF),
}
# Round 57: contrasts between two counties of the same release (per-replicate differences) passed for every
# two-group variant except corrected D (.855) when the larger noise level is below .50. Both rows must also be
# validated.
SAME_RELEASE_CONTRAST_RANGES = {(name, variant): (0., .50) for name in INDICES for variant in ("naive", "bias_corrected")}
SAME_RELEASE_CONTRAST_RANGES[("dissimilarity", "bias_corrected")] = None


def group_quarters_tracts(frame, gq, total, max_share=.5):
    """Tract GEOIDs whose group-quarters share gq / total (e.g. B26001_001 / B01003_001) is >= max_share.

    A definitional choice for residential segregation (prisons, dormitories, nursing homes), reported with the
    result; it has no coverage claim of its own. Tracts with a zero total are not listed."""
    if not 0 < float(max_share) <= 1:
        raise ValueError("max_share must be in (0, 1]")
    g = pd.to_numeric(frame[gq], errors="coerce").to_numpy(float)
    t = pd.to_numeric(frame[total], errors="coerce").to_numpy(float)
    if not (np.isfinite(g) & np.isfinite(t)).all() or (g < 0).any() or (t < 0).any():
        raise ValueError("group-quarters and total population must be finite nonnegative counts")
    share = np.divide(g, t, out=np.zeros_like(g), where=t > 0)
    return sorted(set(frame.loc[share >= max_share, "GEOID"].astype(str)))
MIN_VALIDATED_TRACTS = 5        # the validation excluded counties with fewer populated tracts


def variant_validated(name, variant, n_groups):
    """True when the index variant passed Round 28 (two groups, max CV .15) or Round 50 in some range."""
    r28 = bool(SEGREGATION_VALIDATED[name][variant]) and n_groups == 2
    return r28 or REALISTIC_RANGES.get((name, variant, n_groups)) is not None


def noise_level(counts, count_se):
    """Largest over groups of the median tract CV (tracts with a positive total; zero count -> inf)."""
    c = np.asarray(counts, float); s = np.asarray(count_se, float)
    populated = c.sum(axis=1) > 0
    if not populated.any():
        return float("inf")
    cv = np.where(c > 0, s/np.where(c > 0, c, 1.), np.inf)[populated]
    return float(np.max(np.median(cv, axis=0)))

def _indices(counts):
    """Batch x tracts x groups; zero tracts excluded, absent groups undefined."""
    x=np.asarray(counts,float)
    if x.ndim!=3 or x.shape[2]<2 or not np.isfinite(x).all() or (x<0).any():
        raise ValueError('counts must be finite nonnegative (batch,tracts,groups>=2)')
    totals=x.sum(axis=2);groups=x.sum(axis=1);N=groups.sum(axis=1)
    shares=np.divide(x,totals[:,:,None],out=np.zeros_like(x),where=totals[:,:,None]>0)
    area_shares=np.divide(groups,N[:,None],out=np.zeros_like(groups),where=N[:,None]>0)
    with np.errstate(divide='ignore',invalid='ignore'):
        entropy=-np.where(area_shares>0,area_shares*np.log(area_shares),0).sum(axis=1)
        tract_entropy=-np.where(shares>0,shares*np.log(shares),0).sum(axis=2)
    H=np.divide((totals*(entropy[:,None]-tract_entropy)).sum(axis=1),N*entropy,
                out=np.full(len(x),np.nan),where=N*entropy>0)
    out=np.full((len(x),3),np.nan);out[:,2]=H
    if x.shape[2]==2:
        proportions=np.divide(x,groups[:,None,:],out=np.zeros_like(x),where=groups[:,None,:]>0)
        out[:,0]=.5*np.abs(proportions[:,:,0]-proportions[:,:,1]).sum(axis=1)
        out[:,1]=(proportions[:,:,0]*shares[:,:,0]).sum(axis=1)
    out[(groups<=0).any(axis=1)]=np.nan
    return out


def segregation_indices(counts):
    """Point indices and notes for a tract-by-group array (natural-log entropy)."""
    x=np.asarray(counts,float)
    if x.ndim!=2:raise ValueError('counts must be a tract-by-group matrix')
    values=_indices(x[None])[0];notes=[]
    zero=int(np.sum(x.sum(axis=1)==0))
    if zero:notes.append(f'{zero} zero-total tract(s) excluded from this index calculation.')
    if (x.sum(axis=0)==0).any():notes.append('A declared group has zero area total; indices are undefined.')
    if x.shape[1]!=2:notes.append('Dissimilarity and isolation require exactly two groups; only H is defined.')
    return dict(zip(INDICES,map(float,values)),notes=notes)


def segregation_replicate(frame, groups, replicates, within='county', level=.90, bias_correction=None,
                          negative_replicates=None, exclude_tracts=None):
    """County/year indices with all 80 raw replicate indices retained.

    Tract GEOIDs must be eleven-digit strings. Missing/full or invalid replicate
    counts raise; zero tracts contribute zero and may re-enter in a replicate.
    Missing groups return undefined indices with notes. CIs are normal and
    unbounded, not clipped to [0,1]. Each index defaults to its passing variant.
    A row is validated when its variant passed and the county is in a validated
    range: Round 28 (two groups, every tract group-count CV <= .15,
    ``max_count_cv``) or Rounds 50/52 (``noise_level``, the largest group median tract
    CV, inside ``REALISTIC_RANGES``: bias-corrected D [.15, 1), isolation any finite
    level, H below 1 (two groups), .50 (three) or any finite level (four or five);
    at least five populated tracts). Otherwise it is exploratory only, and confirmatory manifest
    hypotheses on it are refused. Naive isolation/H and H with six or more groups are exploratory.
    ``negative_replicates`` (default ``"clip"``, Round 51): negative replicate group counts are set to
    zero before the index refits; count SEs and the noise level use the unclipped replicates. A county
    with a clipped cell is validated only inside ``CLIP_RANGES`` (bias-corrected variants).
    ``"refuse"`` raises on any negative replicate (the strict pre-Round 51 policy).
    ``exclude_tracts`` (Round 57): tract GEOIDs left out of every index and refit (e.g. group-quarters tracts
    from ``group_quarters_tracts``); a definitional choice noted per county.
    """
    from .models import _replicate_matrices
    from .results import precheck_replicates
    if within!='county':raise ValueError('within must be county; CBSA/metro aggregation is unsupported')
    if not isinstance(groups,(list,tuple)) or len(groups)<2 or not all(isinstance(g,str) for g in groups) or len(set(groups))!=len(groups):
        raise ValueError('groups must contain at least two distinct count-column names')
    if not np.isfinite(level) or not 0<level<1:raise ValueError('level must be between zero and one')
    if bias_correction is not None and type(bias_correction) is not bool:raise ValueError('bias_correction must be boolean or None')
    data=frame.copy().reset_index(drop=True)
    if not len(data) or 'GEOID' not in data or not data.GEOID.map(lambda x:isinstance(x,str) and bool(re.fullmatch(r'[0-9]{11}',x))).all():
        raise ValueError('tract GEOIDs must be nonmissing eleven-digit strings')
    if not all(g in data for g in groups):raise ValueError('every declared group must be in the frame')
    excluded_by_county={}
    if exclude_tracts is not None:
        excl=set(map(str,exclude_tracts))
        drop=data.GEOID.isin(excl)
        for g in data.GEOID[drop]:excluded_by_county[g[:5]]=excluded_by_county.get(g[:5],0)+1
        data=data.loc[~drop].reset_index(drop=True)
        if not len(data):raise ValueError('every tract was excluded')
    if 'Year' in data:
        years=pd.to_numeric(data.Year,errors='coerce').to_numpy(float)
        if not np.isfinite(years).all() or np.any(years!=np.floor(years)) or np.any(years<2009):raise ValueError('Year must contain ACS five-year release integers')
        data['Year']=years.astype(int)
    else:data['Year']=0
    years=sorted(data.Year.unique())
    if any(b-a<5 for a,b in zip(years,years[1:])):raise ValueError('overlapping five-year releases are refused')
    if data.duplicated(['GEOID','Year']).any():raise ValueError('duplicate tract/release keys')
    counts=data[list(groups)].to_numpy(float)
    if not np.isfinite(counts).all() or (counts<0).any():raise ValueError('group counts must be finite and nonnegative; no complete-case dropping or clipping')
    if isinstance(replicates,Mapping):
        parts=[]
        for year,rep in replicates.items():
            part=rep.copy()
            if 'Year' in part and not (pd.to_numeric(part.Year,errors='coerce')==int(year)).all():
                raise IncompleteReplicatesError('replicate mapping key disagrees with Year')
            part['Year']=int(year);parts.append(part)
        replicates=pd.concat(parts,ignore_index=True) if parts else None
    if not isinstance(replicates,pd.DataFrame) or not len(replicates):
        raise IncompleteReplicatesError('segregation requires all 80 replicates for every declared group and tract')
    rep=replicates.copy()
    if exclude_tracts is not None and 'GEOID' in rep:rep=rep[~rep.GEOID.astype(str).isin(set(map(str,exclude_tracts)))]
    if not {'GEOID','variable',*REPLICATE_COLUMNS}<=set(rep):raise IncompleteReplicatesError('segregation requires GEOID/variable and all 80 replicate columns')
    if 'Year' not in rep:
        if len(years)>1:raise IncompleteReplicatesError('each release requires its own Year-labelled replicates')
        rep['Year']=years[0]
    else:
        ry=pd.to_numeric(rep.Year,errors='coerce').to_numpy(float)
        if not np.isfinite(ry).all() or np.any(ry!=np.floor(ry)):raise IncompleteReplicatesError('invalid replicate Year')
        rep['Year']=ry.astype(int)
    if rep.duplicated(['GEOID','Year','variable']).any():raise IncompleteReplicatesError('duplicate tract/release/group replicate keys')
    mats,held=_replicate_matrices(data,rep,groups)
    precheck_replicates('strict',rows_held_fixed=held,variables_without_replicates=[g for g in groups if g not in mats],context='segregation')
    cube=np.stack([mats[g] for g in groups],axis=2) # tracts,80,groups
    policy=DEFAULT_NEGATIVE_REPLICATES if negative_replicates is None else negative_replicates
    if policy not in NEGATIVE_REPLICATE_POLICIES:raise ValueError("negative_replicates must be 'clip' or 'refuse'")
    if not np.isfinite(cube).all():raise IncompleteReplicatesError('invalid group-count replicate; no redrawing')
    if policy=='refuse' and (cube<0).any():raise IncompleteReplicatesError('negative group-count replicate; strict policy (negative_replicates="refuse"), no clipping/redrawing')
    negative=cube<0;refit=np.maximum(cube,0.)
    data['_county']=data.GEOID.str[:5];rows=[];z=norm.ppf((1+level)/2)
    for (county,year),part in data.groupby(['_county','Year'],sort=True):
        loc=part.index.to_numpy();raw=_indices(counts[loc][None])[0]
        rr=_indices(refit[loc].transpose(1,0,2));clipped=int(negative[loc].sum())
        defined=np.isfinite(raw)
        if not np.isfinite(rr[:,defined]).all():raise IncompleteReplicatesError('a defined full-sample index has undefined replicate refits')
        zero=int(np.sum(counts[loc].sum(axis=1)==0));se=np.sqrt(.05*np.sum((rr-raw)**2,axis=0));bc=raw-4*(rr.mean(axis=0)-raw)
        count_se=np.sqrt(.05*np.sum((cube[loc]-counts[loc,None,:])**2,axis=1))
        cv=np.divide(count_se,counts[loc],out=np.zeros_like(count_se),where=counts[loc]>0)
        cv[(counts[loc]==0)&(count_se>0)]=np.inf
        max_cv=float(np.max(cv)) if cv.size else 0.;in_range=max_cv<=MAX_VALIDATED_COUNT_CV+1e-12
        noise=noise_level(counts[loc],count_se)
        for k,name in enumerate(INDICES):
            if len(groups)>2 and name!='theil_h':continue
            corrected=DEFAULT_BIAS_CORRECTION[name] if bias_correction is None else bias_correction
            variant='bias_corrected' if corrected else 'naive'
            variant_ok=bool(variant_validated(name,variant,len(groups)) and level==.90)
            r28=bool(SEGREGATION_VALIDATED[name][variant]) and len(groups)==2 and in_range
            span=REALISTIC_RANGES.get((name,variant,len(groups)))
            if clipped:
                span=CLIP_RANGES.get((name,variant,len(groups)));r28=False
            populated=int(np.sum(counts[loc].sum(axis=1)>0))
            r50=span is not None and span[0]<=noise<span[1] and populated>=MIN_VALIDATED_TRACTS
            validated=variant_ok and (r28 or r50)
            point=bc[k] if corrected else raw[k];notes=[]
            if clipped:notes.append(f'{clipped} negative replicate group count(s) set to zero before the index refits (Round 51 policy; validated for bias-corrected variants only).')
            if excluded_by_county.get(county):notes.append(f'{excluded_by_county[county]} tract(s) excluded by exclude_tracts (e.g. group quarters); the index describes the remaining tracts.')
            if zero:notes.append(f'{zero} zero-total tract(s) excluded in full-sample index; totals recomputed in every refit.')
            if not np.isfinite(raw[k]):notes.append('A declared group has zero county total; index and inference undefined.')
            if not variant_ok:notes.append('EXPLORATORY ONLY: index/variant/group count/level lacks passing coverage validation (Rounds 28, 50 and 52).')
            elif not validated:
                rng_text=f'[{span[0]:.2f}, {span[1]:.2f})' if span is not None else 'none'
                where=(f'{populated} populated tract(s), fewer than the {MIN_VALIDATED_TRACTS} the Round 50 validation required'
                       if span is not None and span[0]<=noise<span[1] else
                       f'noise level {noise:.2f} (largest group median tract CV) is outside the Rounds 50/52 validated range {rng_text} for this variant')
                if clipped and span is None:notes.append('EXPLORATORY ONLY: this variant failed the Round 51 clipped-replicate validation; confirmatory tests refused.')
                else:notes.append(f'EXPLORATORY ONLY: {where}'+('' if clipped else f', and the largest tract group-count CV {max_cv:.2f} exceeds the Round 28 .15')+'; confirmatory tests refused.')
            notes.append('Declared groups must be mutually exclusive; totals are their sum. ACS sampling uncertainty only, not superpopulation or spatial uncertainty.')
            row=dict(GEOID=county,Year=int(year),statistic=name,estimate=float(point),naive_estimate=float(raw[k]),bias_corrected_estimate=float(bc[k]),
                     se=float(se[k]),ci_lower=float(point-z*se[k]),ci_upper=float(point+z*se[k]),bias_correction=corrected,
                     validated=validated,max_count_cv=max_cv,noise_level=noise,clipped_replicates=clipped,confidence_level=level,tracts=int(len(loc)),zero_total_tracts=zero,groups=list(groups),notes=notes)
            row.update(zip(REPLICATE_COLUMNS,map(float,rr[:,k])));rows.append(row)
    result=pd.DataFrame(rows);result.attrs.update(uncertainty='ACS 4/80 raw replicate deviations; correction uses same SE', confidence_level=level)
    return result


def segregation_test(result, statistic, geoid, null_value=None, compare_geoid=None, release=None, compare_release=None):
    """One-area or contrast Wald result; independent-release variances add."""
    def select(county,year):
        sub=result[(result.GEOID==county)&(result.statistic==statistic)]
        if year is not None:sub=sub[sub.Year==year]
        if len(sub)!=1:raise ValueError('county/statistic/release must select exactly one result; specify release for multiple years')
        return sub.iloc[0]
    first=select(geoid,release);other=None
    if compare_geoid is not None or compare_release is not None:
        other=select(compare_geoid or geoid,compare_release if compare_release is not None else int(first.Year))
        if first.GEOID==other.GEOID and first.Year==other.Year:raise ValueError('cannot compare an area/release with itself')
        if first.bias_correction!=other.bias_correction:raise ValueError('contrast variants must match')
    elif null_value is None:raise ValueError('one-area tests require a pre-registered null_value')
    if null_value is not None and (isinstance(null_value,(bool,np.bool_)) or not isinstance(null_value,(int,float,np.integer,np.floating))):raise ValueError('null_value must be numeric, not boolean')
    null=0. if null_value is None else float(null_value)
    if not np.isfinite(null):raise ValueError('null_value must be finite')
    estimate=float(first.estimate);se=float(first.se)
    if other is not None:
        estimate-=float(other.estimate)
        if first.Year!=other.Year:
            if abs(first.Year-other.Year)<5:raise ValueError('overlapping five-year releases refused')
            se=float(np.hypot(first.se,other.se))
            variant='bias_corrected' if bool(first.bias_correction) else 'naive'
            span=CONTRAST_RANGES.get((statistic,variant))
            groups=first.get('groups');noise=max(float(first.get('noise_level',np.inf)),float(other.get('noise_level',np.inf)))
            contrast_ok=(span is not None and isinstance(groups,(list,tuple)) and len(groups)==2
                         and span[0]<=noise<span[1])
        else:
            delta=(first[list(REPLICATE_COLUMNS)].to_numpy(float)-other[list(REPLICATE_COLUMNS)].to_numpy(float))-(first.naive_estimate-other.naive_estimate)
            se=float(np.sqrt(.05*np.sum(delta**2)))
            variant='bias_corrected' if bool(first.bias_correction) else 'naive'
            span=SAME_RELEASE_CONTRAST_RANGES.get((statistic,variant))
            groups=first.get('groups');noise=max(float(first.get('noise_level',np.inf)),float(other.get('noise_level',np.inf)))
            same_ok=(span is not None and isinstance(groups,(list,tuple)) and len(groups)==2
                     and span[0]<=noise<span[1])
    if not np.isfinite(estimate) or not np.isfinite(se) or se<=0:raise ValueError('index or nonzero sampling uncertainty undefined; Wald test not available')
    z=norm.ppf((1+float(first.get('confidence_level',result.attrs.get('confidence_level',.90))))/2)
    validated=bool(first.validated) and (other is None or bool(other.validated))
    cross=other is not None and first.Year!=other.Year
    same=other is not None and not cross
    if cross:validated=validated and contrast_ok
    if same:validated=validated and same_ok
    refusal=None if validated else ('segregation result not validated (failed variant, group count, level, county outside '
                                    'the validated noise range' + (', or a cross-release contrast with more than two groups '
                                    'or a larger noise level of .50 or more (Round 52)' if cross else '')
                                    + (', or a same-release county contrast with more than two groups, corrected D, or a '
                                       'larger noise level of .50 or more (Round 57)' if same else '')
                                    + '); exploratory only, confirmatory test refused')
    return dict(estimate=estimate,test_estimate=estimate-null,validated=validated,confirmatory_refusal=refusal,null_value=null,se=se,se_basis='se_sampling',
                p_two_sided=float(2*norm.sf(abs((estimate-null)/se))),ci_lower=estimate-z*se,ci_upper=estimate+z*se,
                geoid=geoid,release=int(first.Year),compare_geoid=other.GEOID if other is not None else None,
                compare_release=int(other.Year) if other is not None else None)
