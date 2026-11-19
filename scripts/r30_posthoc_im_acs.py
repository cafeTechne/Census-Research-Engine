# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cache-only Round 30 re-checks. Never write registered inputs or contact WONDER.

Uses the owner's cached R21b/R22 and the local v0.26.0 R29 attachment. All source
hashes are checked before fitting and again afterwards. C2 failures stay unavailable.
"""
import argparse
import hashlib
import json
import subprocess
import sys
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import patsy
from scipy.special import expit
from census.manifest import manifest_hash
from census.manifest.run import _statistic, _one_sided
from census.models import fit_replicate
from census.multitest import adjust_pvalues
from census.spatial_clusters import IM_ACS_VALIDATED
from census.wonder_outputs import restore_snapshot, audit_outputs

MANIFESTS={'r21b':'r21b_mi_ny_county_premature_mortality.json',
           'r22':'r22_mi_ny_county_low_birth_weight.json','r29':'r29_mi_ny_mortality_smr.json'}


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path,value):
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def load_verified(folder, manifest_name):
    m=json.loads((folder/'manifest.json').read_text())
    run=json.loads((folder/'bundle/results/run.json').read_text())
    registered=json.loads((ROOT/'examples/manifests'/manifest_name).read_text())
    if manifest_hash(m)!=manifest_hash(registered) or manifest_hash(m)!=run['manifest_hash']:
        raise ValueError('cached manifest mismatch')
    inventory=json.loads((folder/'bundle/bundle.json').read_text())['files']
    hashes={folder/'manifest.json':digest(folder/'manifest.json')}
    names={h['analysis'] for h in m['hypotheses']}
    for rel in ['results/run.json','tables/hypotheses.csv']+[f'results/{a}.json' for a in sorted(names)]:
        path=folder/'bundle'/rel
        if inventory.get(rel)!=digest(path):raise ValueError('cached result checksum mismatch: '+rel)
        hashes[path]=inventory[rel]
    loaded={}
    for name,info in run['analysed_data'].items():
        path=folder/info['path']
        if digest(path)!=info['sha256']:raise ValueError('cached analysed checksum mismatch: '+name)
        hashes[path]=info['sha256']
        loaded[name]=pd.read_parquet(path) if path.suffix=='.parquet' else pd.read_csv(path,dtype={'GEOID':str})
    return m,run,loaded,hashes


def extract_r29(archive,destination):
    prefix='r29/mi_ny/confirmatory/'
    with tarfile.open(archive) as tar:
        members=[m for m in tar.getmembers() if m.name.startswith(prefix)]
        if not members:raise ValueError('R29 MI/NY cache absent from attachment')
        for member in members:
            path=Path(member.name)
            if not member.isfile() or path.is_absolute() or '..' in path.parts:
                raise ValueError('unsafe R29 archive member')
        tar.extractall(destination,members=members,filter='data')
    return destination/prefix


def residual_moran(folder,a,frame,boundary):
    from census import spatial
    y,X=patsy.dmatrices(a['formula'],frame,return_type='dataframe')
    saved=json.loads((folder/f"bundle/results/{a['id']}.json").read_text())
    coefs={r['term']:r['estimate'] for r in saved['coefficients']}
    eta=X.to_numpy()@np.array([coefs[c] for c in X.columns])
    args=a.get('args') or {};model=args.get('model','ols')
    if model=='binomial':fitted=expit(eta)
    elif model=='poisson':fitted=np.exp(eta)*frame.loc[X.index,args['exposure']].to_numpy(float)
    else:fitted=eta
    # Residuals are transient: WONDER suppressed counties have no residual and
    # neither residual vectors nor raw counts are written to any output.
    residual=frame.loc[X.index,['GEOID']].assign(residual=y.iloc[:,0].to_numpy()-fitted)
    gdf=boundary.merge(residual,on='GEOID',validate='one_to_one').sort_values('GEOID').reset_index(drop=True)
    if len(gdf)!=len(residual):raise ValueError('cached boundary coverage mismatch')
    weights=spatial.spatial_weights(gdf,'queen',cache=False)
    result=spatial.morans_i(gdf,'residual',weights,permutations=999,seed=20261201)
    return {'I':float(result.I),'p_sim':float(result.p_sim),'n':len(gdf),
            'basis':'unchanged registered reference response residuals; queen row-standardized, 999 permutations, seed 20261201'}


def evaluate(m,frame,reps,coords,out):
    models={};attempts={}
    for a in m['analyses']:
        if a['id'] not in {h['analysis'] for h in m['hypotheses']}:continue
        if a['method']=='fit_eiv':
            attempts[a['id']]={'status':'unavailable','reason':'C2 IM EIV failed fixed validation; no C1 substitution'}
            continue
        args=dict(a.get('args') or {});model=args.get('model','ols')
        if not IM_ACS_VALIDATED.get(model,False):
            attempts[a['id']]={'status':'unavailable','reason':'C1 model failed fixed validation'}
            continue
        args.pop('scale',None);args['target']='population';args['spatial_clusters']={'k':8,'method':'im'}
        outcome=a['formula'].split('~',1)[0].strip()
        try:
            result=fit_replicate(a['formula'],frame,reps,coords=coords,replicate_policy='strict',
                                 fixed_variables=(outcome,),confidence_level=m.get('confidence_level',.90),**args)
        except (ValueError,np.linalg.LinAlgError) as exc:
            attempts[a['id']]={'status':'unavailable','reason':str(exc)}
            continue
        result.provenance.update(analysis_status='exploratory',review='author self-review, not independent',
                                 registered_manifest_hash=manifest_hash(m),registered_analysis=a['id'])
        models[a['id']]=result
        write_json(out/f"im_{a['id']}.json",result.to_dict())
        attempts[a['id']]={'status':'available','cluster_terms':result.diagnostics['spatial_clusters']['cluster_terms'],
                          'cluster_estimates':result.diagnostics['spatial_clusters']['cluster_estimates'],
                          'not_estimable_terms':result.diagnostics['spatial_clusters']['not_estimable_terms']}
    rows=[]
    for h in m['hypotheses']:
        row={'id':h['id'],'analysis':h['analysis'],'term':h['term'],'p_value':None,'p_adjusted':None,'still_holds':None}
        if h['analysis'] in models:
            try:
                stat=_statistic(h,models[h['analysis']])
                row.update(estimate=stat['estimate'],p_value=_one_sided(stat['p_two_sided'],stat['estimate'],h.get('direction','two-sided')))
            except (ValueError,KeyError) as exc:row['reason']=str(exc)
        else:row['reason']=attempts[h['analysis']]['reason']
        rows.append(row)
    # An incomplete family cannot yield the requested Holm comparison without
    # inventing a missing p-value. Preserve the full registered family.
    families={r['id']:next(h.get('family','primary') for h in m['hypotheses'] if h['id']==r['id']) for r in rows}
    groups=[rows] if m.get('correction',{}).get('family','all')=='all' else [[r for r in rows if families[r['id']]==f] for f in sorted(set(families.values()))]
    for group in groups:
        if all(r['p_value'] is not None for r in group):
            adjusted=adjust_pvalues([r['p_value'] for r in group],m.get('correction',{}).get('method','holm'))
            for row,p in zip(group,adjusted):row.update(p_adjusted=float(p),still_holds=bool(p<1-m.get('confidence_level',.90)))
        else:
            for row in group:row['family_status']='unavailable: complete registered family could not be tested'
    return rows,attempts


def run(studies_root,r29_archive,out):
    from census.boundaries import get_boundaries
    out=out.resolve()
    if out.exists():raise ValueError('use a fresh post hoc output directory')
    archive_hash=digest(r29_archive)
    with patch('requests.sessions.Session.request',side_effect=RuntimeError('Round 30: HTTP blocked')), \
         patch('urllib.request.urlopen',side_effect=RuntimeError('Round 30: HTTP blocked')), \
         TemporaryDirectory(prefix='r30-input-') as scratch:
        r29=extract_r29(r29_archive,Path(scratch))
        sources={'r21b':studies_root/'r21b/confirmatory','r22':studies_root/'r22/confirmatory','r29':r29}
        loaded={};all_hashes={}
        for study,folder in sources.items():
            if out.is_relative_to(folder.resolve()):raise ValueError('outputs must be separate from registered inputs')
            m,info,data,hashes=load_verified(folder,MANIFESTS[study]);all_hashes.update(hashes)
            if study=='r29':data['analysis_frame']=restore_snapshot(data['analysis_frame'],['h1','h2','h3'])
            loaded[study]=(m,info,data,hashes)
        targets=json.loads((ROOT/'docs/audits/im_acs_beta_star.json').read_text())
        coords=pd.DataFrame(targets['coordinates'])
        boundary=get_boundaries('county',2022)
        out.mkdir(parents=True)
        summary={'analysis_status':'post hoc, exploratory','review':'author self-review, not independent',
                 'validation_commit':'2774140a3bdfe0dd5d4f9727a7cdc99631255c01','r29_archive_sha256':archive_hash,
                 'assignment_scope':'fixed Round 26 2020 MI/NY representative points, assigned on all 145 counties before complete cases',
                 'http':'blocked','studies':{}}
        lines=['# Round 30 post hoc IM/ACS re-checks','',
               '**Post hoc; author self-review, not independent. Registered manifests and outputs are unchanged.**','',
               'C1 passed linear, binomial and Poisson observed-estimate targets. C2 EIV failed and remains refused; R21b is unavailable. '
               'C1 is not measurement-error correction and does not test a general true-slope null when noisy controls are present. '
               'Eight fixed clusters, unweighted mean coefficients, between-cluster SE and t(7); no additive ACS SE. '
               'Terms constant in all clusters are absorbed by cluster intercepts and cannot be tested. Poisson offsets stay fixed.','',
               'All cached input/result SHA-256 values and registered manifest hashes were verified before fitting, with HTTP blocked. '
               'MI/NY only: OH/PA is outside the validation geometry and is not re-checked.','']
        for study,(m,info,data,hashes) in loaded.items():
            part=out/study;part.mkdir()
            frame=data['analysis_frame']
            if set(frame.GEOID.astype(str))!=set(coords.GEOID.astype(str)):raise ValueError('post hoc frame differs from validation geography')
            rows,attempts=evaluate(m,frame,data['replicates'],coords,part)
            original=pd.read_csv(sources[study]/'bundle/tables/hypotheses.csv').set_index('id')
            moran={a['id']:residual_moran(sources[study],a,frame,boundary)
                   for a in m['analyses'] if a['id'] in {h['analysis'] for h in m['hypotheses']}}
            for row in rows:row['registered_holm_p']=float(original.loc[row['id'],'p_adjusted'])
            record={'manifest_hash':manifest_hash(m),'rows':rows,'attempts':attempts,'reference_residual_moran':moran,
                    'verified_source_hashes':{str(p.relative_to(sources[study])):v for p,v in hashes.items()}}
            if study=='r29':
                policy=info['wonder_output_policy'];audit=audit_outputs(part,policy)
                if not audit['passed']:raise ValueError('R29 disclosure check failed')
                record['wonder_disclosure']=audit
                record['suppression']=policy['suppression']
                write_json(part/'output_policy.json',policy)
            write_json(part/'summary.json',record);summary['studies'][study]=record
            lines += [f'## {study.upper()}','', '| Hypothesis | Registered Holm p | IM-8 Holm p | Still holds under IM-8? |',
                      '| :--- | ---: | ---: | :--- |']
            for row in rows:
                p='unavailable' if row['p_adjusted'] is None else f"{row['p_adjusted']:.6g}"
                hold='not assessed' if row['still_holds'] is None else 'yes' if row['still_holds'] else 'no'
                lines.append(f"| {row['id']} ({row['analysis']}: {row['term']}) | {row['registered_holm_p']:.6g} | {p} | {hold} |")
            if study=='r21b':lines += ['', 'C2 failed; no EIV IM coefficients or p-values are invented. The original EIV fits remain the reference.']
            if study=='r22':lines += ['', 'Registered p-values retain the original Pearson X2 inference, later found to under-cover. This table does not endorse X2. C1 tests naive ACS-estimate associations, not corrected true effects.']
            if study=='r29':lines += ['', 'H2 excludes its 13 suppressed counties after assignment on all 145. No county values, residual vectors or imputed counts are output. Fixed E omits its ACS and reference-rate uncertainty from slope inference.']
            lines += ['', 'Reference-fit residual Moran I (2022 cached queen contiguity, row standardized; 999 permutations, seed 20261201):','']
            lines += [f"- {aid}: I={z['I']:.6f}, permutation p={z['p_sim']:.4f}, n={z['n']}." for aid,z in moran.items()]
            lines += ['', 'Per-cluster coefficient estimates (labels 0–7; coefficients only):','']
            for aid,attempt in attempts.items():
                if attempt['status']=='unavailable':lines += [f"- {aid}: unavailable ({attempt['reason']})."]
                else:
                    lines += [f"- {aid}: terms `{', '.join(attempt['cluster_terms'])}`; absorbed/not estimable `{', '.join(attempt['not_estimable_terms'])}`.", '']
                    lines += ['| Cluster | '+' | '.join(attempt['cluster_terms'])+' |','| ---: | '+' | '.join('---:' for _ in attempt['cluster_terms'])+' |']
                    lines += ['| '+str(i)+' | '+' | '.join(f'{x:.6g}' for x in b)+' |' for i,b in enumerate(attempt['cluster_estimates'])]
                    lines += ['']
        for path,expected in all_hashes.items():
            if digest(path)!=expected:raise ValueError('registered cached input changed')
        if digest(r29_archive)!=archive_hash:raise ValueError('R29 attachment changed')
        audit=audit_outputs(out/'r29',loaded['r29'][1]['wonder_output_policy'])
        if not audit['passed']:raise ValueError('final R29 disclosure check failed')
        summary['wonder_disclosure']=audit
        lines += ['', '## Interpretation and artifacts','',
                  'These checks leave registered results unchanged. IM with C1 incorporates independent ACS-error variation through the cluster estimates, '
                  'but does not remove attenuation or control-variable measurement-error bias. Coverage was validated only in the frozen MI/NY simulation; '
                  'its passing criterion does not establish performance for arbitrary spatial covariance, county geometries or measurement-error regimes. '
                  'C2 remains unavailable; spatial random effects for corrected EIV inference are the next backlog step.','',
                  'Supporting coefficients, per-cluster estimates, source hashes and Moran summaries are in `r30_study_outputs.tar.gz`. '
                  'The R29 part contains coefficients/diagnostics only and passes `census.wonder_outputs.audit_outputs`; no county death counts or derived '
                  'values for suppressed counties, raw WONDER exports, or national reference death-count vectors are included. '
                  'The archive is key-scanned locally and not published by this script.','']
        write_json(out/'summary.json',summary)
        report='\n'.join(lines)
        (out/'report.md').write_text(report)
        dest=ROOT/'docs/studies/r30_posthoc_im_acs.md'
        if dest.exists():raise ValueError('refusing to overwrite post hoc report')
        dest.write_text(report)
        # Keys are read only to scan the artifact, never printed or serialized.
        from dotenv import dotenv_values
        import os
        common=Path(subprocess.check_output(['git','rev-parse','--git-common-dir'],cwd=ROOT,text=True).strip())
        if not common.is_absolute():common=ROOT/common
        key=os.environ.get('CENSUS_API_KEY') or dotenv_values(common.resolve().parent/'.env').get('CENSUS_API_KEY')
        files=sorted(p for p in out.rglob('*') if p.is_file())
        for path in files:
            if path.is_symlink() or key and key.encode() in path.read_bytes():raise ValueError('archive safety scan failed')
        archive=ROOT/'studies_output/r30_study_outputs.tar.gz'
        if archive.exists():raise ValueError('refusing to overwrite archive')
        with tarfile.open(archive,'w:gz') as tar:
            for path in files:tar.add(path,arcname=str(Path('r30')/path.relative_to(out)),recursive=False)
        with tarfile.open(archive) as tar:
            for member in tar.getmembers():
                if not member.isfile() or key and key.encode() in tar.extractfile(member).read():raise ValueError('archive key scan failed')
        print('Post hoc report complete; HTTP blocked; original hashes unchanged; R29 disclosure passed; key scan', 'passed' if key else 'no configured key')
        print('Local archive',archive,'SHA-256',digest(archive))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--studies-root',type=Path,required=True)
    p.add_argument('--r29-archive',type=Path,default=Path('/tmp/r29_study_outputs.tar.gz'))
    p.add_argument('--output-dir',type=Path,default=ROOT/'studies_output/r30')
    a=p.parse_args();run(a.studies_root,a.r29_archive,a.output_dir)


if __name__=='__main__':main()
