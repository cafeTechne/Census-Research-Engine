# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 48 exploratory example (author self-review, not independent; not a registered study).

    CENSUS_GEO_DIR=<cached boundaries> python scripts/r48_spatial_example.py R29_ARCHIVE OUT_DIR

Round 29 counties (MI/NY and OH/PA): Spearman correlations of poverty with the log SMRs (H1-H3; counties
with hidden or zero counts dropped per pair), with the Round 33 interval (independent areas) and the
Round 48 effective-sample-size interval (cached county boundaries); plus Feldt alpha of the three log SMRs
both ways. Coefficients only; WONDER disclosure audit must pass. No network access.
"""
import json
import sys
import warnings
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'scripts'))
import numpy as np
from census.composite_index import build_index
from census.correlation import validated_correlations
from census.small_spatial import frame_coordinates
from census.wonder_outputs import audit_outputs, restore_snapshot
from r30_posthoc_im_acs import load_verified
from r44_posthoc_r29 import REGIONS, HYPS, extract, digest


def main():
    archive, out = Path(sys.argv[1]), Path(sys.argv[2]).resolve()
    if out.exists():
        raise SystemExit('use a fresh output directory')
    warnings.simplefilter('ignore')
    summary = dict(status='exploratory example; author self-review, not independent', r29_archive_sha256=digest(archive), regions={})
    with patch('requests.sessions.Session.request', side_effect=RuntimeError('HTTP blocked')), \
         TemporaryDirectory(prefix='r48-input-') as scratch:
        folders = extract(archive, scratch)
        for key, (name, _, _) in REGIONS.items():
            m, run, data, _ = load_verified(folders[key], name)
            f = restore_snapshot(data['analysis_frame'], list(HYPS))
            for h in HYPS:
                ok = (f[f'{h}_numerator'] > 0) & (f[f'E_{h}'] > 0)
                f[f'log_smr_{h}'] = np.where(ok, np.log(f[f'{h}_numerator'].where(ok)/f[f'E_{h}'].where(ok)), np.nan)
            coords = frame_coordinates(f, 2022)
            res = dict(n_counties=len(f), correlations={}, alpha={})
            for h in HYPS:
                cols = ['poverty', f'log_smr_{h}']
                plain = validated_correlations(f, cols, 'spearman').iloc[0]
                spat = validated_correlations(f, cols, 'spearman', coords=coords).iloc[0]
                res['correlations'][h] = dict(n=int(plain.n), estimate=float(plain.estimate),
                                              independent=(float(plain.ci_lower), float(plain.ci_upper)),
                                              spatial=(float(spat.ci_lower), float(spat.ci_upper)), n_eff=float(spat.n_eff))
            smr = [f'log_smr_{h}' for h in HYPS]
            for label, c in (('independent', None), ('spatial', coords)):
                a = build_index(f, smr, coords=c)['cronbach_alpha']
                res['alpha'][label] = {k: a[k] for k in ('estimate', 'lower', 'upper')} | ({'n_eff': a['n_eff']} if 'n_eff' in a else {})
            part = out/key; part.mkdir(parents=True)
            (part/'r48_example.json').write_text(json.dumps(res, indent=2, allow_nan=False)+'\n')
            audit = audit_outputs(part, run['wonder_output_policy'])
            if not audit['passed']:
                raise ValueError('WONDER disclosure audit failed')
            res['wonder_disclosure'] = audit; summary['regions'][key] = res
    (out/'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False)+'\n')
    for k, r in summary['regions'].items():
        print(k, r['n_counties'])
        for h, c in r['correlations'].items():
            print(' ', h, 'n', c['n'], 'rho %.3f' % c['estimate'], 'indep (%.3f, %.3f)' % c['independent'],
                  'spatial (%.3f, %.3f)' % c['spatial'], 'n_eff %.1f' % c['n_eff'])
        print('  alpha', r['alpha'])


if __name__ == '__main__':
    main()
