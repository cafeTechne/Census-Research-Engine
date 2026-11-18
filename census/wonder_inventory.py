# SPDX-License-Identifier: AGPL-3.0-or-later
"""Structural inventory of manual WONDER exports; no network or associations."""
import csv
import hashlib
import io
import os
from pathlib import Path
import re
from .vital_records import _split_footer,parse_footer,read_wonder_export,WonderExportError

CAUSES={
 'all_causes':(), 'premature_all_causes':(),
 'heart_disease':('I00-I09','I11','I13','I20-I51'),
 'drug_overdose':('X40-X44','X60-X64','X85','Y10-Y14'),
 'cancer':('C00-C97',),'unintentional_injury':('V01-X59','Y85-Y86'),
 'suicide':('U03','X60-X84','Y87.0'),'diabetes':('E10-E14',),
 'stroke':('I60-I69',),'clrd':('J40-J47',),'liver_disease':('K70','K73-K74'),
 'kidney_disease':('N00-N07','N17-N19','N25-N27'),
 'alcohol_induced':(), 'firearm':(),
}
DRUGS={'any_opioid':('T40.0','T40.1','T40.2','T40.3','T40.4','T40.6'),
       'synthetic_opioid':('T40.4',),'cocaine':('T40.5',),'psychostimulant':('T43.6',)}
UNDER75=('< 1 year','1-4 years','5-14 years','15-24 years','25-34 years','35-44 years','45-54 years','55-64 years','65-74 years')


def years_from_parameters(parameters):
 return sorted(set(map(int,re.findall(r'\b(?:19|20)\d{2}\b',parameters.get('Year/Month',parameters.get('Year',''))))))


def codes_in(text):
 text=str(text).upper().replace('–','-').replace('—','-')
 return {x.replace(' ','') for x in re.findall(r'\b[A-Z][0-9]{2}(?:\.[0-9]+)?(?:\s*-\s*[A-Z][0-9]{2}(?:\.[0-9]+)?)?',text)}


def cause_codes(parameters):
 return codes_in('; '.join(str(v) for k,v in parameters.items() if any(x in k for x in ('Cause List','ICD-10 Codes','Drug/Alcohol'))))


def inspect_file(path,root,*,minimum_counties=3100):
 path=Path(path);rel=path.relative_to(root);parts=rel.parts;flags=[]
 if len(parts)!=4 or parts[0] not in ('ucd','mcd'):raise WonderExportError('expected ucd|mcd/<years>/<group>/<cause> layout')
 family,window,kind=parts[:3];m=re.fullmatch(r'(\d{4})-(\d{4})',window)
 if not m:raise WonderExportError('folder years must be YYYY-YYYY')
 expected_years=list(range(int(m[1]),int(m[2])+1));cause=re.sub(r'_v[0-9]+$','',path.stem)
 raw=path.read_bytes();body,footer=_split_footer(raw.decode('utf-8-sig'));meta=parse_footer(footer);params=meta['parameters']
 database=meta['dataset'];years=years_from_parameters(params);group=params.get('Group By','')
 table=list(csv.DictReader(io.StringIO('\n'.join(body)),delimiter='\t'));columns=list(table[0]) if table else []
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
  normalized=group.lower().replace('gender','sex');parts_group={v.strip() for v in normalized.split(';')}
  wanted={'ten-year age groups','sex'}|({'state'} if kind=='state_age_sex' else set())
  if kind not in ('national_age_sex','state_age_sex') or parts_group!=wanted:flags.append('folder kind disagrees with Group By')
  if kind=='national_age_sex' and not 22<=count<=24:flags.append('national reference must have 22–24 age/sex rows')
 if years!=expected_years:flags.append('folder years differ from query years')
 expected_database=('Multiple Cause of Death, 2018-2024, Single Race' if family=='mcd' and window=='2018-2022' else
                    'Underlying Cause of Death, 2018-2024, Single Race' if family=='ucd' and window=='2018-2022' else
                    'Underlying Cause of Death, 1999-2020' if family=='ucd' and window=='2013-2017' else None)
 if expected_database is None or database.replace('–','-')!=expected_database:flags.append('database differs from folder family/years')
 if family=='mcd':
  ucd=params.get('UCD - Drug/Alcohol Induced Causes','');mcd=params.get('MCD - ICD-10 Codes','');codes=codes_in(ucd)|codes_in(mcd)
  if cause not in DRUGS or codes_in(mcd)!=set(DRUGS.get(cause,())) or not mcd:flags.append('MCD - ICD-10 Codes missing or differs from drug involvement selection')
  if codes_in(ucd)!=set(CAUSES['drug_overdose']):flags.append('UCD overdose items missing or incorrect')
 else:
  codes=cause_codes(params)
  if cause not in CAUSES:flags.append('unrecognized cause filename')
  elif cause=='alcohol_induced':
   if params.get('Drug/Alcohol Induced Causes','').strip()!='Alcohol-induced causes':flags.append('alcohol-induced selection differs from guide')
  elif cause=='firearm':
   if params.get('Injury Mechanism & All Other Leading Causes','').strip()!='Firearm':flags.append('firearm mechanism selection differs from guide')
  elif codes!=set(CAUSES[cause]):flags.append('ICD-10 selections differ from the declared cause')
 if cause=='premature_all_causes':
  age=' '.join(params.get('Ten-Year Age Groups','').split()).replace('–','-')
  if [x.strip() for x in age.split(';')]!=list(UNDER75):flags.append('premature all-causes must select exactly nine age groups under 75')
 elif params.get('Ten-Year Age Groups','*All*').strip() not in ('*All*','All','All Ages'):flags.append('unexpected age filter for all-age cause')
 for key in ('Show Zero Values','Show Suppressed'):
  if params.get(key,'').lower() not in ('true','enabled','yes'):flags.append(f'{key} not enabled')
 return dict(path=rel.as_posix(),database=database,years=years,group_by=group,cause_codes=sorted(codes),
             sha256=hashlib.sha256(raw).hexdigest(),rows=count,suppressed_rows=supp,zero_rows=zero,columns=columns,flags=flags)


def inventory(root):
 root=Path(root);records=[]
 for directory,dirs,files in os.walk(root):
  dirs[:]=sorted(d for d in dirs if d!='.git')
  for name in sorted(files):
   path=Path(directory)/name
   if path.suffix.lower() not in ('.txt','.tsv'):continue
   try:records.append(inspect_file(path,root))
   except (ValueError,OSError) as exc:records.append(dict(path=path.relative_to(root).as_posix(),flags=[str(exc)]))
 return sorted(records,key=lambda r:r['path'])


def write_inventory(root,records):
 lines=['# WONDER structural inventory','', 'Manual exports only. Structure checked without associations. Raw files stay private; suppressed cells are recorded, not reconstructed.','',
        '| File | Database | Years | Group by | Cause codes | SHA-256 | Rows | Suppressed | Zero | Measures | Flags |',
        '| :-- | :-- | :-- | :-- | :-- | :-- | --: | --: | --: | :-- | :-- |']
 for r in records:
  vals=[r.get(k,'') for k in ('path','database','years','group_by','cause_codes','sha256','rows','suppressed_rows','zero_rows','columns','flags')]
  lines.append('| '+' | '.join(str(v).replace('|','/').replace('\n',' ') for v in vals)+' |')
 path=Path(root)/'INVENTORY.md';path.write_text('\n'.join(lines)+'\n');return path
