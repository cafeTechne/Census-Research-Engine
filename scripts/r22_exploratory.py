# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 22 planned exploratory X3–X5, on hash-checked registered study inputs.

Usage: .venv/bin/python scripts/r22_exploratory.py [studies_output/r22]
X1 and X2 are separate exploratory manifest runs. No confirmatory output is changed.
"""
import hashlib
import json
import math
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from census import spatial, workflows_geo
from census.manifest import manifest_hash, run_variant


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def clean(value):
    if isinstance(value,dict):
        return {str(k):clean(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):
        return [clean(v) for v in value]
    if isinstance(value,np.ndarray):
        return clean(value.tolist())
    if isinstance(value,np.generic):
        return clean(value.item())
    if isinstance(value,float) and not math.isfinite(value):
        return None
    return value


def bundle_summary(folder):
    run=json.loads((folder/'bundle/results/run.json').read_text())
    hypotheses=json.loads((folder/'bundle/results/hypotheses.json').read_text())
    result={'analysis_status':run['analysis_status'],'manifest_hash':run['manifest_hash'],
            'n_units':run['n_units'],'deviations':run['deviations'],'hypotheses':hypotheses['rows'],
            'analysed_data':{k:v['sha256'] for k,v in run.get('analysed_data',{}).items()},'models':{}}
    for aid in ('m1','m2'):
        file=folder/f'bundle/results/{aid}.json'
        if file.exists():
            model=json.loads(file.read_text())
            result['models'][aid]={k:model[k] for k in ('n_obs','formula','coefficients','diagnostics')}
    return result


def main(folder='studies_output/r22'):
    folder=Path(folder)
    run_dir=folder/'confirmatory'
    out=folder/'exploratory'
    out.mkdir(parents=True,exist_ok=True)
    m=json.loads((run_dir/'manifest.json').read_text())
    run=json.loads((run_dir/'bundle/results/run.json').read_text())
    h=manifest_hash(m)
    if h!=run['manifest_hash']:
        raise ValueError('registered manifest hash mismatch')
    data={}
    for name,info in run['analysed_data'].items():
        path=run_dir/info['path']
        if digest(path)!=info['sha256']:
            raise ValueError(f'analysed {name} hash mismatch')
        data[name]=pd.read_parquet(path) if path.suffix=='.parquet' else pd.read_csv(path,dtype={'GEOID':str})
    frame=data['analysis_frame']
    summary={'analysis_status':'exploratory','related_manifest_hash':h,
             'note':'X1–X5 are exploratory; spatial HAC failed validation and is not validated.',
             'confirmatory':bundle_summary(run_dir),'X3':[]}
    for label in ('x1_without_nyc','x2_race_composition'):
        try:
            summary[label]=bundle_summary(folder/label)
        except FileNotFoundError as exc:
            summary[label]={'error':str(exc),'analysis_status':'exploratory'}
    for aid in ('m1','m2'):
        for cutoff in (50,100,200):
            try:
                result=run_variant(run_dir,aid,args={'spatial_se':{'cutoff_km':cutoff}},
                                   out_dir=out/'spatial',label=f'{cutoff}km')
                summary['X3'].append({'analysis':aid,'cutoff_km':cutoff,'validation_status':'not validated',
                                      'units':result['units'],'result':result['result']})
            except (OSError,ValueError,RuntimeError) as exc:
                summary['X3'].append({'analysis':aid,'cutoff_km':cutoff,'error':str(exc),'validation_status':'not validated'})
    a=next(a for a in m['analyses'] if a['id']=='m2')
    formula='lbw_numerator ~ '+a['formula'].split('~',1)[1]
    poisson=run_variant(run_dir,'m2',formula=formula,args={'model':'poisson','trials':None,
                        'exposure':'lbw_denominator','scale':'X2'},out_dir=out,label='poisson')
    summary['X5']={'analysis_status':'exploratory','units':poisson['units'],'result':poisson['result']}
    # Reconstruct m2 response residuals from the saved full-sample coefficients.
    import patsy
    model=json.loads((run_dir/'bundle/results/m2.json').read_text())
    required=['lbw','lbw_denominator','pov_rate','pct_bachelors','no_vehicle','cost_burden']
    cc=frame.dropna(subset=required).reset_index(drop=True)
    X=patsy.dmatrix(a['formula'].split('~',1)[1],cc,return_type='dataframe')
    params={r['term']:r['estimate'] for r in model['coefficients']}
    eta=X.to_numpy()@np.array([params[c] for c in X.columns])
    residuals=cc[['GEOID']].assign(resid_m2=cc.lbw.to_numpy()-1/(1+np.exp(-eta)))
    residual_path=out/'resid_m2.csv';residuals.to_csv(residual_path,index=False)
    mapped=workflows_geo.make_map(str(residual_path),'resid_m2','county',2022,scheme='diverging',k=6,
                    output_dir=str(out/'figures/resid_m2'),label='Low birth weight minus fitted probability (m2)',
                    data_source=f'Exploratory; CHR&R 2025 natality 2017–2023; ACS 2018–2022; manifest {h[:12]}')
    summary['X4_map']={k:mapped.get(k) for k in ('success','paths','error')}
    gdf=workflows_geo._with_boundaries(residuals,'county',2022)
    weights=spatial.spatial_weights(gdf,'queen')
    moran=spatial.morans_i(gdf,'resid_m2',weights,permutations=999,seed=20261122)
    summary['X4_moran']=moran.__dict__
    summary['X4_residuals']={'kind':'response residuals, observed minus fitted probability','n':len(residuals),
                              'sha256':digest(residual_path),'permutations':999,'seed':20261122}
    summary['descriptives']=frame[required].describe().to_dict()
    summary['external']=run.get('external')
    docs=ROOT/'docs/studies/r22';docs.mkdir(parents=True,exist_ok=True)
    figures=[]
    for source in sorted((out/'figures').rglob('*')):
        if source.is_file():
            target=docs/source.relative_to(out/'figures')
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,target)
            figures.append({'path':str(target.relative_to(ROOT)),'sha256':digest(target)})
    summary['figures']=figures
    payload=clean(summary)
    # Required literal key scan before publishing any generated study artifact.
    from dotenv import dotenv_values
    key=dotenv_values(ROOT/'.env').get('CENSUS_API_KEY')
    text=json.dumps(payload,indent=2,ensure_ascii=False,allow_nan=False)+'\n'
    hits=text.count(key) if key else 0
    hits+=sum(p.read_bytes().count(key.encode()) for p in docs.rglob('*') if p.is_file()) if key else 0
    if hits:
        raise ValueError('configured API key found in generated study artifacts')
    (out/'exploratory_summary.json').write_text(text)
    (docs/'exploratory_summary.json').write_text(text)
    print('summary SHA-256',digest(docs/'exploratory_summary.json'))
    print('API key occurrences in generated study artifacts:',hits)
    print('Moran I',moran.I,'p_sim',moran.p_sim)


if __name__=='__main__':
    main(*sys.argv[1:2])
