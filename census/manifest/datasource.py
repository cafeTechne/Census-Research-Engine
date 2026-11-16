# SPDX-License-Identifier: AGPL-3.0-or-later
"""Manifest datasource definitions."""

from typing import Any, Dict, Mapping, Optional, Tuple



def effective_data_source(manifest: Mapping[str, Any], client: Any = None) -> Dict[str, Any]:
    """Declaration-level data source (before a run): the manifest's
    ``data_source`` (default: not synthetic), forced synthetic when ``client``
    is observed synthetic. Runs use :func:`resolve_data_source`."""
    ds = dict(manifest.get("data_source") or {})
    ds["synthetic"] = bool(ds.get("synthetic")) or (client is not None and observed_data_source(client)[0])
    return ds


def observed_data_source(client: Any = None, use_cache: bool = True) -> Tuple[bool, Dict[str, Any]]:
    """(synthetic, marker) for the client that serves the data: synthetic when
    the client has a true ``synthetic`` attribute or its cache (for
    ``client=None``: the default cache, when ``use_cache``) carries a
    ``QueryCache.mark_synthetic`` marker. ``marker`` holds its description and
    generator ({} when none)."""
    if client is None:
        from ..cache import get_default_cache
        cache = get_default_cache() if use_cache else None
    else:
        cache = getattr(client, "cache", None)
    marker = None
    if cache is not None and hasattr(cache, "synthetic_marker"):
        try:
            marker = cache.synthetic_marker()
        except Exception:  # noqa: BLE001 - unreadable marker: treat as none
            marker = None
    synthetic = marker is not None or (client is not None and getattr(client, "synthetic", False) is True)
    return synthetic, dict(marker or {})


def data_source_record(client: Any = None, use_cache: bool = True) -> Dict[str, Any]:
    """Observed data source as recorded in extraction metadata and results bundles:
    {"kind": "synthetic" | "census_api", "synthetic": bool} plus the synthetic
    marker's description and generator when set (:func:`observed_data_source`)."""
    synthetic, marker = observed_data_source(client, use_cache)
    record: Dict[str, Any] = {"kind": "synthetic" if synthetic else "census_api", "synthetic": synthetic}
    record.update({k: marker[k] for k in ("description", "generator") if marker.get(k)})
    return record


def resolve_data_source(manifest: Mapping[str, Any], client: Any = None,
                        use_cache: bool = True) -> Tuple[Dict[str, Any], Optional[str]]:
    """Data-source label for a run: the observed source wins over the declaration.

    Returns (source, mismatch). ``source["synthetic"]`` is the observed value;
    ``declared_synthetic`` the manifest's (None when undeclared). On a
    mismatch the declared description/generator are dropped (they describe
    data that were not used) and ``mismatch`` explains it.
    """
    ds = manifest.get("data_source")
    ds = dict(ds) if isinstance(ds, Mapping) else {}
    declared = ds.get("synthetic") if isinstance(ds.get("synthetic"), bool) else None
    observed, marker = observed_data_source(client, use_cache)
    mismatch = None
    if declared is not None and declared != observed:
        mismatch = (f"manifest declares data_source.synthetic={str(declared).lower()} but the data came from a "
                    + ("synthetic source (synthetic client or marked cache)" if observed
                       else "non-synthetic source (Census Data API client or unmarked cache)")
                    + "; labelled by the observed source")
        ds = {}
    source: Dict[str, Any] = {k: v for k, v in ds.items() if k != "synthetic"}
    if observed:
        for k in ("description", "generator"):
            if not source.get(k) and marker.get(k):
                source[k] = marker[k]
    source.update(synthetic=observed, declared_synthetic=declared)
    return source, mismatch
