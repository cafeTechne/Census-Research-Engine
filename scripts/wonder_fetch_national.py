#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Official WONDER API only: national age x sex references, serial and throttled."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from census.wonder_api import WonderClient,CAUSES,WonderAPIError


def next_path(folder,cause):
    p=folder/(cause+'.xml');version=1
    while p.exists() or p.with_suffix('.request.xml').exists():
        version+=1;p=folder/f'{cause}_v{version}.xml'
    return p


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT/'external_data/wonder')
    p.add_argument('--accept-data-use-restrictions',action='store_true');p.add_argument('--probe-only',action='store_true')
    a=p.parse_args()
    if a.accept_data_use_restrictions is not True:p.error('explicit --accept-data-use-restrictions required')
    import requests # Network use occurs here, never in manifest runs or tests.
    folder=a.root/'ucd/2018-2022/national_age_sex'
    with WonderClient(a.root,post=requests.post) as client:
        for cause in (list(CAUSES)[:1] if a.probe_only else CAUSES):
            print(f'National D158 request: {cause}; subsequent requests wait >=120 seconds.',flush=True)
            try:
                info=client.fetch(cause,(2018,2019,2020,2021,2022),accept_data_use_restrictions=True,path=next_path(folder,cause))
            except WonderAPIError as exc:
                print(f'National API unavailable/refused: {exc}. No web-form fallback is automated.',file=sys.stderr,flush=True)
                return 2
            print(json.dumps(info),flush=True)
    return 0

if __name__=='__main__':raise SystemExit(main())
