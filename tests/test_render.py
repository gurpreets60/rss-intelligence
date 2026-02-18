from __future__ import annotations

from datetime import datetime, timezone

from news.render import format_timestamp


def test_format_timestamp_with_value():
    dt = datetime(2024, 1, 1, 15, 30, tzinfo=timezone.utc)
    assert format_timestamp(dt) == "2024-01-01 15:30 UTC"


def test_format_timestamp_none():
    assert format_timestamp(None) == "(no timestamp)"
