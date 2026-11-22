# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 70: .env discovery (N47) and run_manifest checkpoints / progress lines (N48)."""
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pandas as pd
import pytest

from census.manifest import load_manifest, run_manifest
from tests.test_manifest import EXAMPLE, FakeClient

ROOT = Path(__file__).resolve().parents[1]
KEY = "r70dummykey0123456789abcdef"

PROBE = ("import sys, os; sys.path.insert(0, %r); from census import env; p = env.load_environment(); "
         "print(os.getenv('CENSUS_API_KEY', '') == %r, p is not None)")


def _probe(cwd, extra_env=None):
    env = {k: v for k, v in os.environ.items() if k not in ("CENSUS_API_KEY", "CENSUS_DOTENV")}
    env.update(extra_env or {})
    r = subprocess.run([sys.executable, "-c", PROBE % (str(ROOT), KEY)], cwd=cwd, env=env, capture_output=True, text=True)
    assert KEY not in r.stdout and KEY not in r.stderr
    return r.stdout.split()


def test_env_found_from_working_directory(tmp_path):
    (tmp_path/".env").write_text(f"CENSUS_API_KEY={KEY}\n")
    assert _probe(tmp_path) == ["True", "True"]


def test_explicit_dotenv_wins(tmp_path):
    (tmp_path/".env").write_text("CENSUS_API_KEY=wrong\n")
    other = tmp_path/"other.env"; other.write_text(f"CENSUS_API_KEY={KEY}\n")
    assert _probe(tmp_path, {"CENSUS_DOTENV": str(other)}) == ["True", "True"]


def test_existing_variable_not_overridden(tmp_path):
    (tmp_path/".env").write_text("CENSUS_API_KEY=fromfile\n")
    assert _probe(tmp_path, {"CENSUS_API_KEY": KEY}) == ["True", "True"]


def test_package_fallback_only_without_cwd_file(tmp_path):
    """With no .env upward of the working directory, the package location is searched (editable clones)."""
    from census import env
    with mock.patch.object(env, "find_dotenv", return_value=""), mock.patch.dict(os.environ, {}, clear=False):
        os.environ.pop("CENSUS_DOTENV", None)
        p = env.load_environment(force=True)
    assert p is None or Path(p).parent in Path(env.__file__).resolve().parents


def _ok(tmp_path, **kw):
    return run_manifest(load_manifest(EXAMPLE), tmp_path, client=FakeClient(), use_cache=False, **kw)


def test_checkpoint_resume_and_cleanup(tmp_path, monkeypatch):
    from census.manifest import run as runmod
    real = runmod._run_analysis
    calls = {"n": 0}

    def flaky(a, *args, **kw):
        calls["n"] += 1
        if calls["n"] == 2:
            raise KeyboardInterrupt  # simulates a killed run after the first analysis
        return real(a, *args, **kw)

    m = load_manifest(EXAMPLE)
    if len(m["analyses"]) < 2:
        pytest.skip("example manifest has a single analysis")
    monkeypatch.setattr(runmod, "_run_analysis", flaky)
    with pytest.raises(KeyboardInterrupt):
        _ok(tmp_path, checkpoint=True)
    saved = sorted(p.name for p in (tmp_path/".checkpoint").glob("*.pkl"))
    assert len(saved) == 1
    monkeypatch.setattr(runmod, "_run_analysis", real)
    res = _ok(tmp_path, checkpoint=True)
    assert res["checkpoint"]["reused"] == [saved[0][:-4]] and res["checkpoint"].get("removed")
    assert not (tmp_path/".checkpoint").exists()
    plain = _ok(tmp_path/"plain")
    pd.testing.assert_frame_equal(res["hypotheses"].reset_index(drop=True), plain["hypotheses"].reset_index(drop=True))


def test_stale_checkpoint_ignored(tmp_path):
    from census.manifest import run as runmod
    m = load_manifest(EXAMPLE)
    first = run_manifest(m, tmp_path/"a", client=FakeClient(), use_cache=False, checkpoint=True)
    folder = tmp_path/"b"/".checkpoint"; folder.mkdir(parents=True)
    aid = m["analyses"][0]["id"]
    import pickle
    (folder/f"{aid}.pkl").write_bytes(pickle.dumps({"key": "other", "result": None, "deviations": []}))
    res = run_manifest(m, tmp_path/"b", client=FakeClient(), use_cache=False, checkpoint=True)
    assert any(x["analysis"] == aid for x in res["checkpoint"]["ignored"]) and res["checkpoint"]["reused"] == []
    pd.testing.assert_frame_equal(res["hypotheses"].reset_index(drop=True), first["hypotheses"].reset_index(drop=True))


def test_progress_to_stderr_and_silenced(tmp_path, capsys, monkeypatch):
    _ok(tmp_path/"p")
    err = capsys.readouterr().err
    assert "census: run_manifest: analysis" in err
    monkeypatch.setenv("CENSUS_PROGRESS", "0")
    _ok(tmp_path/"q")
    assert "census:" not in capsys.readouterr().err


def test_cli_stdout_stays_json(tmp_path):
    from census import progress
    with mock.patch("sys.stdout") as out:
        progress.report("x", 1, 2)
    out.write.assert_not_called()
