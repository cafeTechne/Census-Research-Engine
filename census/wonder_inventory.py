# SPDX-License-Identifier: AGPL-3.0-or-later
"""Structural WONDER inventory: no joins, covariates, correlations or models."""
import csv
import hashlib
import io
from pathlib import Path
import re
from .vital_records import _split_footer,parse_footer,read_wonder_export,WonderExportError
from .wonder_api import CAUSES,validate_response,response_rows

UNDER75=('< 1 year','1-4 years','5-14 years','15-24 years','25-34 years','35-44 years','45-54 years','55-64 years','65-74 years')


def years_from_parameters(parameters):
    return sorted(set(map(int,re.findall(r'\b(?:19|20)\d{2}\b',parameters.get('Year/Month',parameters.get('Year',''))))))


def cause_codes(parameters):
    text='; '.join(str(v) for k,v in parameters.items() if any(x in k for x in ('Cause List','ICD-10 Codes','Drug/Alcohol')))
    text=text.upper().replace('–','-').replace('—','-')
    return set(re.findall(r'\b[A-Z][0-9]{2}(?:\.[0-9]+)?(?:\s*-\s*[A-Z][0-9]{2}(?:\.[0-9]+)?)?',text))


def inspect_file(path,root,*,minimum_counties=3100):
    path=Path(path);rel=path.relative_to(root);parts=rel.parts;flags=[]
    if len(parts)!=4 or parts[0]!='ucd':raise WonderExportError('expected ucd/<years>/<group>/<cause> file layout')
    window,kind=parts[1:3];m=re.fullmatch(r'(\d{4})-(\d{4})',window)
    if not m:raise WonderExportError('folder years must be YYYY-YYYY')
    expected_years=list(range(int(m[1]),int(m[2])+1));cause=re.sub(r'_v[0-9]+$','',path.stem)
    raw=path.read_bytes();sha=hashlib.sha256(raw).hexdigest()
    if path.suffix.lower()=='.xml':
        if kind!='national_age_sex':flags.append('API file outside national_age_sex')
        request=path.with_suffix('.request.xml')
        if not request.exists():raise WonderExportError('API file lacks its request XML')
        info=validate_response(raw,request.read_bytes());rows=response_rows(raw)
        years=info['years'];database=info['database'];group='Ten-Year Age Groups; Sex';codes=set(info['cause_codes'])-{'*All*'}
        count=len(rows);supp=sum(r['deaths']=='Suppressed' for r in rows);zero=sum(r['deaths'].replace(',','')=='0' for r in rows)
        if cause!=info['cause']:flags.append('filename cause differs from echoed request')
        columns=['Age','Sex','Deaths','Population']
    else:
        text=raw.decode('utf-8-sig');body,footer=_split_footer(text);meta=parse_footer(footer);params=meta['parameters']
        database=meta['dataset'];years=years_from_parameters(params);group=params.get('Group By','');codes=cause_codes(params)
        table=list(csv.DictReader(io.StringIO('\n'.join(body)),delimiter='\t'))
        columns=list(table[0]) if table else []
        if 'Deaths' not in columns:flags.append('missing Deaths column')
        if kind=='county':
            if 'County Code' not in columns:flags.append('missing County Code column')
            parsed=read_wonder_export(str(path));count=len(parsed['rows']);supp=int(parsed['rows'].deaths_suppressed.sum());zero=int((parsed['rows'].deaths==0).sum())
            if group.strip()!='County':flags.append('county folder disagrees with Group By')
            location=params.get('Location','*All* (The United States)')
            if ('*All*' in location or location=='The United States') and count<minimum_counties:flags.append(f'all-US county export has fewer than {minimum_counties} rows; check Show Zero Values')
        else:
            rows=[r for r in table if r.get('Notes','').strip()!='Total' and r.get('Deaths','').strip()]
            count=len(rows);supp=sum(r['Deaths'].strip()=='Suppressed' for r in rows);zero=sum(r['Deaths'].strip()=='0' for r in rows)
            normalized=group.lower().replace('gender','sex')
            required=['ten-year age groups','sex']+(['state'] if kind=='state_age_sex' else [])
            if kind not in ('national_age_sex','state_age_sex') or not all(v in normalized for v in required):flags.append('folder kind disagrees with Group By')
        if cause=='premature_all_causes':
            age=' '.join(params.get('Ten-Year Age Groups','').split()).replace('–','-')
            if [x.strip() for x in age.split(';')]!=list(UNDER75):flags.append('premature all-causes must select exactly nine age groups under 75')
        elif params.get('Ten-Year Age Groups','*All*').strip() not in ('*All*','All','All Ages'):
            flags.append('unexpected age filter for all-age cause')
        if 'Underlying Cause of Death' not in database:flags.append('not an Underlying Cause of Death database')
        if expected_years[0]>=2018 and 'Single Race' not in database:flags.append('wrong database for 2018+ single-race exports')
        for key in ('Show Zero Values','Show Suppressed'):
            if params.get(key,'').lower() not in ('true','enabled','yes'):flags.append(f'{key} not enabled')
    if years!=expected_years:flags.append('folder years differ from query years')
    wanted=set(CAUSES.get('all_causes' if cause=='premature_all_causes' else cause,()))-{'*All*'}
    if cause not in CAUSES and cause!='premature_all_causes':flags.append('unrecognized cause filename')
    elif {c.replace(' ','') for c in codes}!=wanted:flags.append('ICD-10 selections differ from the declared cause')
    return dict(path=rel.as_posix(),database=database,years=years,group_by=group,cause_codes=sorted(codes),
                sha256=sha,rows=count,suppressed_rows=supp,zero_rows=zero,columns=columns,flags=flags)


def inventory(root):
    root=Path(root);records=[]
    for path in sorted(root.rglob('*')):
        if not path.is_file() or path.suffix.lower() not in ('.txt','.tsv','.xml') or path.name.endswith('.request.xml'):continue
        try:records.append(inspect_file(path,root))
        except (ValueError,OSError) as exc:records.append(dict(path=path.relative_to(root).as_posix(),flags=[str(exc)]))
    return records


def write_inventory(root,records):
    lines=['# WONDER structural inventory','', 'Structure only: no outcome–covariate associations computed. Raw exports/API responses remain private and gitignored.','',
           '| File | Database | Years | Group by | Cause codes | SHA-256 | Rows | Suppressed | Zero | Measures | Flags |',
           '| :-- | :-- | :-- | :-- | :-- | :-- | --: | --: | --: | :-- | :-- |']
    for r in records:
        vals=[r.get(k,'') for k in ('path','database','years','group_by','cause_codes','sha256','rows','suppressed_rows','zero_rows','columns','flags')]
        lines.append('| '+' | '.join(str(v).replace('|','/').replace('\n',' ') for v in vals)+' |')
    path=Path(root)/'INVENTORY.md';path.write_text('\n'.join(lines)+'\n');return path
