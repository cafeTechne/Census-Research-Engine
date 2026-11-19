# SPDX-License-Identifier: AGPL-3.0-or-later
"""WONDER disclosure controls for structured outputs, snapshots and bundles.

Only explicitly WONDER-origin columns are controlled; ACS values are unchanged.
Suppressed observations never become exact counts. Complete-case totals must be
provably sums of the displayed, unsuppressed county observations.
"""
import copy
import numpy as np
import pandas as pd

GENERIC_COLUMNS={'observed','deaths','smr','log_smr','se_log_smr','smr_lower','smr_upper','smr_exact_lower','smr_exact_upper',
                 'expected','shrinkage','p_value','p_two_sided','raw_ratio','raw_rate','eb_ratio','eb_lower','eb_upper','eb_rate','eb_rate_lower','eb_rate_upper',
                 'estimate','se','moe90','ci_lower','ci_upper'}


def suppression_info(frame,name):
    flag=frame.get(name+'_flag',pd.Series(0,index=frame.index))
    count=frame.get(name+'_numerator',frame.get(name,pd.Series(np.nan,index=frame.index)))
    num=pd.to_numeric(count,errors='coerce');supp=(flag==2)|num.between(1,9)
    ids=frame.loc[supp,'GEOID'].astype(str).tolist()
    return dict(suppressed_counties=ids,excluded_counties=len(ids),excluded_deaths_bounds=[len(ids),9*len(ids)])


def policy_from_frame(frame,manifest=None):
    names=list(frame.attrs.get('wonder_columns',()))
    if not names:return None
    columns={};info={}
    for name in names:
        info[name]=suppression_info(frame,name);ids=info[name]['suppressed_counties']
        for col in frame:
            if (col==name or col.startswith(name+'_')) and col!=name+'_flag':columns[col]=ids
    results={}
    for a in (manifest or {}).get('analyses',[]):
        outcome=str(a.get('observed',a.get('outcome',str(a.get('formula','')).split('~')[0].strip())))
        base=next((n for n in names if outcome in (n,n+'_numerator')),None)
        if base:results[a['id']]={'columns':{c:info[base]['suppressed_counties'] for c in GENERIC_COLUMNS},'count_column':'observed'}
    return dict(columns=columns,results=results,figures={},suppression=info)


def sanitize_frame(frame,scope,*,parquet=False):
    if not isinstance(frame,pd.DataFrame) or not scope:return frame
    cols=scope.get('columns',{});geo=next((c for c in ('GEOID','geoid') if c in frame),None)
    if geo is None:return frame
    out=frame.copy();ids=out[geo].astype(str)
    suppressed=set(str(g) for groups in cols.values() for g in groups)
    # A state/grand total could reveal a hidden county by subtraction. Only
    # totals whose count equals displayed complete-case counties may be written.
    dynamic=set()
    for col in ('observed','deaths'):
        if col in cols and col in out:
            dynamic.update(ids[pd.to_numeric(out[col],errors='coerce').between(1,9)])
    suppressed |= dynamic
    total=ids.str.lower().isin(('all','us','usa','national','united states','00000','0100000us'))|ids.str.fullmatch(r'[0-9]{2}(?:000)?')
    if suppressed and total.any() and any(c in out for c in cols):
        count_col=scope.get('count_column')
        if not count_col or count_col not in out:raise ValueError('WONDER complementary-suppression risk: total lacks verifiable complete-case counts')
        numbers=pd.to_numeric(out[count_col],errors='coerce')
        for i in np.flatnonzero(total.to_numpy()):
            key=ids.iloc[i];members=(~total)&(~ids.isin(suppressed))
            if str(key).lower() not in ('all','us','usa','national','united states','00000','0100000us'):members &= ids.str.startswith(key[:2])
            if not np.isfinite(numbers.iloc[i]) or numbers.loc[members].isna().any() or numbers.iloc[i]!=numbers.loc[members].sum():
                raise ValueError('WONDER complementary-suppression risk: total includes unavailable county deaths')
    for col,hidden in cols.items():
        if col not in out:continue
        mask=ids.isin(set(map(str,hidden))|dynamic)
        # Independently refuse publishing numeric 1..9 observed counts, even
        # when a malformed source omitted its suppression flag.
        if col in ('observed','deaths') or col.endswith('_numerator'):
            mask |= pd.to_numeric(out[col],errors='coerce').between(1,9)
        if mask.any():
            if parquet:out[col]=out[col].astype('string')
            else:out[col]=out[col].astype(object)
            out.loc[mask,col]='suppressed'
    return out


