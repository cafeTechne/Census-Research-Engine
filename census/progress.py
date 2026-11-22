# SPDX-License-Identifier: AGPL-3.0-or-later
"""Progress lines for long workflows (Round 70, backlog N48).

Lines go to stderr, never stdout (which stays clean JSON for the CLI and MCP). ``CENSUS_PROGRESS=0`` silences them.
An MCP server can register a callback (``set_callback``) that forwards progress to the client.
"""
import os
import sys
from contextvars import ContextVar
from typing import Callable, Optional

_CALLBACK: ContextVar[Optional[Callable[[float, Optional[float], str], None]]] = ContextVar("census_progress", default=None)


def enabled() -> bool:
    return os.getenv("CENSUS_PROGRESS", "1").strip().lower() not in ("0", "false", "no", "off")


def set_callback(fn: Optional[Callable[[float, Optional[float], str], None]]):
    """Register a progress sink for this context; returns a token for ``reset_callback``."""
    return _CALLBACK.set(fn)


def reset_callback(token) -> None:
    _CALLBACK.reset(token)


def report(message: str, done: Optional[float] = None, total: Optional[float] = None) -> None:
    """Emit one progress line (and forward it to a registered callback). Never raises."""
    if not enabled():
        return
    try:
        frac = f" [{int(done)}/{int(total)}]" if done is not None and total else ""
        print(f"census: {message}{frac}", file=sys.stderr, flush=True)
        cb = _CALLBACK.get()
        if cb is not None:
            cb(float(done or 0), None if total is None else float(total), message)
    except Exception:  # noqa: BLE001 - progress must never break a run
        pass
