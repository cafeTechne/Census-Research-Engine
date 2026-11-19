# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 44 post hoc (author self-review, not independent): Round 29 H1-H3 under NB2-HC3.

    python scripts/r44_posthoc_r29.py R29_ARCHIVE OUT_DIR

P0 Poisson HC3 (population target; comparison), P1 NB2-HC3 (population target; validated in Round 39),
P2 H2 interval-censored Poisson (suppressed counties as counts in [1, 9]; exploratory, Round 42).
Registered results are read from the verified bundles and are not changed. Network is blocked. Outputs
are coefficients only and must pass census.wonder_outputs.audit_outputs.
"""
import hashlib
import json
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
import patsy
import statsmodels.api as sm
from scipy import stats

from census.manifest.methods import _negbin_result
from census.manifest.run import _one_sided
from census.missing_censored_its import fit_censored_poisson
from census.models import fit_replicate
from census.multitest import adjust_pvalues
from census.wonder_outputs import audit_outputs, restore_snapshot
from r30_posthoc_im_acs import load_verified

REGIONS = {'mi_ny': ('r29_mi_ny_mortality_smr.json', '36', 'NY'), 'oh_pa': ('r29_oh_pa_replication.json', '42', 'PA')}
HYPS = ('h1', 'h2', 'h3')
LEVEL = .90


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def extract(archive, dest):
    with tarfile.open(archive) as tar:
        members = [m for m in tar.getmembers() if m.name.startswith(('r29/mi_ny/confirmatory/', 'r29/oh_pa/confirmatory/'))]
        for m in members:
            p = Path(m.name)
            if not m.isfile() or p.is_absolute() or '..' in p.parts:
                raise ValueError('unsafe archive member')
        tar.extractall(dest, members=members, filter='data')
    return {r: Path(dest)/'r29'/r/'confirmatory' for r in REGIONS}


def row(est, se, direction='greater'):
    p2 = float(2*stats.norm.sf(abs(est/se)))
    z = stats.norm.ppf((1+LEVEL)/2)
    return dict(estimate=float(est), se=float(se), ci_lower=float(est-z*se), ci_upper=float(est+z*se),
                p_one_sided=float(_one_sided(p2, est, direction)))


def nb_alpha(formula, frame, exposure):
    data = frame.dropna(subset=[exposure]).copy()
    y, X = patsy.dmatrices(formula, data, return_type='dataframe', NA_action='drop')
    nb = sm.NegativeBinomial(y, X, exposure=data.loc[X.index, exposure].to_numpy(float)).fit(disp=0, maxiter=200)
    return float(np.asarray(nb.params)[-1])


def region(folder, manifest_name, code, label):
    m, run, data, hashes = load_verified(folder, manifest_name)
    raw = data['analysis_frame']
    frame = restore_snapshot(raw, list(HYPS))
    registered = pd.read_csv(folder/'bundle/tables/hypotheses.csv')
    analyses = {a['id']: a for a in m['analyses']}
    out = {'P0': [], 'P1': []}
    for h in m['hypotheses']:
        a = analyses[h['analysis']]; f = a['formula']; E = a['args']['exposure']
        p0 = fit_replicate(f, frame, model='poisson', exposure=E, scale='robust', target='population', confidence_level=LEVEL)
        r0 = p0.coefficients.set_index('term').loc[h['term']]
        out['P0'].append(dict(id=h['id'], n=int(p0.n_obs), **row(r0.estimate, r0.se_model, h['direction'])))
        p1 = _negbin_result(f, frame, E, LEVEL)
        r1 = p1.coefficients.set_index('term').loc[h['term']]
        out['P1'].append(dict(id=h['id'], n=int(p1.n_obs), alpha=nb_alpha(f, frame, E), **row(r1.estimate, r1.se_model, h['direction'])))
    for key in out:
        adj = adjust_pvalues([r['p_one_sided'] for r in out[key]], m['correction']['method'])
        for r, p in zip(out[key], adj):
            r.update(p_holm=float(p), holds=bool(p < 1-LEVEL))
    reg = {r.id: dict(estimate=float(r.estimate), se=float(r.se), p_holm=float(r.p_adjusted), holds=bool(r.significant))
           for r in registered.itertuples()}
    f2 = frame.copy()
    f2['hidden'] = raw['h2_numerator'].astype(str).eq('suppressed').to_numpy()
    f2['state2'] = f2.GEOID.astype(str).str.startswith(code).astype(float)
    c = fit_censored_poisson(f2, 'h2_numerator', 'hidden', 'E_h2', ['poverty', 'state2'])
    t = c['table'].set_index('term').loc['poverty']
    p2 = dict(id='H2', n=int(c['n']), n_hidden=int(c['n_censored']), validated=False, **row(t.estimate, t.se))
    reading = {h['id']: ('holds' if reg[h['id']]['holds'] and nb['holds'] else
                         'sensitive to overdispersion' if reg[h['id']]['holds'] else
                         'not supported as registered' + (' (holds under NB2)' if nb['holds'] else ''))
               for h, nb in zip(m['hypotheses'], out['P1'])}
    return dict(region=label, manifest_hash=run['manifest_hash'], registered=reg, P0=out['P0'], P1=out['P1'], P2=p2,
                reading=reading, input_sha256={str(Path(k).relative_to(folder)): v for k, v in hashes.items()}), run


def main():
    archive, out = Path(sys.argv[1]), Path(sys.argv[2]).resolve()
    if out.exists():
        raise SystemExit('use a fresh output directory')
    warnings.simplefilter('ignore')
    sha = digest(archive)
    with patch('requests.sessions.Session.request', side_effect=RuntimeError('Round 44: HTTP blocked')), \
         patch('urllib.request.urlopen', side_effect=RuntimeError('Round 44: HTTP blocked')), \
         TemporaryDirectory(prefix='r44-input-') as scratch:
        folders = extract(archive, scratch)
        summary = dict(review='author self-review, not independent', status='post hoc; registered results unchanged',
                       r29_archive_sha256=sha, regions={})
        for key, (name, code, label) in REGIONS.items():
            res, run = region(folders[key], name, code, label)
            part = out/key; part.mkdir(parents=True)
            (part/'r44_posthoc.json').write_text(json.dumps(res, indent=2, allow_nan=False)+'\n')
            audit = audit_outputs(part, run['wonder_output_policy'])
            if audit.get('failures'):
                raise ValueError(f'WONDER disclosure audit failed for {key}')
            res['wonder_disclosure'] = audit
            summary['regions'][key] = res
        (out/'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False)+'\n')
    if digest(archive) != sha:
        raise ValueError('R29 archive changed during the run')
    print(json.dumps({k: v['reading'] for k, v in summary['regions'].items()}, indent=1))


if __name__ == '__main__':
    main()
