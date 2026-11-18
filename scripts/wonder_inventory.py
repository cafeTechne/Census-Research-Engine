#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Write a private, structural-only inventory of manual exports/national API files."""
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from census.wonder_inventory import inventory,write_inventory


def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT/'external_data/wonder');a=p.parse_args()
 records=inventory(a.root);path=write_inventory(a.root,records)
 for r in records:print(r['path'], 'OK' if not r['flags'] else '; '.join(r['flags']))
 print(f'{len(records)} files; {sum(bool(r["flags"]) for r in records)} flagged. Inventory: {path}')
 return int(not records or any(r['flags'] for r in records))

if __name__=='__main__':raise SystemExit(main())
