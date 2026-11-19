# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 45 exploratory example (author self-review, not independent; not a registered study).

    python scripts/r45_count_example.py R29_ARCHIVE OUT_DIR

Round 29 county mortality: (1) H2 (drug overdose) with suppressed counties as counts in [1, 9] under the
validated interval-censored NB2; (2) H1-H3 slopes under IM-8 NB2 (MI/NY: the validated geometry; OH/PA:
state-respecting clusters, exploratory). Coefficients only; WONDER disclosure audit must pass.
"""
import json
import sys
import warnings
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'scripts'))
import pandas as pd

from census.count_models import fit_count_model
from census.missing_censored_its import fit_censored_negbin, fit_censored_poisson
from census.wonder_outputs import audit_outputs, restore_snapshot
from r30_posthoc_im_acs import load_verified
from r44_posthoc_r29 import REGIONS, HYPS, extract, digest

GEOM = {'mi_ny': 'docs/audits/im_acs_beta_star.json', 'oh_pa': 'docs/audits/ohpa_geometry.json'}


def main():
    archive, out = Path(sys.argv[1]), Path(sys.argv[2]).resolve()
    if out.exists():
        raise SystemExit('use a fresh output directory')
    warnings.simplefilter('ignore')
    sha = digest(archive); summary = dict(status='exploratory example; author self-review, not independent',
                                          r29_archive_sha256=sha, regions={})
    with patch('requests.sessions.Session.request', side_effect=RuntimeError('HTTP blocked')), \
         TemporaryDirectory(prefix='r45-input-') as scratch:
        folders = extract(archive, scratch)
        for key, (name, code, label) in REGIONS.items():
            m, run, data, _ = load_verified(folders[key], name)
            raw = data['analysis_frame']; frame = restore_snapshot(raw, list(HYPS))
            coords = pd.DataFrame(json.loads((ROOT/GEOM[key]).read_text())['coordinates'])
            f2 = frame.assign(hidden=raw['h2_numerator'].astype(str).eq('suppressed').to_numpy(),
                              state2=frame.GEOID.astype(str).str.startswith(code).astype(float))
            res = dict(region=label)
            for tag, fn in (('censored_nb2', fit_censored_negbin), ('censored_poisson', fit_censored_poisson)):
                t = fn(f2, 'h2_numerator', 'hidden', 'E_h2', ['poverty', 'state2'])['table'].set_index('term').loc['poverty']
                res[tag] = dict(estimate=float(t.estimate), se=float(t.se), lower=float(t.lower), upper=float(t.upper))
            res['n_hidden'] = int(f2.hidden.sum())
            im = {}
            for a in [a for a in m['analyses'] if a['id'] in HYPS]:
                o = fit_count_model(a['formula'], frame, a['args']['exposure'], 'negbin', spatial='clusters', coords=coords,
                                    within_states=(key == 'oh_pa'))
                t = o['table'].set_index('term').loc['poverty']
                im[a['id']] = dict(estimate=float(t.estimate), se=float(t.se), lower=float(t.lower), upper=float(t.upper),
                                   notes=[n for n in o['notes'] if 'outside' in n or 'CROSS' in n])
            res['im8_negbin'] = im
            part = out/key; part.mkdir(parents=True)
            (part/'r45_example.json').write_text(json.dumps(res, indent=2, allow_nan=False)+'\n')
            audit = audit_outputs(part, run['wonder_output_policy'])
            if not audit['passed']:
                raise ValueError('WONDER disclosure audit failed')
            res['wonder_disclosure'] = audit; summary['regions'][key] = res
    (out/'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != 'wonder_disclosure'} for k, v in summary['regions'].items()}, indent=1))


if __name__ == '__main__':
    main()
