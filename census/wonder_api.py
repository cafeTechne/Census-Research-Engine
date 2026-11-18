# SPDX-License-Identifier: AGPL-3.0-or-later
"""National-only CDC WONDER API requests. No network transport is installed here.

The fetch script supplies transport after explicit data-use acceptance. Dataset
D158 is confirmed by the public expanded-database HTML form action. Parameter
suffixes V1/V2/V5/V7 and M1/M2/M3 come from CDC's published D76 example metadata;
D158's age/sex labels and echoed selections MUST be confirmed by the probe.
Sources: https://wonder.cdc.gov/wonder/help/wonder-api.html and its Example1 XML.
No web-form submission, location query, browser impersonation or bot bypass.
"""
from contextlib import AbstractContextManager
import hashlib
import json
import os
from pathlib import Path
import time
import xml.etree.ElementTree as ET

DATABASE='D158'
ENDPOINT='https://wonder.cdc.gov/controller/datarequest/D158'
USER_AGENT='Census-Research-Engine/0.26 (national statistical reference client)'
CAUSES={
    'all_causes':('*All*',),
    'heart_disease':('I00-I09','I11','I13','I20-I51'),
    'drug_overdose':('X40-X44','X60-X64','X85','Y10-Y14'),
    'cancer':('C00-C97',),
    'unintentional_injury':('V01-X59','Y85-Y86'),
    'suicide':('U03','X60-X84','Y87.0'),
    'diabetes':('E10-E14',),
}
METADATA_SOURCES=(
    'https://wonder.cdc.gov/ucd-icd10-expanded.html',
    'https://wonder.cdc.gov/wonder/help/api-examples/D76_Example1-req.xml',
    'https://wonder.cdc.gov/wonder/help/api-examples/D76_Example1-resp.xml',
)


class WonderAPIError(ValueError):
    pass


def parameters(cause,years):
    if cause not in CAUSES:raise WonderAPIError('unsupported cause')
    years=tuple(years)
    if not years or any(type(y) is not int or not 2018<=y<=2024 for y in years) or len(set(years))!=len(years):
        raise WonderAPIError('D158 requires distinct release years in 2018..2024')
    return {'dataset_code':[DATABASE], 'B_1':['D158.V5'],'B_2':['D158.V7'],
            'B_3':['*None*'],'B_4':['*None*'],'B_5':['*None*'],
            'M_1':['D158.M1'],'M_2':['D158.M2'],'M_3':['D158.M3'],
            'F_D158.V1':list(map(str,sorted(years))),'O_V1_fmode':['freg'],
            'O_age':['D158.V5'],'V_D158.V5':['*All*'],'V_D158.V7':['*All*'],
            'O_ucd':['D158.V2'],'F_D158.V2':list(CAUSES[cause]),'O_V2_fmode':['freg'],
            'O_show_suppressed':['true'],'O_show_zeros':['true'],'O_show_totals':['true'],
            'O_rate_per':['100000'],'O_precision':['1'],'O_timeout':['600'],
            'accept_datause_restrictions':['true']}


def request_xml(cause,years,*,accept_data_use_restrictions):
    if accept_data_use_restrictions is not True:raise WonderAPIError('explicit True acceptance of data-use restrictions required')
    root=ET.Element('request-parameters')
    for key,values in parameters(cause,years).items():
        p=ET.SubElement(root,'parameter');ET.SubElement(p,'name').text=key
        for value in values:ET.SubElement(p,'value').text=value
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)


def xml_parameters(raw):
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():raise WonderAPIError('XML entities/DOCTYPE refused')
    try:root=ET.fromstring(raw)
    except ET.ParseError as exc:raise WonderAPIError('response is not WONDER XML (possibly an access/error page)') from exc
    node=root if root.tag=='request-parameters' else root.find('.//request-parameters')
    if node is None:raise WonderAPIError('WONDER response lacks echoed request parameters')
    out={}
    for p in node.findall('parameter'):
        key=p.findtext('name')
        if not key or key in out:raise WonderAPIError('missing or repeated request parameter')
        out[key]=[(v.text or '').strip() for v in p.findall('value')]
    return root,out


def validate_national_request(raw):
    _,p=xml_parameters(raw)
    # An allowlist refuses ALL unrecognized fields, including location fields
    # even when their value is All; unknown group-bys also fail closed.
    allowed=set(parameters('all_causes',(2018,)))
    if set(p)-allowed:raise WonderAPIError('national-only request: location or unrecognized parameter refused')
    if p.get('dataset_code')!=[DATABASE] or p.get('B_1')!=['D158.V5'] or p.get('B_2')!=['D158.V7']:
        raise WonderAPIError('national-only ten-year age/sex grouping required')
    if any(p.get(f'B_{n}')!=['*None*'] for n in (3,4,5)):raise WonderAPIError('location/additional grouping refused')
    if p.get('accept_datause_restrictions')!=['true']:raise WonderAPIError('explicit acceptance missing')
    try:years=tuple(int(v) for v in p['F_D158.V1'])
    except (KeyError,ValueError):raise WonderAPIError('invalid requested years') from None
    cause=next((c for c,codes in CAUSES.items() if list(codes)==p.get('F_D158.V2')),None)
    if cause is None:raise WonderAPIError('unregistered cause selection')
    expected=parameters(cause,years)
    if p!=expected:raise WonderAPIError('request differs from the documented national query template')
    return cause,years


