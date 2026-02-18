from __future__ import annotations

from datetime import datetime, timedelta, timezone

from news.filter import apply_filters
from news.models import FilterOptions


def test_filter_include_exclude(make_item):
    items = [
        make_item(id="1", title="AI breakthrough"),
        make_item(id="2", title="Sports update"),
    ]
    opts = FilterOptions(include=("ai",), exclude=("sports",))
    filtered = apply_filters(items, opts)
    assert [item.id for item in filtered] == ["1"]


def test_filter_domain_and_tags(make_item):
    items = [
        make_item(id="1", link="https://news.example.com/a", tags=("tech",)),
        make_item(id="2", link="https://other.com/b", tags=("world",)),
    ]
    opts = FilterOptions(domains=("example.com",), tags=("tech",))
    filtered = apply_filters(items, opts)
    assert filtered[0].id == "1"


def test_filter_since_and_limit(make_item):
    now = datetime(2024, 1, 5, tzinfo=timezone.utc)
    recent = make_item(id="1", published_dt=now - timedelta(hours=1))
    old = make_item(id="2", published_dt=now - timedelta(days=3))
    opts = FilterOptions(since=now - timedelta(days=1), max_items=1)
    filtered = apply_filters([recent, old], opts)
    assert filtered == [recent]
