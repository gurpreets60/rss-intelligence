from __future__ import annotations

from datetime import datetime, timezone

import news.render as render
from news.models import Cluster, NewsItem


def test_format_timestamp_with_value():
    dt = datetime(2024, 1, 1, 15, 30, tzinfo=timezone.utc)
    assert render.format_timestamp(dt) == "2024-01-01 15:30 UTC"


def test_format_timestamp_none():
    assert render.format_timestamp(None) == "(no timestamp)"


def test_set_color_updates_console():
    render.set_color(True)
    assert render.console.no_color is False
    render.set_color(False)
    assert render.console.no_color is True


def test_print_clusters_limits_items(capsys):
    render.set_color(False)
    items = [
        NewsItem(id=str(i), title=f"Story {i}", link=f"https://e/{i}", source="Src", tags=[], authors=[])
        for i in range(10)
    ]
    cluster = Cluster(cluster_id="c1", items=items, keywords=["test"])
    render.print_clusters([cluster], max_items=3)
    captured = capsys.readouterr().out
    assert "Story 0" in captured and "Story 3" not in captured