def validate_response(raw,request):
    cause,years=validate_national_request(request)
    root,echo=xml_parameters(raw)
    dataset=root.find('dataset')
    if dataset is None or dataset.get('code')!=DATABASE:raise WonderAPIError('response database mismatch')
    for key in ('B_1','B_2','F_D158.V1','O_ucd','F_D158.V2'):
        if echo.get(key)!=parameters(cause,years)[key]:raise WonderAPIError(f'response echo mismatch: {key}')
    labels={v.get('code'):v.get('label','') for v in root.iter('variable')}
    if 'ten-year' not in labels.get('D158.V5','').lower() or labels.get('D158.V7','').lower() not in ('sex','gender'):
        raise WonderAPIError('probe did not confirm D158 ten-year-age and sex parameter labels')
    if root.find('.//data-table') is None:raise WonderAPIError('response has no data table')
    return {'database':DATABASE,'years':list(years),'group_by':['Ten-Year Age Groups','Sex'],
            'cause':cause,'cause_codes':list(CAUSES[cause]),'metadata_sources':list(METADATA_SOURCES)}


def response_rows(raw):
    """Expand WONDER's row-spanning XML cells; omit totals/subtotals."""
    root,_=xml_parameters(raw);table=root.find('.//data-table')
    if table is None:raise WonderAPIError('no data table')
    spans={};rows=[]
    for r in table.findall('r'):
        cells=list(r.findall('c'));current=[];pos=0;col=0
        while pos<len(cells) or (col in spans and spans[col][1]>0):
            if col in spans and spans[col][1]>0:
                value,left=spans[col];current.append(value);spans[col]=(value,left-1)
            else:
                c=cells[pos];pos+=1;value=c.get('l',c.get('v',''));current.append(value)
                count=int(c.get('r','1'))
                if count>1:spans[col]=(value,count-1)
            col+=1
        if any(c.get('c') in ('1','2') for c in cells):continue
        if len(current)<4:raise WonderAPIError('truncated age/sex data row')
        if current[1] not in ('Male','Female','M','F'):continue
        rows.append(dict(age=current[0],sex=current[1],deaths=current[2],population=current[3]))
    if not rows:raise WonderAPIError('no national age/sex rows')
    return rows


class WonderClient(AbstractContextManager):
    """Serialized, persistent 120-second throttle. Transport is script-injected."""
    def __init__(self,root,*,post=None,clock=time.time,sleep=time.sleep):
        self.root=Path(root);self.post=post;self.clock=clock;self.sleep=sleep;self.locked=False
        self.lock=self.root/'.wonder-api.lock';self.stamp=self.root/'.wonder-api-last-request'
    def __enter__(self):
        self.root.mkdir(parents=True,exist_ok=True)
        try:
            with self.lock.open('x') as f:f.write(str(os.getpid()))
        except FileExistsError as exc:raise WonderAPIError('another WONDER run holds the lock; do not run concurrently') from exc
        self.locked=True;return self
    def __exit__(self,*exc):
        if self.locked:self.lock.unlink();self.locked=False
    def _wait(self):
        last=float(self.stamp.read_text()) if self.stamp.exists() else float('-inf')
        while self.clock()-last<120:self.sleep(min(30,120-(self.clock()-last)))
        self.stamp.write_text(str(self.clock()))
    def fetch(self,cause,years,*,accept_data_use_restrictions,path):
        req=request_xml(cause,years,accept_data_use_restrictions=accept_data_use_restrictions)
        validate_national_request(req)
        if not self.locked:raise WonderAPIError('use WonderClient as a context manager')
        path=Path(path);request_path=path.with_suffix('.request.xml')
        if path.exists() or request_path.exists():raise WonderAPIError('existing cache file refused; choose a new _v2 name')
        if self.post is None:raise WonderAPIError('network transport is only installed by the fetch script')
        response=None
        for attempt in range(2):
            self._wait()
            try:
                response=self.post(ENDPOINT,data={'request_xml':req.decode()},headers={'User-Agent':USER_AGENT},timeout=600)
                if response.status_code>=500 or response.status_code==429:raise OSError(f'WONDER HTTP {response.status_code}')
                if response.status_code!=200:raise WonderAPIError(f'WONDER refused D158 API query (HTTP {response.status_code})')
                break
            except OSError as exc:
                if attempt:raise WonderAPIError(f'WONDER transport failed after one throttled retry: {type(exc).__name__}') from exc
        raw=response.content
        info=validate_response(raw,req);response_rows(raw)
        path.parent.mkdir(parents=True,exist_ok=True)
        with request_path.open('xb') as f:f.write(req)
        with path.open('xb') as f:f.write(raw)
        info.update(file=str(path),sha256=hashlib.sha256(raw).hexdigest(),request_sha256=hashlib.sha256(req).hexdigest(),data_use_accepted=True)
        return info
