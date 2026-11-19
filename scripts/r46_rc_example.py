# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 46 exploratory example (author self-review, not independent; not a registered study).

    python scripts/r46_rc_example.py R29_ARCHIVE OUT_DIR

Round 29 mortality H1-H3: naive NB2-HC3 slope on poverty vs regression calibration of poverty's ACS
sampling error (NB2), MI/NY and OH/PA. Coefficients only; WONDER disclosure audit must pass.
"""
import json
import sys
import warnings
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'scripts'))
from census.count_models import fit_count_model
from census.models import regression_calibration
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
         TemporaryDirectory(prefix='r46-input-') as scratch:
        folders = extract(archive, scratch)
        for key, (name, code, label) in REGIONS.items():
            m, run, data, _ = load_verified(folders[key], name)
            frame = restore_snapshot(data['analysis_frame'], list(HYPS))
            res = dict(region=label, reliability_poverty=None, hypotheses={})
            v = frame['poverty'].var(); e = (frame['poverty_se']**2).mean()
            res['reliability_poverty'] = float((v-e)/v)
            for a in [a for a in m['analyses'] if a['id'] in HYPS]:
                E = a['args']['exposure']
                nb = fit_count_model(a['formula'], frame, E)['table'].set_index('term').loc['poverty']
                rc = regression_calibration(a['formula'], frame, ['poverty'], model='negbin', exposure=E, seed=46)
                r = rc.coefficients.set_index('term').loc['poverty']
                res['hypotheses'][a['id']] = dict(
                    naive_nb2=dict(estimate=float(nb.estimate), lower=float(nb.lower), upper=float(nb.upper)),
                    calibrated_nb2=dict(estimate=float(r.estimate), lower=float(r.ci_lower), upper=float(r.ci_upper)))
            part = out/key; part.mkdir(parents=True)
            (part/'r46_example.json').write_text(json.dumps(res, indent=2, allow_nan=False)+'\n')
            audit = audit_outputs(part, run['wonder_output_policy'])
            if not audit['passed']:
                raise ValueError('WONDER disclosure audit failed')
            res['wonder_disclosure'] = audit; summary['regions'][key] = res
    (out/'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False)+'\n')
    for k, r in summary['regions'].items():
        print(k, 'poverty reliability %.3f' % r['reliability_poverty'])
        for h, x in r['hypotheses'].items():
            print(' ', h, ' '.join(f"{t} {y['estimate']:.4f} ({y['lower']:.4f}, {y['upper']:.4f})" for t, y in x.items()))


if __name__ == '__main__':
    main()
