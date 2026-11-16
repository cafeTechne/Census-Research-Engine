# SPDX-License-Identifier: AGPL-3.0-or-later
"""Offline execution golden for behavior-preserving manifest refactors.

Usage: .venv/bin/python scripts/run_golden.py OUT.json

Fixtures reuse tests.test_manifest, test_manifest_multistate, test_tract_harmonization,
test_round20, test_round21_part2, test_round22 and test_round24. All HTTP is refused.
Failures are injected at existing production dependency boundaries, never at new stages.

Normalisation is limited to:
* JSON keys generated_at (wall-clock extraction time), git_commit and package_version
  (execution-build identity; commits and the required version bump change these stamps).
  Build-identity normalisation is the explicit Round 25 section 8 exception; scientific
  values, manifest created timestamps/hashes and dependency versions are NOT masked.
* the scenario's absolute temporary-directory prefix, in paths and embedded text;
* SVG dc:date (Matplotlib wall-clock creation time). svg.hashsalt is a fixed fixture input.
* SHA-256 references to text artifacts whose bytes change under these rules: replace
  their raw digest with the digest of the normalised content, bottom-up. Other digests,
  including input/export/replicate/parquet hashes, are preserved.
Binary artifacts are inventoried by name only, as specified by the plan. DataFrames
retain their split data/index/columns. No model result, exception or deviation is omitted.
"""
import contextlib
import copy
import csv
import hashlib
import io
import json
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matplotlib as mpl
import numpy as np
import pandas as pd
from census import health_sources as hs, tract_harmonization as th
from census.manifest import run_manifest, run_variant
from census.manifest.schema import BLOCKING_DEVIATIONS
from tests.test_manifest import FakeClient
from tests.test_manifest_multistate import TwoStateClient, two_state_manifest
from tests.test_round20 import FakeClient as AgeClient, _replicates
from tests.test_round21_part2 import WONDER, _chr_csv
from tests.test_round22 import count_manifest
from tests.test_round24 import manifest as index_manifest
from tests.test_tract_harmonization import TractClient, fake_vre, manifest as tract_manifest, toy_crosswalk

TEXT = {'.json', '.md', '.csv', '.tex', '.txt', '.svg'}
VOLATILE_KEYS = {'generated_at', 'git_commit', 'package_version'}
UNREACHABLE = ()  # All 19 blocking kinds are exercised, including explicit dependency failures.


