# SPDX-License-Identifier: AGPL-3.0-or-later
"""Locate and load the user's ``.env`` (Round 70, backlog N47).

``load_dotenv()`` without a path searches upward from the *calling file*, so an engine installed from a wheel
never saw the project's ``.env`` (its Census API key). Order here:

1. ``CENSUS_DOTENV``: an explicit file;
2. ``.env`` found upward from the current working directory;
3. ``.env`` found upward from the package location (editable clones, the previous behaviour).

Variables already in the environment are never overridden, and no value is ever printed or returned.
"""
import os
from pathlib import Path
from typing import Optional

from dotenv import find_dotenv, load_dotenv

_LOADED: Optional[str] = None
_DONE = False


def load_environment(force: bool = False) -> Optional[str]:
    """Load the first ``.env`` in the order above; returns its path (or None). Idempotent unless ``force``."""
    global _LOADED, _DONE
    if _DONE and not force:
        return _LOADED
    _DONE, _LOADED = True, None
    explicit = os.getenv("CENSUS_DOTENV", "").strip()
    candidates = [explicit] if explicit else []
    candidates.append(find_dotenv(usecwd=True))
    pkg = Path(__file__).resolve().parent
    for folder in (pkg, *pkg.parents):
        if (folder/".env").is_file():
            candidates.append(str(folder/".env"))
            break
    for path in candidates:
        if path and Path(path).is_file():
            load_dotenv(path, override=False)
            _LOADED = str(Path(path).resolve())
            break
    return _LOADED
