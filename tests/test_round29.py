# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 29 synthetic-only fixtures. No live Census or WONDER requests."""
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import pytest

FIXTURES=Path(__file__).parent/'fixtures/wonder'


def test_real_format_wrapped_parameters_and_missing_optional_measures():
 from census.vital_records import read_wonder_export
 first=read_wonder_export(str(FIXTURES/'heart_disease.tsv'));rows=first['rows']
 assert rows.GEOID.tolist()==['01001','01003','01005']
 assert np.isnan(rows.population.iloc[2]) and rows.deaths.iloc[2]==0
 assert any('unavailable' in n for n in first['notes'])
 second=read_wonder_export(str(FIXTURES/'premature_all_causes.tsv'))
 assert second['footer']['parameters']['Ten-Year Age Groups'].endswith('65-74 years')
 assert second['footer']['parameters']['Year/Month'].endswith('2022')
 assert second['rows'].population.isna().all() and any('Deaths-only' in n for n in second['notes'])


def test_inventory_compares_codes_and_detects_structural_mismatches(tmp_path):
 from census.wonder_inventory import inspect_file
 folder=tmp_path/'ucd/2018-2022/county';folder.mkdir(parents=True)
 file=folder/'heart_disease.tsv';text=(FIXTURES/'heart_disease.tsv').read_text();file.write_text(text)
 assert inspect_file(file,tmp_path,minimum_counties=0)['flags']==[]
 assert any('fewer than 3100' in f for f in inspect_file(file,tmp_path)['flags'])
 for old,new,flag in [('I00-I09,I11,I13,I20-I51','C00-C97','ICD-10'),('2022','2023','years'),('Group By: County','Group By: State','Group By')]:
  file.write_text(text.replace(old,new));assert any(flag in f for f in inspect_file(file,tmp_path,minimum_counties=0)['flags'])
 file=folder/'premature_all_causes.tsv';file.write_text((FIXTURES/file.name).read_text())
 assert inspect_file(file,tmp_path,minimum_counties=0)['flags']==[]
 file.write_text(file.read_text().replace('65-74','75-84'))
 assert any('nine age groups' in f for f in inspect_file(file,tmp_path,minimum_counties=0)['flags'])


def test_equivalent_cancer_codes_do_not_depend_on_form_tab():
 from census.wonder_inventory import cause_codes
 assert cause_codes({'ICD-10 Codes':'C00-C97'})==cause_codes({'ICD-10 113 Cause List':'#Malignant neoplasms (C00-C97)'})


def test_wrapped_drug_selection_preserves_later_parameters():
 from census.vital_records import parse_footer
 p=parse_footer(['Dataset: Synthetic','Query Parameters:','Drug/Alcohol Induced Causes: Unintentional (X40-X44); Suicide (X60-X64);',
 'Homicide (X85); Undetermined (Y10-Y14)','Year/Month: 2018; 2019; 2020; 2021; 2022','Group By: County','Query Date: synthetic'])['parameters']
 assert p['Drug/Alcohol Induced Causes'].endswith('(Y10-Y14)') and p['Group By']=='County'


def test_reference_bands_rates_and_not_stated_note():
 from census.vital_records import read_wonder_reference
 r=read_wonder_reference(FIXTURES/'national_age_sex.tsv');rows=r['rows']
 assert len(rows)==20 and rows.sex.tolist()==['M']*10+['F']*10
 assert rows.iloc[0].deaths==60 and rows.iloc[0].population==5000
 assert rows.iloc[0].rate==pytest.approx(60/5000) # Not a mean of component rates.
 assert rows.iloc[1].rate==pytest.approx(50/10000)
 assert any('2 Not Stated' in n for n in r['notes']) and r['years']==[2018,2019,2020,2021,2022]