def _safe(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as exc:  # the exception class and message belong in the golden
        return f'{type(exc).__name__}: {exc}'


def _normal(value, directory, digests=None):
    if isinstance(value, pd.DataFrame):
        return _normal(value.to_dict(orient='split'), directory, digests)
    if hasattr(value, 'to_dict'):
        return _normal(value.to_dict(), directory, digests)
    if isinstance(value, dict):
        return {str(k): '<volatile>' if k in VOLATILE_KEYS else _normal(v, directory, digests)
                for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normal(v, directory, digests) for v in value]
    if isinstance(value, np.ndarray):
        return _normal(value.tolist(), directory, digests)
    if isinstance(value, np.generic):
        return _normal(value.item(), directory, digests)
    if isinstance(value, Path):
        value = str(value)
    if isinstance(value, str):
        value = value.replace(str(directory), '.')
        for old, new in (digests or {}).items():
            value = value.replace(old, new)
    return value


def _text(raw, suffix, directory, digests):
    text = raw.decode('utf-8')
    import re
    if suffix == '.json':
        # Replace only the volatile scalar, retaining all output whitespace/formatting.
        quoted = r'"(?:\\.|[^"\\])*"'
        keys = '|'.join(sorted(VOLATILE_KEYS))
        text = re.sub(r'("(?:'+keys+r')"\s*:\s*)('+quoted+r'|null)',
                      lambda match: match[1]+'"<volatile>"', text)
        escaped_prefix = json.dumps(str(directory))[1:-1]
        text = text.replace(escaped_prefix, '.')
    text = re.sub(r'(<dc:date>)[^<]+(</dc:date>)', r'\1<volatile>\2', text)
    return _normal(text, directory, digests).encode()


def snapshot(result, directory):
    files = sorted(p for p in directory.rglob('*') if p.is_file())
    text_files = {p: p.read_bytes() for p in files if p.suffix.lower() in TEXT}
    # Artifact digests can refer to other artifacts (bundle -> sidecar -> metadata).
    # The dependency graph is acyclic; fail instead of silently masking a cycle.
    digests = {}
    for _ in range(len(text_files) + 1):
        next_digests = {hashlib.sha256(raw).hexdigest(): hashlib.sha256(
            _text(raw, p.suffix.lower(), directory, digests)).hexdigest() for p, raw in text_files.items()}
        if next_digests == digests:
            break
        digests = next_digests
    else:
        raise RuntimeError('text-artifact digest normalisation did not converge')
    inventory = {str(p.relative_to(directory)): ({'sha256': hashlib.sha256(
        _text(text_files[p], p.suffix.lower(), directory, digests)).hexdigest()} if p in text_files else None)
        for p in files}
    return {'returned': _normal(result, directory, digests), 'files': inventory}


def _client(cls=FakeClient, **kwargs):
    client = cls(**kwargs)
    client.synthetic = True
    return client


def _base():
    m = index_manifest('inequality')
    m.pop('exploratory')
    m['analyses'] = [{'id': 'm1', 'method': 'fit_replicate', 'formula': 'income ~ pop'}]
    m['hypotheses'] = [{'id': 'H1', 'analysis': 'm1', 'statistic': 'coefficient', 'term': 'pop',
                        'direction': 'greater', 'statement': 'Frozen offline association'}]
    m['data_source'] = {'synthetic': True, 'description': 'Frozen offline run-golden fixture'}
    return m


def _call(m, out, client=None, **kwargs):
    return run_manifest(m, out, client=client or _client(), use_cache=False, **kwargs)


def _with_reps(m, out, client=None, names=None):
    probe_m = copy.deepcopy(m)
    probe_m.pop('adjustments', None)
    probe = _call(probe_m, out/'probe', client)
    frame = probe['frame']
    names = names or [v['name'] for v in m['variables']]
    reps = _replicates(frame, names, seed=25)
    reps['Year'] = np.tile(frame['Year'].to_numpy(), len(names))
    return reps


class ScreenClient(FakeClient):
    def fetch(self, *args, **kwargs):
        raw = super().fetch(*args, **kwargs)
        if 'B19013_001M' in raw[0]:
            col = raw[0].index('B19013_001M')
            raw[2][col] = str(float(raw[2][col])*6)
        return raw


class CountyClient(AgeClient):
    """Round 22's offline tract payload represented as distinct county rows."""
    def fetch(self, *args, **kwargs):
        raw = super().fetch(*args, **kwargs)
        header = raw[0]
        ci, ti, gi = (header.index(k) for k in ('county', 'tract', 'GEO_ID'))
        rows = []
        for i, row in enumerate(raw[1:]):
            row = list(row)
            row[ci] = f'{2*i+1:03}'
            row[gi] = '0500000US26'+row[ci]
            rows.append([v for j, v in enumerate(row) if j != ti])
        return [[v for j, v in enumerate(header) if j != ti]]+rows


class WonderClient(CountyClient):
    def fetch(self, *args, **kwargs):
        return super().fetch(*args, **kwargs)[:4]


def _chr_fixture(n):
    """Adapt the Round 21 CSV fixture to coherent LBW proportions and birth counts."""
    rows = list(csv.reader(io.StringIO(_chr_csv(
        [(f'26{2*i+1:03}', .07+i/1000, 0) for i in range(n)], code='v037').decode())))
    for row in rows[3:-1]:
        value = float(row[6])
        row[7:11] = [str(round(value*30000)), '30000', str(value-.006), str(value+.006)]
    buf = io.StringIO(); csv.writer(buf, lineterminator='\n').writerows(rows)
    raw = buf.getvalue().encode()
    return {'raw': raw, 'files': [{'url': 'fixture://chr', 'sha256': hashlib.sha256(raw).hexdigest()}],
            'dataset': 'offline_chr.csv', 'rows_updated_at': None}


def _harmonized(out, failure=None):
    def crosswalk(target, states, kinds, releases=()):
        if failure == 'failed':
            raise ValueError('offline crosswalk failure')
        cw = toy_crosswalk()
        if failure == 'incomplete':
            cw = cw[cw.source_geoid.str.endswith('000100')].copy()
        return {kind: cw for kind in kinds}
    def vre(*args, **kwargs):
        f = fake_vre(*args, **kwargs)
        if failure == 'mismatch' and args[1] == 2019:
            f['estimate'] *= 1.01
        return f
    with mock.patch.object(th, 'crosswalks', side_effect=crosswalk), \
            mock.patch('census.replicate.fetch_vre', side_effect=vre):
        return _call(tract_manifest(), out/'run', _client(TractClient))


def scenario(name, out):
    m = _base()
    if name in ('fit_replicate', 'exclusions', 'replicates_incomplete', 'variant'):
        reps = _with_reps(m, out)
        if name == 'replicates_incomplete':
            reps = reps.iloc[1:]
        if name == 'exclusions':
            m['exclusions'] = [{'rule': 'geoid_exclude', 'geoids': [str(reps.GEOID.iloc[0])]},
                {'rule': 'cv_screen', 'variables': ['income'], 'threshold': 30, 'action': 'exclude'}]
        result = _call(m, out/'run', _client(ScreenClient) if name == 'exclusions' else None, replicates=reps)
        if name == 'variant':
            return {'run': result, 'variant': _safe(run_variant, out/'run', 'm1', formula='income ~ np.log(pop)',
                                                   out_dir=out/'variant', label='golden')}
        return result
    if name in ('inequality', 'smr'):
        m = index_manifest(name)
        return _call(m, out/'run', replicates=_with_reps(m, out))
    if name in ('multistate_rpp_derivations', 'failed_calls', 'adjustment_failed'):
        m = two_state_manifest()
        client = _client(TwoStateClient, fail_states=['36'] if name == 'failed_calls' else [])
        if name == 'adjustment_failed':
            with mock.patch('census.workflows_microdata.place_adjust', side_effect=ValueError('offline RPP failure')):
                return _call(m, out/'run', client)
        return _call(m, out/'run', client, replicates=_with_reps(m, out, client))
    if name.startswith('harmonization'):
        return _harmonized(out, name.split('_', 1)[1] if '_' in name else None)
    if name in ('chr_binomial', 'external_join_failed', 'external_unavailable'):
        m = count_manifest()
        client = _client(CountyClient)
        n = len(client.fetch(2024, 'B18101'))-1
        if name == 'external_unavailable':
            with mock.patch.object(hs, 'fetch_chr', side_effect=ValueError('offline external failure')):
                return _call(m, out/'run', client)
        got = _chr_fixture(n if name != 'external_join_failed' else n//2)
        with mock.patch.object(hs, 'fetch_chr', return_value=got):
            return _call(m, out/'run', client, replicates=_with_reps(m, out, client))
    if name == 'wonder':
        path = out/'wonder.txt'; path.write_text(WONDER, encoding='utf-8', newline='\n')
        m = count_manifest(); m['external'] = [{'name': 'deaths', 'source': 'wonder', 'measure': 'deaths',
                                               'file': 'wonder.txt', 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}]
        m['analyses'] = [{'id': 'm1', 'method': 'fit_replicate', 'formula': 'deaths ~ 1'}]
        # Restrict ACS units to the fixture's three counties; keep suppression missing.
        m['geography']['codes'] = ['001', '003', '005']
        m['hypotheses'][0]['term'] = 'Intercept'
        with mock.patch.object(hs, 'resolve_external_file', side_effect=lambda p: str(out/p)):
            return _call(m, out/'run', _client(WonderClient))
    if name == 'validation_error':
        m['analyses'] = []
    elif name == 'output_error':
        (out/'run'/'bundle').mkdir(parents=True)
        (out/'run'/'bundle'/'occupied.txt').write_text('existing output\n')
    elif name == 'replicates_unavailable':
        m['analyses'][0]['replicates'] = 'required'
    elif name == 'analysis_failed':
        m['analyses'][0]['formula'] = 'income ~ I(pop / 0)'
    elif name == 'hypothesis_not_tested':
        m['hypotheses'][0]['term'] = 'absent_term'
    elif name == 'data_source_mismatch':
        client = _client(); client.synthetic = False
        return _call(m, out/'run', client)
    elif name == 'blocked_variable':
        with mock.patch('census.pipeline.plan_extraction', return_value={'success': False, 'message': 'offline blocked variable'}):
            return _call(m, out/'run')
    elif name == 'extraction_failed':
        return _call(m, out/'run', _client(FakeClient, fail_tables=['B01003']))
    elif name == 'variable_missing_from_extraction':
        with mock.patch('census.manifest.run._codebook_columns', return_value=None):
            return _call(m, out/'run')
    elif name == 'analysis_frame_failed':
        with mock.patch('census.analysis.analysis_frame', side_effect=ValueError('offline analysis-frame failure')):
            return _call(m, out/'run')
    elif name == 'aggregation_failed':
        m['aggregation'] = {'mapping': {}}
        with mock.patch('census.aggregate.aggregate_geographies', side_effect=ValueError('offline aggregation failure')):
            return _call(m, out/'run')
    elif name == 'replicates_overlapping_releases':
        m['releases'] = [2018, 2019]
        return _call(m, out/'run', replicates=_with_reps(m, out))
    else:
        if name not in ('validation_error', 'output_error', 'replicates_unavailable', 'analysis_failed', 'hypothesis_not_tested'):
            raise ValueError(f'unknown golden scenario {name}')
    return _call(m, out/'run')


SCENARIOS = ('fit_replicate', 'replicates_unavailable', 'exclusions', 'multistate_rpp_derivations',
             'harmonization', 'harmonization_failed', 'harmonization_incomplete', 'harmonization_mismatch',
             'chr_binomial', 'wonder', 'inequality', 'smr', 'variant', 'validation_error', 'output_error',
             'analysis_failed', 'hypothesis_not_tested', 'data_source_mismatch', 'blocked_variable',
             'extraction_failed', 'variable_missing_from_extraction', 'analysis_frame_failed',
             'aggregation_failed', 'replicates_incomplete', 'failed_calls', 'adjustment_failed',
             'replicates_overlapping_releases', 'external_unavailable', 'external_join_failed')


def main():
    snapshots = {}; kinds = set()
    with tempfile.TemporaryDirectory(prefix='run-golden-') as tmp, \
            mpl.rc_context({'svg.hashsalt': 'run-golden'}), \
            mock.patch('requests.sessions.Session.request', side_effect=AssertionError('run golden attempted HTTP')) as http:
        for name in SCENARIOS:
            directory = Path(tmp)/name; directory.mkdir()
            with contextlib.redirect_stdout(io.StringIO()):
                result = _safe(scenario, name, directory)
            values = [result] if isinstance(result, dict) else []
            if isinstance(result, dict) and 'run' in result:
                values.append(result['run'])
            for value in values:
                kinds.update(d['kind'] for d in value.get('deviations', []))
            if not isinstance(result, dict):
                raise RuntimeError(f'{name} did not return a run result: {result}')
            if name in ('fit_replicate', 'exclusions', 'multistate_rpp_derivations', 'harmonization',
                        'chr_binomial', 'inequality', 'smr', 'variant'):
                run = result.get('run', result)
                if not run.get('success'):
                    raise RuntimeError(f'{name} unexpectedly failed: {run.get("deviations", run.get("errors"))}')
            snapshots[name] = snapshot(result, directory)
            print(name, flush=True)
        if http.call_count:
            raise RuntimeError(f'offline corpus attempted {http.call_count} HTTP requests')
    missing = set(BLOCKING_DEVIATIONS)-kinds-set(UNREACHABLE)
    if missing:
        raise RuntimeError(f'missing blocking-deviation coverage: {sorted(missing)}')
    Path(sys.argv[1]).write_text(json.dumps(snapshots, sort_keys=True, indent=1) + '\n', encoding='utf-8')
    print(f'{len(snapshots)} scenarios; {len(kinds)} deviation kinds -> {sys.argv[1]}')


if __name__ == '__main__':
    main()
