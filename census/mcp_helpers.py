# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pure calculation MCP tools extracted from mcp_server.py (Round 148)."""
from typing import Any, Dict, Optional

from census import (
    PRICE_INDEXES,
    PriceIndexUnavailable,
    adjust_inflation as _adjust_inflation,
    calculate_cv as _calculate_cv,
    errors,
    load_price_index,
    price_index_info,
    provisional_advisory,
    z_test,
)
from census.data_integrity import BundledDataIntegrityError, integrity_error_result
from census.decennial import is_decennial
from census.stats import acs_overlap_years


def calculate_cv(estimate: float, moe: float, product: Optional[str] = None) -> Dict[str, Any]:
    """Standard error, coefficient of variation and reliability for an ACS estimate.

    SE = MOE / 1.645; CV = SE / estimate x 100.
    Reliability: High (CV <= 15%), Moderate (15-30%), Low (> 30%).

    Args:
        estimate: The ACS estimate.
        moe: Its published 90% margin of error.
        product: 'decennial' is refused: 2020 Census counts have no sampling MOE.
    """
    try:
        return _calculate_cv(estimate, moe, product=product)
    except ValueError as exc:
        return errors.error_result(errors.INVALID_INPUT, str(exc))


def calculate_significance(
    est1: float,
    moe1: float,
    est2: float,
    moe2: float,
    confidence_level: float = 0.90,
    year1: Optional[int] = None,
    year2: Optional[int] = None,
    product: str = "5-year",
    product2: Optional[str] = None,
) -> Dict[str, Any]:
    """Two-tailed Z-test for whether two ACS estimates differ significantly.

    Z = |X1 - X2| / sqrt(SE1^2 + SE2^2). When year1 and year2 are both given
    (same geography, different 5-year periods), the Census overlapping-sample
    adjustment sqrt(1 - overlap/5) is applied to the SE of the difference.

    Args:
        est1, moe1: First estimate and its 90% MOE.
        est2, moe2: Second estimate and its 90% MOE.
        confidence_level: 0.90, 0.95 or 0.99 (default 0.90, the ACS standard).
        year1, year2: Optional ACS end years for the overlap adjustment.
        product: '5-year' (default) or '1-year' (1-year releases never overlap).
            'decennial' alone is refused (census counts are not sample-based).
        product2: Product of the second value when it differs: 'decennial' tests the
            ACS estimate against a 2020 Census count as a fixed reference (moe2=0);
            the result notes that only ACS sampling error is measured.
    """
    second = product2 or product
    try:
        both_acs = not (is_decennial(product) or is_decennial(second))
        overlap = acs_overlap_years(year1, year2, product, second) if year1 and year2 and both_acs else 0
        return z_test(est1, moe1, est2, moe2, confidence_level, overlap_years=overlap,
                      product1=product, product2=second)
    except ValueError as exc:
        return errors.error_result(errors.INVALID_INPUT, str(exc))


def adjust_inflation(
    value: float,
    from_year: int,
    to_year: int,
    index: str = "r-cpi-u-rs",
    allow_provisional: bool = False,
) -> Dict[str, Any]:
    """Convert a dollar value between years with an annual price index.

    Args:
        value: Dollar amount in from_year dollars (e.g. 2012 ACS median income).
        from_year: Year of the original dollars (the ACS period end year).
        to_year: Target constant-dollar year.
        index: 'r-cpi-u-rs' (Census Bureau standard for ACS, default), 'cpi-u', or
            'c-cpi-u' (CPS ASEC income reports).
        allow_provisional: Use a year whose annual figure rests on fewer than 12
            published months (2025); the result carries an advisory.
    """
    if index not in PRICE_INDEXES:
        return errors.error_result(errors.INVALID_INPUT, f"index must be one of {PRICE_INDEXES}.")
    try:
        adjusted = _adjust_inflation(value, from_year, to_year, index=index, allow_provisional=allow_provisional)
    except PriceIndexUnavailable as exc:
        return errors.error_result(errors.PRICE_INDEX_UNAVAILABLE, str(exc.args[0]))
    except BundledDataIntegrityError as exc:
        return integrity_error_result(exc)
    table = load_price_index(index, allow_provisional=allow_provisional)
    info = price_index_info(index)
    custom = {"custom_table": info["custom_table"]} if "custom_table" in info else {}
    return {
        "advisory": provisional_advisory(index, [from_year, to_year]) if allow_provisional else None,
        "success": True,
        "value": value,
        "from_year": from_year,
        "to_year": to_year,
        "index": index,
        "index_from": table[from_year],
        "index_to": table[to_year],
        "adjusted_value": adjusted,
        "source": info.get("source", ""),
        **custom,
    }