def test_reference_pin_and_suppression_national_vs_state(tmp_path):
 from census.vital_records import read_wonder_reference
 import hashlib
 source=(FIXTURES/'national_age_sex.tsv').read_text();path=tmp_path/'ref.tsv';path.write_text(source)
 with pytest.raises(ValueError,match='SHA-256'):read_wonder_reference(path,expected_sha256='0'*64)
 path.write_text(source.replace('\t20\t1000\t','\tSuppressed\t1000\t',1))
 with pytest.raises(ValueError,match='suppressed reference'):read_wonder_reference(path)
 lines=path.read_text().splitlines();lines[0]+='\t"State Code"'
 for i in range(1,25):lines[i]+='\t"26"'
 path.write_text(('\n'.join(lines)+'\n').replace('Group By: Ten-Year Age Groups; Sex','Group By: State; Ten-Year Age Groups; Sex'))
 with pytest.raises(ValueError,match='preregistered'):read_wonder_reference(path)
 r=read_wonder_reference(path,state='26',validate_only=True);assert r['rows'].suppressed.any()
 with pytest.raises(ValueError,match='suppressed reference'):read_wonder_reference(path,state='26')


def test_acs_template_covers_each_cell_once_and_fixed_reference_order():
 from census.wonder_reference import acs_age_sex_bands,validate_band_order
 t=acs_age_sex_bands(2022);refs=[v['ref'] for v in t['variables']]
 assert len(refs)==46 and len(set(refs))==46 and len(t['derivations'])==20
 assert {int(r.rsplit('_',1)[1]) for r in refs}==set(range(3,26))|set(range(27,50))
 validate_band_order(t['population_bands'])
 with pytest.raises(ValueError,match='order'):validate_band_order(t['population_bands'][::-1])


def expected_entry():
 import hashlib
 from census.wonder_reference import acs_age_sex_bands
 t=acs_age_sex_bands(2022)
 path=FIXTURES/'national_age_sex.tsv'
 return dict(name='expected',op='expected_count',population_bands=t['population_bands'],period_years=5,
             reference_export={'file':str(path.resolve()),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})


def test_expected_count_point_and_replicates_and_period_validation():
 from census.wonder_reference import expected_count_weights
 from census.analysis import analysis_frame,attach_replicates
 from census.simulation import replicate_long,make_replicates
 entry=expected_entry();names=entry['population_bands'];weights,_=expected_count_weights(entry)
 frame=pd.DataFrame({'GEOID':['01001','01003'],'Year':2022})
 values=np.arange(40,dtype=float).reshape(2,20)+100
 for j,name in enumerate(names):frame[name+'E']=values[:,j];frame[name+'M']=2.
 result=analysis_frame(frame,variables={n:n for n in names},derive=[entry])
 np.testing.assert_allclose(result.expected,values@weights)
 rep=make_replicates(values,np.ones_like(values),np.random.default_rng(29))
 long=replicate_long(frame.GEOID,names,values,rep);long['Year']=2022
 out,reps=attach_replicates(result,long,variables={n:n for n in names},derive=[entry],replace_se=True)
 er=np.einsum('abr,b->ar',rep,weights)
 np.testing.assert_allclose(out.expected_se,np.sqrt(.05*np.sum((er-result.expected.to_numpy()[:,None])**2,axis=1)),rtol=1e-10)
 bad=dict(entry,period_years=4)
 with pytest.raises(ValueError,match='footer years'):expected_count_weights(bad)


