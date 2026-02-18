from __future__ import annotations

from news.dedupe import dedupe_items


def test_dedupe_same_link(make_item):
    items = [
        make_item(id="1", link="https://example.com/a"),
        make_item(id="2", link="https://example.com/a"),
    ]
    unique = dedupe_items(items)
    assert len(unique) == 1


def test_dedupe_similar_titles(make_item):
    items = [
        make_item(id="1", title="AI breakthrough at MIT", link="https://example.com/a"),
        make_item(id="2", title="MIT AI breakthroughs", link="https://example.com/b"),
    ]
    unique = dedupe_items(items)
    assert len(unique) == 1


def test_dedupe_strips_tracking_params(make_item):
    items = [
        make_item(id="1", title="Story A", link="https://example.com/a?utm_source=rss&utm_medium=feed&ref=tw"),
        make_item(id="2", title="Story A duplicate", link="https://example.com/a"),
        make_item(id="3", title="Completely different headline", link="https://example.com/a?session=123"),
    ]
    unique = dedupe_items(items)
    assert [item.id for item in unique] == ["1", "3"]
