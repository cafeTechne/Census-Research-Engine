# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 35 post hoc: R21b H1-H4 with corrected spatial EIV (G1, G2). Cached inputs only.

Post hoc; author self-review, not independent. Registered results are unchanged.
Usage: scripts/r35_posthoc_spatial_eiv.py STUDIES_ROOT OUT_DIR
"""
import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'scripts'))
import numpy as np
import pandas as pd

from census.multitest import adjust_pvalues
from census.spatial_eiv import fit_spatial_eiv
from r30_posthoc_im_acs import load_verified


def main(studies_root, out_dir):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=False)
    m, run, data, hashes = load_verified(Path(studies_root)/'r21b/confirmatory', 'r21b_mi_ny_county_premature_mortality.json')
    frame, reps = data['analysis_frame'], data['replicates']
    frame['GEOID'] = frame['GEOID'].astype(str)
    geo = json.loads((ROOT/'docs/audits/im_acs_beta_star.json').read_text())['coordinates']
    coords = pd.DataFrame({'GEOID': geo['GEOID'], 'lon': geo['lon'], 'lat': geo['lat']})
    registered = pd.read_csv(Path(studies_root)/'r21b/confirmatory/bundle/tables/hypotheses.csv')
    fits, rows = {}, []
    with patch('requests.sessions.Session.request', side_effect=RuntimeError('post hoc: HTTP blocked')):
        for method in ('g1', 'g2'):
            for a in m['analyses']:
                outcome = a['formula'].split('~', 1)[0].strip()
                fits[(method, a['id'])] = fit_spatial_eiv(a['formula'], frame, reps, method=method, coords=coords,
                                                          fixed_variables=(outcome,))
            ps = []
            for h in m['hypotheses']:
                t = fits[(method, h['analysis'])]['table'].set_index('term').loc[h['term']]
                from scipy import stats
                p_one = float(stats.t.sf(t.estimate/t.se, t.df)) if h.get('direction') == 'greater' else float(t.p_value)
                ps.append(p_one)
                rows.append(dict(method=method, id=h['id'], term=h['term'], estimate=float(t.estimate), se=float(t.se),
                                 ci_lower=float(t.ci_lower), ci_upper=float(t.ci_upper), p_one_sided=p_one,
                                 validated=fits[(method, h['analysis'])]['validated']))
            adj = adjust_pvalues(ps, 'holm')
            for r, p in zip([r for r in rows if r['method'] == method], adj):
                r['p_holm'] = float(p); r['still_holds'] = bool(p < .10)
    table = pd.DataFrame(rows).merge(registered[['id', 'p_adjusted']].rename(columns={'p_adjusted': 'registered_p_holm'}), on='id')
    summary = dict(table=table.to_dict('records'), lambda_g2={a: fits[('g2', a)]['lambda'] for a in ('m1', 'm2', 'm3')},
                   source_hashes={str(k): v for k, v in hashes.items()}, notes={f'{k[0]}/{k[1]}': v['notes'] for k, v in fits.items()})
    (out/'summary.json').write_text(json.dumps(summary, indent=2, default=str)+'\n')
    print(table.to_string()); print(summary['lambda_g2'])


if __name__ == '__main__':
    main(*sys.argv[1:3])
