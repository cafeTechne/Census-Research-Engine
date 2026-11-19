# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 47 exploratory example (author self-review, not independent; not a registered study).

    python scripts/r47_causal_example.py R29_ARCHIVE R31_ARCHIVE CACHE_DB OUT_DIR

MI/NY counties, Round 29 log SMRs (H1-H3; counties with hidden counts excluded):
(a) IV: poverty 2018-2022 instrumented by poverty 2011-2015 (non-overlapping release, summed from the
    cached tract tables, read-only); OLS vs 2SLS vs Anderson-Rubin, first-stage F; state term as control.
(b) Treatment effect of metro status (Round 31 frame) on log SMR adjusting for poverty and share 65+
    (both with ACS SEs): plain AIPW vs calibrated AIPW.
Coefficients only; WONDER disclosure audit must pass. No network access.
"""
import json
import sqlite3
import sys
import tarfile
import warnings
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'scripts'))
import numpy as np
import pandas as pd
from census import causal
from census.wonder_outputs import audit_outputs, restore_snapshot
from r30_posthoc_im_acs import load_verified
from r44_posthoc_r29 import REGIONS, HYPS, extract, digest


def poverty_2015(cache):
    con = sqlite3.connect(f"file:{cache}?mode=ro", uri=True)
    rows = con.execute("select payload from responses where endpoint like '%/2015/acs/acs5' "
                       "and params like '%group(B17001)%' and params like '%tract%'").fetchall()
    parts = []
    for (payload,) in rows:
        d = json.loads(payload); t = pd.DataFrame(d[1:], columns=d[0])
        parts.append(t[['state', 'county', 'B17001_001E', 'B17001_002E']])
    t = pd.concat(parts)
    if set(t.state) != {'26', '36'}:
        raise ValueError('expected cached 2015 tract tables for MI and NY')
    t['GEOID'] = t.state+t.county
    g = t.assign(**{c: pd.to_numeric(t[c]) for c in ('B17001_001E', 'B17001_002E')}).groupby('GEOID')[['B17001_001E', 'B17001_002E']].sum()
    return (100*g.B17001_002E/g.B17001_001E).rename('poverty_2015').reset_index()


def share65(r31):
    with TemporaryDirectory(prefix='r47-r31-') as tmp, tarfile.open(r31) as tar:
        tar.extractall(tmp, filter='data')
        f = pd.read_parquet(Path(tmp)/'r31ex/frame.parquet'); reps = pd.read_parquet(Path(tmp)/'r31ex/replicates.parquet')
    r = reps[reps.variable == 'share65'].set_index('GEOID')
    rc = [c for c in r.columns if c.startswith('rep_') or c.startswith('Var_Rep') or c.startswith('rep')]
    se = np.sqrt(4/80*((r[rc].sub(r['estimate'], axis=0))**2).sum(axis=1)).rename('share65_se')
    return f[['GEOID', 'share65', 'metro_class']].merge(se.reset_index(), on='GEOID')


def main():
    r29, r31, cache, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]).resolve()
    if out.exists():
        raise SystemExit('use a fresh output directory')
    warnings.simplefilter('ignore')
    summary = dict(status='exploratory example; author self-review, not independent', r29_archive_sha256=digest(r29),
                   r31_archive_sha256=digest(r31))
    with patch('requests.sessions.Session.request', side_effect=RuntimeError('HTTP blocked')), \
         TemporaryDirectory(prefix='r47-input-') as scratch:
        folders = extract(r29, scratch)
        m, run, data, _ = load_verified(folders['mi_ny'], REGIONS['mi_ny'][0])
        f = restore_snapshot(data['analysis_frame'], list(HYPS))
        f = f.merge(poverty_2015(cache), on='GEOID', how='left').merge(share65(r31), on='GEOID', how='left')
        f['NY'] = f.GEOID.str.startswith('36').astype(float)
        f['metro'] = (f.metro_class != 'nonmetro').astype(float)
        res = dict(n_counties=len(f), corr_poverty_releases=float(f[['poverty', 'poverty_2015']].corr().iloc[0, 1]),
                   iv={}, treatment={})
        for h in HYPS:
            g = f[(f[f'{h}_numerator'] > 0) & (f[f'E_{h}'] > 0)].copy()
            g['log_smr'] = np.log(g[f'{h}_numerator']/g[f'E_{h}'])
            iv = causal.iv_slope(g, 'log_smr', 'poverty', 'poverty_2015', ['NY'])
            ar = iv['ar_interval']
            res['iv'][h] = dict(n=iv['n'], first_stage_f=iv['first_stage_f'], ols=iv['ols_naive'], tsls=iv['iv'],
                                anderson_rubin=dict(kind=ar['kind'], lower=ar['lower'], upper=ar['upper']))
            plain = causal.estimate_effect(g, 'log_smr', 'metro', ['poverty', 'share65'])
            cal = causal.estimate_effect(g, 'log_smr', 'metro', ['poverty', 'share65'], calibrate=True)
            res['treatment'][h] = dict(n=plain['n'], n_metro=plain['n_treated'], aipw=plain['ate'],
                                       aipw_calibrated={k: cal['ate'][k] for k in ('estimate', 'lower', 'upper')})
        part = out/'mi_ny'; part.mkdir(parents=True)
        (part/'r47_example.json').write_text(json.dumps(res, indent=2, allow_nan=False, default=float)+'\n')
        audit = audit_outputs(part, run['wonder_output_policy'])
        if not audit['passed']:
            raise ValueError('WONDER disclosure audit failed')
        summary['mi_ny'] = res; summary['wonder_disclosure'] = audit
    (out/'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False, default=float)+'\n')
    print('corr(poverty 2022, 2015) %.3f' % res['corr_poverty_releases'])
    for h in HYPS:
        v, t = res['iv'][h], res['treatment'][h]
        print(h, 'n', v['n'], 'F %.1f' % v['first_stage_f'], 'OLS %.4f' % v['ols']['estimate'],
              '2SLS %.4f (%.4f, %.4f)' % (v['tsls']['estimate'], v['tsls']['lower'], v['tsls']['upper']),
              'AR', v['anderson_rubin'])
        print('  metro AIPW %.4f (%.4f, %.4f)' % (t['aipw']['estimate'], t['aipw']['lower'], t['aipw']['upper']),
              'calibrated %.4f (%.4f, %.4f)' % tuple(t['aipw_calibrated'][k] for k in ('estimate', 'lower', 'upper')),
              'n_metro', t['n_metro'])


if __name__ == '__main__':
    main()