def test_wonder_join_identity_suppression_zero_and_missing_are_distinct():
 from census.health_sources import join_external
 frame=pd.DataFrame({'GEOID':['01001','01003','01005'],'x':[1.,2.,3.]})
 ext=pd.DataFrame({'GEOID':frame.GEOID,'y':[20.,np.nan,0.],'y_numerator':[20.,np.nan,0.],'y_flag':[0,2,0]})
 ext.attrs['wonder_columns']=['y']
 out,info=join_external(frame,ext,['y'],['x'])
 assert info['matched_units']==3 and info['suppressed_units']==1 and info['analyzable_units']==2
 assert info['missing_share_by_variable']['y']==0 and out.y.iloc[2]==0
 assert info['wonder']['y']['excluded_deaths_bounds']==[1,9]
 missing=ext.iloc[:2].copy();missing.attrs=ext.attrs
 _,record=join_external(frame,missing,['y'],['x']);assert record['unmatched_units']==1 and record['missing_share_by_variable']['y']==pytest.approx(1/3)
 missing=ext.copy();missing.loc[2,'y']=np.nan;missing.attrs=ext.attrs
 _,record=join_external(frame,missing,['y'],['x']);assert record['wonder']['y']['unsuppressed_missing']==1 and record['matched_units']==3


def test_other_sources_keep_their_original_join_semantics():
 from census.health_sources import join_external
 f=pd.DataFrame({'GEOID':['01001','01003','01005'],'x':[1.,2.,3.]})
 e=pd.DataFrame({'GEOID':f.GEOID,'y':[1.,np.nan,0.],'y_flag':[0,2,0]})
 _,info=join_external(f,e,['y'],['x'])
 assert info['matched_units']==2 and info['missing_share_by_variable']['y']==pytest.approx(1/3) and 'wonder' not in info


def test_wonder_bundle_suppresses_derived_values_and_refuses_complementary_totals(tmp_path):
 import json
 from census.report_tables import results_bundle
 hidden=['01003'];cols={k:hidden for k in ('observed','smr','eb_ratio','eb_lower','eb_upper')}
 policy={'columns':cols,'results':{},'figures':{},'count_column':'observed'}
 data=pd.DataFrame({'GEOID':['01001','01003'],'observed':[20.,5.],'smr':[2.,.5],'eb_ratio':[1.8,.7],'eb_lower':[1.2,.2],'eb_upper':[2.4,1.6]})
 results_bundle(tmp_path/'ok',results={'rates':{'rows':data}},wonder_policy=policy)
 saved=json.loads((tmp_path/'ok/results/rates.json').read_text())['rows']
 assert saved[1]['observed']=='suppressed' and all(saved[1][k]=='suppressed' for k in cols)
 total=pd.concat([data,pd.DataFrame({'GEOID':['all'],'observed':[25.],'smr':[1.]})],ignore_index=True)
 with pytest.raises(ValueError,match='complementary'):results_bundle(tmp_path/'bad',results={'rates':{'rows':total}},wonder_policy=policy)
 total.loc[total.GEOID=='all','observed']=20.
 results_bundle(tmp_path/'complete-case',results={'rates':{'rows':total}},wonder_policy=policy)


def test_safe_snapshots_preserve_suppression_labels_and_restore_for_refits(tmp_path):
 from census.manifest.run import _write_analysed_data
 from census.wonder_outputs import restore_snapshot
 f=pd.DataFrame({'GEOID':['01001','01003'],'y':[20.,np.nan],'y_numerator':[20.,np.nan],'y_flag':[0,2],'x':[.1,.2]})
 f.attrs['wonder_columns']=['y'];files=_write_analysed_data(tmp_path,f,None);path=tmp_path/files['analysis_frame']['path']
 saved=pd.read_parquet(path) if path.suffix=='.parquet' else pd.read_csv(path,dtype={'GEOID':str})
 assert saved.y.iloc[1]=='suppressed' and saved.x.iloc[1]==.2
 restored=restore_snapshot(saved,['y']);assert np.isnan(restored.y.iloc[1]) and restored.y.iloc[0]==20.


def test_older_bare_unreliable_rates_are_missing_not_invalid(tmp_path):
 from census.vital_records import read_wonder_export
 path=tmp_path/'old.tsv';path.write_text((FIXTURES/'heart_disease.tsv').read_text().replace('2000\n','Unreliable\n'))
 r=read_wonder_export(path)['rows'];assert np.isnan(r.crude_rate.iloc[0]) and r.unreliable.iloc[0]
