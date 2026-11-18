# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 29 synthetic-only fixtures. No live Census or WONDER requests."""
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import pytest
from census import wonder_api as api

FIXTURES=Path(__file__).parent/'fixtures/wonder'


class Clock:
 def __init__(self):self.now=1000.;self.sleeps=[]
 def clock(self):return self.now
 def sleep(self,s):self.sleeps.append(s);self.now+=s


def response():return (FIXTURES/'national_api.xml').read_bytes()

def query():return api.request_xml('all_causes',(2018,2019,2020,2021,2022),accept_data_use_restrictions=True)


def test_request_requires_explicit_true_acceptance():
 for accept in (None,False,1,'true'):
  with pytest.raises(api.WonderAPIError,match='explicit True'):api.request_xml('all_causes',(2018,),accept_data_use_restrictions=accept)
 with pytest.raises(TypeError):api.request_xml('all_causes',(2018,))


def test_location_and_unknown_parameters_refused_before_transport(tmp_path,monkeypatch):
 q=ET.fromstring(query());p=ET.SubElement(q,'parameter');ET.SubElement(p,'name').text='F_D158.V9';ET.SubElement(p,'value').text='26'
 raw=ET.tostring(q)
 with pytest.raises(api.WonderAPIError,match='national-only'):api.validate_national_request(raw)
 post=mock.Mock();monkeypatch.setattr(api,'request_xml',lambda *a,**k:raw)
 with api.WonderClient(tmp_path,post=post) as c:
  with pytest.raises(api.WonderAPIError):c.fetch('all_causes',(2018,),accept_data_use_restrictions=True,path=tmp_path/'x.xml')
 post.assert_not_called()


@pytest.mark.parametrize('parameter,value',[('B_1','D158.V9'),('B_2','D158.V10'),('B_3','D158.V11')])
def test_geographic_grouping_refused(parameter,value):
 root=ET.fromstring(query())
 for p in root.findall('parameter'):
  if p.findtext('name')==parameter:p.find('value').text=value
 with pytest.raises(api.WonderAPIError):api.validate_national_request(ET.tostring(root))


def test_echo_and_database_validation_fail_closed():
 q=query();info=api.validate_response(response(),q);assert info['database']=='D158' and info['cause']=='all_causes'
 for old,new in [(b'code="D158"',b'code="D76"'),(b'<value>2022</value>',b'<value>2023</value>'),(b'<value>D158.V5</value>',b'<value>D158.V9</value>')]:
  with pytest.raises(api.WonderAPIError):api.validate_response(response().replace(old,new),q)
 with pytest.raises(api.WonderAPIError):api.validate_response(b'<html>access denied</html>',q)


def test_rowspan_expansion_preserves_age_and_skips_totals():
 rows=api.response_rows(response());assert len(rows)==4
 assert [r['age'] for r in rows]==['< 1 year','< 1 year','1-4 years','1-4 years']
 assert [r['sex'] for r in rows]==['Female','Male','Female','Male']
 assert rows[1]['deaths']=='60'


def test_lock_refuses_concurrent_runs_and_is_released(tmp_path):
 with api.WonderClient(tmp_path):
  with pytest.raises(api.WonderAPIError,match='concurrently'):
   with api.WonderClient(tmp_path):pass
 assert not (tmp_path/'.wonder-api.lock').exists()


def test_throttle_persistent_and_one_retry_with_fake_clock(tmp_path):
 clk=Clock();times=[];attempt=[0]
 def post(*a,**kw):
  times.append(clk.now);attempt[0]+=1
  assert set(kw['data'])=={'request_xml'} and '@' not in kw['headers']['User-Agent']
  if attempt[0]==1:raise OSError('synthetic transport error')
  return SimpleNamespace(status_code=200,content=response())
 with api.WonderClient(tmp_path,post=post,clock=clk.clock,sleep=clk.sleep) as c:
  c.fetch('all_causes',(2018,2019,2020,2021,2022),accept_data_use_restrictions=True,path=tmp_path/'a.xml')
 with api.WonderClient(tmp_path,post=post,clock=clk.clock,sleep=clk.sleep) as c:
  c.fetch('all_causes',(2018,2019,2020,2021,2022),accept_data_use_restrictions=True,path=tmp_path/'b.xml')
 assert times==[1000,1120,1240] and sum(clk.sleeps)==240 and max(clk.sleeps)<=30
 assert (tmp_path/'a.request.xml').exists()


def test_retry_limited_and_existing_file_refused_before_request(tmp_path):
 clk=Clock();post=mock.Mock(side_effect=OSError('synthetic failure'))
 with api.WonderClient(tmp_path,post=post,clock=clk.clock,sleep=clk.sleep) as c:
  with pytest.raises(api.WonderAPIError,match='one throttled retry'):c.fetch('all_causes',(2018,),accept_data_use_restrictions=True,path=tmp_path/'a.xml')
 assert post.call_count==2
 path=tmp_path/'exists.xml';path.write_text('original');post.reset_mock()
 with api.WonderClient(tmp_path,post=post) as c:
  with pytest.raises(api.WonderAPIError,match='existing cache'):c.fetch('all_causes',(2018,),accept_data_use_restrictions=True,path=path)
 assert path.read_text()=='original';post.assert_not_called()


def test_no_library_network_transport_or_xml_entities(tmp_path):
 with api.WonderClient(tmp_path) as c:
  with pytest.raises(api.WonderAPIError,match='fetch script'):c.fetch('all_causes',(2018,),accept_data_use_restrictions=True,path=tmp_path/'x.xml')
 with pytest.raises(api.WonderAPIError,match='DOCTYPE'):api.xml_parameters(b'<!DOCTYPE x [<!ENTITY y "a">]><x/>')


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
