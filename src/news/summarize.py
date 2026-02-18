from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
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
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


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
    llm_client = llm if (llm and opts.llm_enabled) else None
    llm_used = _summarize_clusters(clusters, llm_client)
    cache.mark_clusters(clusters)
    return PipelineResult(clusters=clusters, items=filtered, llm_used=llm_used)


def _summarize_clusters(clusters: Sequence[Cluster], llm: OllamaClient | None) -> bool:
    used = False
    for cluster in clusters:
        representative = select_representative_items(cluster)
        summary_text: str | None = None
        try:
            if llm:
                summary_text = llm.summarize_cluster(cluster, representative)
                used = True
        except OllamaError as exc:
            log.warning("Ollama summarization failed: %s", exc)
        if not summary_text:
            summary_text = build_local_summary(cluster, representative)
        cluster.summary = summary_text
    return used


def select_representative_items(cluster: Cluster, limit: int = 5) -> list[NewsItem]:
    if not cluster.items:
        return []

    def sort_key(item: NewsItem) -> tuple[float, int, str]:
        ts = item.published_dt or EPOCH
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        timestamp = ts.timestamp()
        return (-timestamp, len(item.title), item.title.lower())

    ordered = sorted(cluster.items, key=sort_key)
    return ordered[:limit]


def build_local_summary(cluster: Cluster, items: Sequence[NewsItem]) -> str:
    if not items:
        return "\n".join(
            [
                "What happened: No supporting stories available yet.",
                "- Awaiting additional reporting.",
                "- Check feeds for updates.",
                "- No confirmed facts.",
                "Sources: none",
            ]
        )
    primary = items[0]
    bullets = [f"- {item.source}: {item.title}" for item in items]
    bullets = bullets[:6]
    filler = "- Additional context unavailable."
    while len(bullets) < 3:
        bullets.append(filler)
    sources = "; ".join(sorted({item.source for item in items}))
    return "\n".join(
        [
            f"What happened: {primary.title}",
            *bullets,
            f"Sources: {sources or 'none'}",
        ]
    )
