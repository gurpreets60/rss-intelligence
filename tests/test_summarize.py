from __future__ import annotations

from datetime import datetime, timezone

import pytest

from news.models import Cluster
from news.summarize import build_local_summary, select_representative_items


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
