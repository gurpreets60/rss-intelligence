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
