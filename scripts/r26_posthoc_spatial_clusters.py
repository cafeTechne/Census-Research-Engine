# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cache-only Round 26 post hoc report; original registered outputs are read-only.

The owner retained the IM/ACS restriction and authorized an additional R21b OLS
sensitivity alongside unchanged EIV results. OLS retains ACS replicates and uses
conservative combined SEs; it is not an IM spatial re-check or EIV correction.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import patsy
from scipy.special import expit
from census import spatial
from census.boundaries import get_boundaries, boundary_vintage
from census.manifest import run_variant, manifest_hash, label_exploratory
from census.manifest.run import _statistic, _one_sided
from census.models import fit_replicate
from census.multitest import adjust_pvalues
from census.spatial_clusters import DEFAULT_SPATIAL_CLUSTERS, spatial_clusters
from census import __version__

SOURCES={'r21b':'r21b_mi_ny_county_premature_mortality.json',
         'r22':'r22_mi_ny_county_low_birth_weight.json'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_bundle_assets(folder):
    """Check the original results used for comparison, not only analysed inputs."""
    bundle = folder/'bundle'
    inventory = json.loads((bundle/'bundle.json').read_text())['files']
    hashes = {}
    for rel in ('results/run.json', 'results/m2.json', 'tables/hypotheses.csv'):
        path = bundle/rel
        if not path.is_file():
            raise FileNotFoundError('Missing cached result: '+str(path))
        expected = inventory.get(rel)
        if expected is None or digest(path) != expected:
            raise ValueError('Cached result SHA-256 mismatch: '+str(path))
        hashes[path] = expected
    return hashes


def load_verified(folder, manifest_name):
    m=json.loads((folder/'manifest.json').read_text())
    info=json.loads((folder/'bundle/results/run.json').read_text())
    registered=json.loads((ROOT/'examples/manifests'/manifest_name).read_text())
    if manifest_hash(m)!=info['manifest_hash'] or manifest_hash(m)!=manifest_hash(registered):
        raise ValueError('cached manifest differs from registered example: '+manifest_name)
    data={};hashes=verify_bundle_assets(folder)
    for name,record in info['analysed_data'].items():
        p=folder/record['path']
        if not p.is_file():raise FileNotFoundError('Missing cached analysed file: '+str(p))
        if digest(p)!=record['sha256']:raise ValueError('Cached file SHA-256 mismatch: '+str(p))
        data[name]=pd.read_parquet(p) if p.suffix=='.parquet' else pd.read_csv(p,dtype={'GEOID':str})
        data[name]['GEOID']=data[name].GEOID.astype(str);hashes[p]=record['sha256']
    return m,info,data,hashes


def boundaries(frame, year):
    import geopandas as gpd
    parts=[get_boundaries('county',boundary_vintage(year,'county'),state)
           for state in sorted(set(frame.GEOID.str[:2]))]
    return gpd.GeoDataFrame(pd.concat(parts,ignore_index=True),geometry='geometry',crs=parts[0].crs)


def residual_moran(folder,m,frame,boundary):
    a=next(a for a in m['analyses'] if a['id']=='m2')
    saved=json.loads((folder/'bundle/results/m2.json').read_text())
    y,X=patsy.dmatrices(a['formula'],frame,return_type='dataframe')
    params={r['term']:r['estimate'] for r in saved['coefficients']}
    eta=X.to_numpy()@np.array([params[c] for c in X.columns])
    fitted=expit(eta) if (a.get('args') or {}).get('model')=='binomial' else eta
    residual=frame.loc[X.index,['GEOID']].assign(residual=y.iloc[:,0].to_numpy()-fitted)
    gdf=boundary.merge(residual,on='GEOID',how='inner').sort_values('GEOID').reset_index(drop=True)
    if len(gdf)!=len(residual):raise ValueError('Cached boundaries do not cover residual units exactly')
    w=spatial.spatial_weights(gdf,'queen',cache=False)
    result=spatial.morans_i(gdf,'residual',w,permutations=999,seed=20261126)
    return {'I':float(result.I),'p_sim':float(result.p_sim),'n':len(gdf),'permutations':999,
            'seed':20261126,'weights':'queen, row standardized','basis':'unchanged registered m2 response residuals'}


def ols_sensitivity(m,data,out):
    """Authorized estimator sensitivity; retain available ACS inputs/replicates."""
    models={};frame=data['analysis_frame'];reps=data.get('replicates')
    if reps is None:raise ValueError('OLS sensitivity requires the cached ACS replicate file')
    for a in m['analyses']:
        outcome=a['formula'].split('~',1)[0].strip()
        model=fit_replicate(a['formula'],frame,replicates=reps,model='ols',target='conservative',
                            replicate_policy='strict',fixed_variables=(outcome,),
                            confidence_level=float(m.get('confidence_level',.90)))
        label_exploratory(model,'Post hoc OLS sensitivity, not EIV; retains ACS replicates and uses conservative combined SEs. No spatial correction.',manifest_hash(m))
        model.provenance.update(registered_method=a['method'],sensitivity_method='OLS',spatial_correction=False)
        models[a['id']]=model
        (out/f"ols_{a['id']}.json").write_text(json.dumps(model.to_dict(),indent=2,allow_nan=False)+'\n')
    rows=[]
    for h in m['hypotheses']:
        z=_statistic(h,models[h['analysis']])
        rows.append({'id':h['id'],'analysis':h['analysis'],'term':h['term'],
                     'p_value':_one_sided(z['p_two_sided'],z['estimate'],h.get('direction','two-sided')),
                     'estimate':z['estimate'],'family':h.get('family','primary')})
    table=pd.DataFrame(rows)
    groups=[table.index] if (m.get('correction') or {}).get('family','all')=='all' else [g.index for _,g in table.groupby('family')]
    table['p_adjusted']=np.nan
    for idx in groups:table.loc[idx,'p_adjusted']=adjust_pvalues(table.loc[idx,'p_value'].to_numpy(float),(m.get('correction') or {}).get('method','holm'))
    table.to_csv(out/'ols_hypotheses.csv',index=False)
    return table


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--studies-root',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,default=ROOT/'studies_output/r26')
    args=parser.parse_args();out=args.output_dir.resolve()
    if out.exists() and any(out.iterdir()):raise FileExistsError('Use a new output directory; previous post hoc outputs are preserved')
    cached={};all_hashes={}
    with patch('requests.sessions.Session.request',side_effect=RuntimeError('Round 26 cache-only; no downloads')):
        # Check all caches and boundary vintages before computing any new sensitivity.
        for study,name in SOURCES.items():
            folder=args.studies_root/study/'confirmatory'
            if out.is_relative_to(folder.resolve()):raise ValueError('Output must be separate from the registered run')
            m,info,data,hashes=load_verified(folder,name);all_hashes.update(hashes)
            b=boundaries(data['analysis_frame'],max(m['releases']))
            cached[study]=(folder,m,info,data,b)
        out.mkdir(parents=True,exist_ok=True)
        summary={'analysis_status':'exploratory','review':'author self-review, not independent',
                 'default':DEFAULT_SPATIAL_CLUSTERS,'engine_base_version':__version__,
                 'engine_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                 'script_sha256':digest(__file__),'studies':{}}
        lines=['# Round 26 post hoc spatial-cluster re-checks','',
               '**Post hoc; author self-review, not independent. Registered results are unchanged.**','',
               'Only IM with eight clusters passed the fixed validation (coverage 0.886–0.912). '
               'IM requires population-only inference and refuses analysed inputs with ACS replicates. '
               'Both registered studies have those replicates; Round 21b also uses EIV, outside the validated model families. '
               '**The requested IM comparisons are unavailable under the retained protocol. No clustered p-values or claims that hypotheses still hold are manufactured.**','']
        ols=None
        for study,(folder,m,info,data,boundary) in cached.items():
            part=out/study;part.mkdir()
            attempts={}
            for a in m['analyses']:
                try:
                    v=run_variant(folder,a['id'],args={'spatial_clusters':dict(DEFAULT_SPATIAL_CLUSTERS),'target':'population'},
                                  out_dir=part/'variants',label='im8_posthoc')
                except (TypeError,ValueError) as exc:
                    attempts[a['id']]={'status':'unavailable','error_type':type(exc).__name__,'detail':str(exc)}
                else:
                    raise RuntimeError('An IM refit unexpectedly bypassed the registered-study restrictions')
            old=pd.read_csv(folder/'bundle/tables/hypotheses.csv')
            moran=residual_moran(folder,m,data['analysis_frame'],boundary)
            if study=='r21b':ols=ols_sensitivity(m,data,part)
            summary['studies'][study]={'manifest_hash':info['manifest_hash'],'im_attempts':attempts,
                                       'registered_m2_residual_moran':moran,'original_hypotheses':old.to_dict(orient='records')}
            if study=='r21b':summary['studies'][study]['ols_sensitivity']=ols.to_dict(orient='records')
            lines += [f'## {study.upper()}', '',
                      f"Registered m2 residual Moran's I: **{moran['I']:.6f}**, permutation p={moran['p_sim']:.4f}, "
                      f"n={moran['n']}; queen contiguity, row standardized, 999 permutations (seed 20261126).",'',
                      '| Hypothesis | Registered Holm p | IM-8 Holm p | Still holds under IM? |',
                      '|:---|---:|:---|:---|']
            for h in m['hypotheses']:
                row=old.loc[old.id==h['id']].iloc[0]
                lines.append(f"| {h['id']} ({h['analysis']}: {h['term']}) | {float(row.p_adjusted):.6g} | unavailable | not assessed |")
            lines+=['','Reason: '+('the registered method is EIV, and analysed inputs have ACS replicates.' if study=='r21b'
                                   else 'analysed inputs have ACS replicates; the IM population-only procedure cannot incorporate them.'),'']
            if study=='r22':
                lines+=['The registered R22 p-values above retain the original Pearson X2 inference. '
                        'That convention subsequently failed overdispersion validation; this comparison '
                        'does not endorse it. The separate robust-SE sensitivities remain documented in '
                        '`r22_mi_ny_county_low_birth_weight.md`.','']
        lines+=['## Additional authorized OLS sensitivity for Round 21b','',
                '**Exploratory, unclustered OLS; not an EIV correction and not a substitute for the unavailable IM re-check.** '
                'This uses the exact cached formulas and complete cases, keeps the external outcome fixed during ACS covariate refits, '
                'and retains all cached ACS replicates with conservative combined SEs. Holm adjustment uses the original hypothesis family. '
                'Measurement-error bias and residual spatial dependence remain. The original EIV outputs are unchanged.','',
                '| Hypothesis | Registered EIV Holm p | OLS conservative/ACS Holm p |',
                '|:---|---:|---:|']
        old=pd.read_csv(cached['r21b'][0]/'bundle/tables/hypotheses.csv')
        for row in ols.itertuples():
            original=float(old.loc[old.id==row.id,'p_adjusted'].iloc[0])
            lines.append(f'| {row.id} ({row.analysis}: {row.term}) | {original:.6g} | {row.p_adjusted:.6g} |')
        # Validation geometry, not a claim that IM was applied to the registered studies.
        ids=sorted(g for state in ('26','36') for g in get_boundaries('county',2020,state).GEOID.astype(str))
        assignment=spatial_clusters(ids,'county',2020,8)
        assignment.to_csv(out/'im8_validation_assignment.csv',index=False)
        import geopandas as gpd
        geo=gpd.GeoDataFrame(pd.concat([get_boundaries('county',2020,st) for st in ('26','36')],ignore_index=True),
                             geometry='geometry',crs='EPSG:4269').merge(assignment[['GEOID','cluster']],on='GEOID').to_crs(5070)
        fig,ax=plt.subplots(figsize=(8,5));geo.plot(column='cluster',categorical=True,cmap='tab10',ax=ax,legend=True,edgecolor='white',linewidth=.2)
        ax.set_title('IM-8 validation reference assignment (2020 cached geography)');ax.set_axis_off();fig.tight_layout()
        fig.savefig(out/'im8_cluster_map.png',dpi=200);fig.savefig(out/'im8_cluster_map.pdf');plt.close(fig)
        summary['assignment_scope']='2020 validation geography; neither registered study was refitted with IM'
        lines+=['','## Scope and artifacts','',
                'The cluster map is a release attachment (`im8_cluster_map.png` / `.pdf`), showing the frozen validation geometry; '
                'it does not imply an IM estimate was available for either registered study. '
                'The map and computed outputs are in `/tmp/round26-study-outputs.tar.gz`, not committed datasets.',
                'No sources were downloaded. Cached analysed-file SHA-256 values and registered manifest hashes were checked; '
                'original files were not modified. Supporting an ACS-compatible spatial re-check or EIV/Poisson inference requires separate validation.','']
        for path,expected in all_hashes.items():
            if digest(path)!=expected:raise RuntimeError('Original cached input changed during post hoc work')
        (out/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
        (out/'report.md').write_text('\n'.join(lines))
        (ROOT/'docs/studies/r26_posthoc_spatial_clusters.md').write_text('\n'.join(lines))
    print('Cache-only report complete; IM re-checks correctly unavailable, OLS/ACS sensitivity retained.')
    for study,values in summary['studies'].items():print(study,'Moran I',values['registered_m2_residual_moran']['I'])

if __name__=='__main__':main()
