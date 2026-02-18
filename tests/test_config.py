from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from news.config import load_config, parse_duration, parse_since_window


def test_load_config(tmp_path):
    cfg = tmp_path / "feeds.yaml"
    cfg.write_text(
        """
settings:
  user_agent: test-agent
  cache_dir: cache
feeds:
  - name: Test Feed
    url: https://example.com/rss
    tags: [tech]
"""
    )
    result = load_config(cfg)
    assert result.config.settings.user_agent == "test-agent"
    assert result.config.feeds[0].name == "Test Feed"


def test_parse_since_window_and_duration():
    now = datetime(2024, 1, 2, tzinfo=timezone.utc)
    since = parse_since_window("24h", now=now)
    assert since == now - timedelta(hours=24)
    delta = parse_duration("15m")
    assert delta == timedelta(minutes=15)


@pytest.mark.parametrize("bad", ["", "h", "noop"])
def test_parse_duration_invalid(bad):
    with pytest.raises(ValueError):
        parse_duration(bad)
