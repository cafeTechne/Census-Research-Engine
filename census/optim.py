# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared helpers for multi-start numerical optimization.

L-BFGS-B with very tight ``ftol`` often ends a run that has already reached
the optimum with an ABNORMAL line-search exit, and whether it does depends on
the SciPy version. When several starts reach the same optimum, picking the
lowest objective alone can therefore pick a run flagged as unconverged whose
objective is lower only by rounding (2e-13 on the Round 16 A1 draw under
SciPy 1.15), and the fit is then reported as unconverged although another
start converged to the same point. ``best_start`` prefers a converged run
whose objective ties the minimum; ``projected_score_ok`` judges convergence
from the score at the solution instead of the optimizer's exit status.
"""

from typing import Optional, Sequence, Tuple

import numpy as np

TIE_RTOL = 1e-9
TIE_ATOL = 1e-9


def best_start(results: Sequence, rtol: float = TIE_RTOL, atol: float = TIE_ATOL):
    """Best of several ``scipy.optimize.OptimizeResult`` objects.

    The lowest finite objective wins, except that a converged run (``success``)
    whose objective is within ``atol + rtol * |min|`` of the minimum is
    preferred over an unconverged one. A strictly better unconverged run is
    still returned, so the caller still reports it as unconverged.
    """
    finite = [r for r in results if r is not None and np.isfinite(r.fun)]
    if not finite:
        return results[0] if results else None
    best = min(finite, key=lambda r: r.fun)
    if bool(best.success):
        return best
    tol = atol + rtol * abs(float(best.fun))
    tied = [r for r in finite if bool(r.success) and r.fun <= best.fun + tol]
    return min(tied, key=lambda r: r.fun) if tied else best


def projected_score_ok(x: Sequence[float], grad: Sequence[float],
                       bounds: Sequence[Tuple[Optional[float], Optional[float]]],
                       tol: float = 1e-3, edge: float = 1e-10) -> bool:
    """True when every gradient component is below ``tol`` in absolute value, or
    the parameter sits on a bound with the gradient pointing out of the box
    (the first-order condition of a bound-constrained minimum)."""
    for v, g, (lo, hi) in zip(x, grad, bounds):
        if not np.isfinite(g):
            return False
        at_lo = lo is not None and v <= lo + edge
        at_hi = hi is not None and v >= hi - edge
        if (at_lo and g >= 0) or (at_hi and g <= 0):
            continue
        if abs(g) >= tol:
            return False
    return True
