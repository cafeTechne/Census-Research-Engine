# SPDX-License-Identifier: AGPL-3.0-or-later
"""Background domain-corpus miner for isolated Layer B (OpenAlex + Europe PMC -> Samsung 850 EVO SSD FTS5).

Strictly isolated from ``census/`` (zero imports). Supports polite, resumable,
multi-page continuous harvesting across 24 curated epidemiology, demography,
spatial statistics, causal inference, and ACS survey-methods domains.
"""
from __future__ import annotations

import datetime as _dt
import json
import signal
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from .epmc_client import EuropePMCClient, merge_and_deduplicate
from .local_index import LocalLiteratureIndex, resolve_index_path
from .s2_client import OpenAlexClient

# 24 curated domain topics aligned with every validated statistical/epidemiologic family in the engine.
DOMAIN_TOPICS: List[Dict[str, str]] = [
    {"id": "D01", "domain": "spatial_cancer_mortality", "query": "county cancer mortality poverty spatial disparities United States"},
    {"id": "D02", "domain": "bym2_disease_mapping", "query": "BYM2 Besag York Mollie Bayesian spatial disease mapping mortality"},
    {"id": "D03", "domain": "spatial_scan_clusters", "query": "Kulldorff spatial scan statistic county disease cluster detection"},
    {"id": "D04", "domain": "scpc_spatial_inference", "query": "spatial correlation principal components SCPC regression inference"},
    {"id": "D05", "domain": "fay_herriot_sae", "query": "Fay Herriot small area estimation American Community Survey poverty"},
    {"id": "D06", "domain": "temporal_sae_rao_yu", "query": "Rao Yu temporal small area estimation arcsine proportion survey"},
    {"id": "D07", "domain": "acs_margins_of_error", "query": "American Community Survey margins of error replicate weights reliability"},
    {"id": "D08", "domain": "errors_in_variables", "query": "errors in variables measurement error regression calibration SIMEX survey"},
    {"id": "D09", "domain": "medicare_age65_rdd", "query": "Medicare age 65 regression discontinuity health insurance utilization"},
    {"id": "D10", "domain": "staggered_did_policy", "query": "staggered difference in differences Callaway SantAnna health policy"},
    {"id": "D11", "domain": "interrupted_time_series", "query": "interrupted time series segmented regression public health policy"},
    {"id": "D12", "domain": "causal_aipw_positivity", "query": "augmented inverse probability weighting overlap positivity observational health"},
    {"id": "D13", "domain": "marginal_structural_gformula", "query": "marginal structural model parametric g-formula time-varying confounding"},
    {"id": "D14", "domain": "qba_evalue_sensitivity", "query": "quantitative bias analysis E-value unmeasured confounding epidemiology"},
    {"id": "D15", "domain": "life_table_arriaga", "query": "Chiang life table Arriaga decomposition life expectancy gap United States"},
    {"id": "D16", "domain": "ypll_premature_mortality", "query": "years of potential life lost premature mortality CDC WONDER counties"},
    {"id": "D17", "domain": "oaxaca_fairlie_decomposition", "query": "Oaxaca Blinder Fairlie decomposition disability earnings poverty disparities"},
    {"id": "D18", "domain": "residential_segregation", "query": "residential segregation dissimilarity isolation Theil H census tract ACS"},
    {"id": "D19", "domain": "area_deprivation_rpp", "query": "area deprivation index socioeconomic composite Regional Price Parities"},
    {"id": "D20", "domain": "ecologic_fallacy_puma", "query": "ecologic fallacy contextual effect within between multilevel survey"},
    {"id": "D21", "domain": "who_health_inequality", "query": "WHO health inequality monitoring slope index relative index attributable risk"},
    {"id": "D22", "domain": "county_ranking_uncertainty", "query": "county health rankings rank confidence intervals Klein Wright Wieczorek"},
    {"id": "D23", "domain": "drug_overdose_heart_stroke", "query": "county drug overdose heart disease stroke mortality rural urban disparities"},
    {"id": "D24", "domain": "meta_analysis_hksj", "query": "Hartung Knapp Sidik Jonkman random effects meta-analysis epidemiology"},
    {"id": "D25", "domain": "environmental_pm25_disparities", "query": "PM2.5 air pollution environmental justice county mortality disparities census"},
    {"id": "D26", "domain": "maternal_infant_mortality", "query": "maternal infant mortality county racial socioeconomic disparities United States"},
    {"id": "D27", "domain": "rural_hospital_closures", "query": "rural hospital closures access to care county mortality difference in differences"},
    {"id": "D28", "domain": "housing_eviction_health", "query": "housing affordability rent burden eviction health disparities census tract"},
    {"id": "D29", "domain": "broadband_digital_divide", "query": "broadband internet access digital divide telehealth rural ACS disparities"},
    {"id": "D30", "domain": "climate_heat_mortality", "query": "extreme heat wave climate vulnerability county mortality socioeconomic"},
    {"id": "D31", "domain": "food_deserts_snap", "query": "food insecurity food deserts SNAP participation poverty health counties"},
    {"id": "D32", "domain": "medicaid_expansion_policy", "query": "Medicaid expansion Affordable Care Act uninsured mortality quasi-experimental"},
    {"id": "D33", "domain": "opioid_fentanyl_surveillance", "query": "opioid fentanyl overdose spatial temporal surveillance county epidemiology"},
    {"id": "D34", "domain": "disability_employment_ssi", "query": "disability employment earnings gap American Community Survey PUMS"},
    {"id": "D35", "domain": "tract_harmonization_crosswalk", "query": "census tract boundary harmonization 2010 2020 crosswalk longitudinal"},
    {"id": "D36", "domain": "spatial_cv_maup", "query": "modifiable areal unit problem MAUP spatial block cross-validation epidemiology"},
]


