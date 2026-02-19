from __future__ import annotations

from datetime import datetime, timezone

import pytest

from news.cache import CacheStore
from news.config import AppConfig, Settings
from news.models import Cluster, FilterOptions, PipelineOptions
from news.summarize import build_local_summary, run_pipeline, select_representative_items


def test_select_representative_items_prefers_recent(make_item):
    old = make_item(id="1", title="Older", published_dt=datetime(2023, 1, 1, tzinfo=timezone.utc))
    recent = make_item(id="2", title="Recent story", published_dt=datetime(2024, 1, 1, tzinfo=timezone.utc))
    short = make_item(id="3", title="A", published_dt=datetime(2024, 1, 1, tzinfo=timezone.utc))
    cluster = Cluster(cluster_id="c1", items=[old, recent, short], keywords=[])
    selected = select_representative_items(cluster, limit=2)
    assert [item.id for item in selected] == [short.id, recent.id]


def test_local_summary_structure(make_item):
    items = [
        make_item(id="1", title="Story one", source="A"),
        make_item(id="2", title="Story two", source="B"),
    ]
    cluster = Cluster(cluster_id="c1", items=items, keywords=[])
    text = build_local_summary(cluster, items)
    assert text.startswith("What happened:")
    assert text.count("- ") >= 3
    assert "Sources:" in text


def test_run_pipeline_respects_cache(tmp_path, make_item, monkeypatch):
    config = AppConfig(settings=Settings(cache_dir=str(tmp_path / ".cache")), feeds=[])
    cache = CacheStore(config.ensure_cache_dir(tmp_path))
    items = [make_item(id="1", link="https://example.com/a"), make_item(id="2", link="https://example.com/b")]

    monkeypatch.setattr("news.summarize.fetch_all_feeds", lambda *args, **kwargs: items)
    monkeypatch.setattr("news.summarize.dedupe_items", lambda data: data)
    monkeypatch.setattr("news.summarize.apply_filters", lambda data, opts: data)
    monkeypatch.setattr("news.cluster.cluster_items", lambda items, similarity_threshold, max_items: [
        Cluster(cluster_id="c1", items=list(items), keywords=[])
    ])
    monkeypatch.setattr("news.summarize._summarize_clusters", lambda clusters, llm: False)

    options = PipelineOptions(filters=FilterOptions())
    first = run_pipeline(config, cache, options)
    assert len(first.items) == 2

    second = run_pipeline(config, cache, options)
    assert len(second.items) == 0