def sanitize_payload(value,scope):
    if isinstance(value,pd.DataFrame):return sanitize_frame(value,scope)
    if isinstance(value,dict):return {k:sanitize_payload(v,scope) for k,v in value.items()}
    if isinstance(value,list):
        if value and all(isinstance(r,dict) for r in value) and any('GEOID' in r or 'geoid' in r for r in value):
            return sanitize_frame(pd.DataFrame(value),scope).to_dict('records')
        return [sanitize_payload(v,scope) for v in value]
    if isinstance(value,tuple):return tuple(sanitize_payload(v,scope) for v in value)
    return value


def restore_snapshot(frame,names):
    """Restore only known WONDER numeric fields; suppression labels become NaN."""
    out=frame.copy()
    for name in names:
        for col in out:
            if col==name or col.startswith(name+'_'):
                out[col]=pd.to_numeric(out[col].replace('suppressed',np.nan),errors='raise').to_numpy(dtype=float,na_value=np.nan)
    out.attrs['wonder_columns']=list(names)
    return out


def audit_outputs(folder,policy):
    """Scan serialized study products, including snapshots, before archiving.

    Reports filenames/column names, never the suppressed values. No raw export
    or XML file is admissible. Reference death-count vectors are not published.
    """
    import json
    from pathlib import Path
    failures=[];checked=0
    def frame_check(frame,scope,label):
        nonlocal checked
        checked+=1
        try:safe=sanitize_frame(frame,scope)
        except ValueError:
            failures.append(label+': complementary-suppression risk');return
        for col in scope.get('columns',{}):
            if col in frame and not frame[col].astype('string').fillna('<NA>').equals(safe[col].astype('string').fillna('<NA>')):
                failures.append(label+': unsuppressed protected column '+col)
    def walk(value,scope,label):
        if isinstance(value,dict):
            if 'reference_counts' in value and value['reference_counts'] is not None:
                failures.append(label+': national reference-count vector must not accompany county output')
            if ('GEOID' in value or 'geoid' in value) and any(c in value for c in scope.get('columns',{})):
                frame_check(pd.DataFrame([value]),scope,label);return
            for key,child in value.items():walk(child,scope,label+'/'+str(key))
        elif isinstance(value,list):
            if value and all(isinstance(r,dict) for r in value) and any('GEOID' in r or 'geoid' in r for r in value):
                frame_check(pd.DataFrame(value),scope,label)
            else:
                for child in value:walk(child,scope,label)
    for path in sorted(Path(folder).rglob('*')):
        if not path.is_file():continue
        name=path.stem
        scope=policy.get('results',{}).get(name,policy.get('figures',{}).get(name,policy))
        if path.suffix.lower() in ('.tsv','.xml'):failures.append(str(path)+': raw WONDER-format file excluded')
        elif path.suffix=='.json':walk(json.loads(path.read_text()),scope,str(path))
        elif path.suffix=='.csv':
            data=pd.read_csv(path,dtype={'GEOID':str,'geoid':str})
            if 'GEOID' in data or 'geoid' in data:frame_check(data,scope,str(path))
        elif path.suffix=='.parquet':
            data=pd.read_parquet(path)
            if 'GEOID' in data:frame_check(data,scope,str(path))
    return dict(passed=not failures,structured_frames_checked=checked,failures=failures)
