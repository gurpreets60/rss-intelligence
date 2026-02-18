from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Sequence

import requests

from .cache import CacheStore
from .cluster import cluster_items
from .config import AppConfig
from .dedupe import dedupe_items
from .feeds import fetch_all_feeds
from .filter import apply_filters
from .models import Cluster, NewsItem, PipelineOptions
from .ollama_client import OllamaClient, OllamaError

log = logging.getLogger(__name__)


@dataclass(slots=True)
class PipelineResult:
    clusters: list[Cluster]
    items: list[NewsItem]
    llm_used: bool


SessionFactory = Callable[[], requests.Session]


def run_pipeline(
    app_config: AppConfig,
    cache: CacheStore,
    options: PipelineOptions,
    *,
    session_factory: SessionFactory | None = None,
    llm: OllamaClient | None = None,
) -> PipelineResult:
    opts = options.clamp()
    settings = app_config.settings
    items = fetch_all_feeds(app_config.feeds, settings, session_factory=session_factory)
    deduped = dedupe_items(items)
    unseen = cache.filter_new_items(deduped, mark=False)
    filtered = apply_filters(unseen, opts.filters)
    if opts.max_items is not None:
        filtered = filtered[: opts.max_items]
    cache.mark_items(filtered)

    clusters = cluster_items(
        filtered,
        similarity_threshold=opts.threshold,
        max_items=opts.max_items,
    )
    llm_used = False
    if clusters and llm and opts.llm_enabled:
        llm_used = _summarize_clusters(clusters, llm)
    cache.mark_clusters(clusters)
    return PipelineResult(clusters=clusters, items=filtered, llm_used=llm_used)


def _summarize_clusters(clusters: Sequence[Cluster], llm: OllamaClient) -> bool:
    used = False
    for cluster in clusters:
        try:
            cluster.summary = llm.summarize_cluster(cluster)
            used = True
        except OllamaError as exc:
            log.warning("Ollama summarization failed: %s", exc)
            break
    return used