def resolve_state_path(db_path: Optional[str | Path] = None, state_path: Optional[str | Path] = None) -> Path:
    if state_path is not None:
        return Path(state_path)
    return resolve_index_path(db_path).with_name("miner_state.json")


def load_topics(topics_file: Optional[str | Path] = None) -> List[Dict[str, str]]:
    if topics_file is None:
        return list(DOMAIN_TOPICS)
    data = json.loads(Path(topics_file).read_text(encoding="utf-8"))
    return [dict(item) for item in data]


def load_miner_status(
    db_path: Optional[str | Path] = None,
    state_path: Optional[str | Path] = None,
) -> Dict[str, Any]:
    idx = LocalLiteratureIndex(db_path)
    spath = resolve_state_path(db_path, state_path)
    state: Dict[str, Any] = {}
    if spath.exists():
        try:
            state = json.loads(spath.read_text(encoding="utf-8"))
        except Exception:
            state = {}
    return {
        "ok": True,
        "status": "exploratory_hypothesis_seed",
        "domain_count": len(DOMAIN_TOPICS),
        "state_path": str(spath),
        "index_stats": idx.stats(),
        "miner_state": state,
    }


class CorpusMiner:
    """Polite, resumable, multi-page background harvester for OpenAlex + Europe PMC -> SQLite FTS5."""

    def __init__(
        self,
        *,
        db_path: Optional[str | Path] = None,
        state_path: Optional[str | Path] = None,
        cache_dir: str | Path = ".cache/layer_b_miner",
        topics: Optional[Sequence[Dict[str, str]]] = None,
        limit_per_query: int = 25,
        max_pages_per_topic: int = 10,
        delay_seconds: float = 1.5,
        cycle_sleep_seconds: float = 1800.0,
        openalex_client: Optional[OpenAlexClient] = None,
        epmc_client: Optional[EuropePMCClient] = None,
        sleep_fn: Callable[[float], None] = time.sleep,
        auto_sync_vectors: bool = True,
    ) -> None:
        self.db_path = resolve_index_path(db_path)
        self.state_path = resolve_state_path(self.db_path, state_path)
        self.cache_dir = Path(cache_dir)
        self.topics = list(topics) if topics is not None else list(DOMAIN_TOPICS)
        self.limit_per_query = int(limit_per_query)
        self.max_pages_per_topic = int(max_pages_per_topic)
        self.delay_seconds = float(delay_seconds)
        self.cycle_sleep_seconds = float(cycle_sleep_seconds)
        self.index = LocalLiteratureIndex(self.db_path)
        self.oa = openalex_client or OpenAlexClient(cache_dir=self.cache_dir)
        self.epmc = epmc_client or EuropePMCClient(cache_dir=self.cache_dir)
        self._sleep = sleep_fn
        self.auto_sync_vectors = bool(auto_sync_vectors)
        self._stop_requested = False

    def _load_state(self) -> Dict[str, Any]:
        if self.state_path.exists():
            try:
                return json.loads(self.state_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "cycles_completed": 0,
            "total_ingested_records": 0,
            "topic_pages": {},
            "errors_count": 0,
            "last_run_utc": None,
            "last_topic_id": None,
        }

    def _save_state(self, state: Dict[str, Any]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def mine_topic_step(self, topic: Dict[str, str], state: Dict[str, Any]) -> int:
        tid = topic["id"]
        page = int(state["topic_pages"].get(tid, 1))
        if page > self.max_pages_per_topic:
            page = 1  # wrap around to refresh newest literature on subsequent cycles

        oa_papers = self.oa.search_papers(topic["query"], limit=self.limit_per_query, page=page)
        ep_papers = self.epmc.search_papers(topic["query"], limit=self.limit_per_query) if page == 1 else []
        merged = merge_and_deduplicate(oa_papers, ep_papers)
        added = self.index.ingest_papers(merged, source=f"miner:{topic['domain']}:p{page}")

        state["topic_pages"][tid] = page + 1
        state["total_ingested_records"] = int(state.get("total_ingested_records", 0)) + added
        state["last_topic_id"] = tid
        state["last_run_utc"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
        self._save_state(state)
        return added

    def run_once(self, *, log_stream=None) -> Dict[str, Any]:
        """Run one full pass (1 page per topic) across all configured domain topics."""
        state = self._load_state()
        cycle_added = 0
        topic_errors = 0
        for topic in self.topics:
            if self._stop_requested:
                break
            try:
                added = self.mine_topic_step(topic, state)
                cycle_added += added
                if log_stream is not None:
                    print(
                        f"[{state['last_run_utc']}] {topic['id']} ({topic['domain']}) -> +{added} "
                        f"(index total: {self.index.stats()['paper_count']})",
                        file=log_stream,
                        flush=True,
                    )
            except Exception as exc:
                topic_errors += 1
                state["errors_count"] = int(state.get("errors_count", 0)) + 1
                state["last_error"] = f"{topic['id']}: {type(exc).__name__}: {exc}"
                self._save_state(state)
                if log_stream is not None:
                    print(f"[WARN] {state['last_error']}", file=log_stream, flush=True)
                self._sleep(min(30.0, max(2.0, self.delay_seconds * 4.0)))
            if not self._stop_requested and self.delay_seconds > 0:
                self._sleep(self.delay_seconds)

        state["cycles_completed"] = int(state.get("cycles_completed", 0)) + 1
        state["last_run_utc"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
        vectors_synced = 0
        if self.auto_sync_vectors:
            try:
                from .vector_store import sync_from_literature_index
                vrep = sync_from_literature_index(db_path=self.db_path)
                vectors_synced = int(vrep.get("synced", 0))
                state["last_vector_count"] = int(vrep["stats"]["vector_count"])
            except Exception as exc:
                state["last_vector_error"] = f"{type(exc).__name__}: {exc}"
        self._save_state(state)
        return {
            "ok": True,
            "status": "exploratory_hypothesis_seed",
            "topics_processed": len(self.topics),
            "cycle_added": cycle_added,
            "topic_errors": topic_errors,
            "vectors_synced": vectors_synced,
            "stats": self.index.stats(),
            "state_path": str(self.state_path),
            "cycles_completed": state["cycles_completed"],
        }

    def run_forever(self, *, max_cycles: Optional[int] = None, log_stream=None) -> int:
        """Indefinite polite background mining loop with graceful SIGTERM/SIGINT shutdown."""
        out = log_stream if log_stream is not None else sys.stdout

        def _handle_stop(_signum, _frame):
            self._stop_requested = True
            print("[miner] Shutdown signal received; finishing current step cleanly.", file=out, flush=True)

        try:
            signal.signal(signal.SIGTERM, _handle_stop)
            signal.signal(signal.SIGINT, _handle_stop)
        except ValueError:
            pass  # non-main thread in tests

        done = 0
        while not self._stop_requested:
            rep = self.run_once(log_stream=out)
            done += 1
            print(
                f"[miner] Cycle {rep['cycles_completed']} complete: +{rep['cycle_added']} records, "
                f"index={rep['stats']['paper_count']} papers, errors={rep['topic_errors']}",
                file=out,
                flush=True,
            )
            if max_cycles is not None and done >= max_cycles:
                break
            if not self._stop_requested and self.cycle_sleep_seconds > 0:
                # Sleep in short increments so SIGTERM exits promptly
                remaining = self.cycle_sleep_seconds
                while remaining > 0 and not self._stop_requested:
                    step = min(5.0, remaining)
                    self._sleep(step)
                    remaining -= step
        return 0
