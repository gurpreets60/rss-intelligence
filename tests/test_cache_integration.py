from __future__ import annotations

from pathlib import Path

import pytest

from news.cache import CacheStore
from news.config import AppConfig, FeedConfig, Settings
from news.models import FilterOptions, PipelineOptions
from news.summarize import PipelineResult, run_pipeline


class DummySession:
    def __init__(self, responses):
        self.responses = responses
        self.index = 0

    def get(self, *_args, **_kwargs):
        content = self.responses[self.index]
        self.index += 1
        return type("Resp", (), {"content": content.encode(), "raise_for_status": lambda self: None})()

    def close(self):
        return None


def _session_factory(responses):
    def factory():
        return DummySession(responses)

    return factory


@pytest.fixture
def feeds_config(tmp_path):
    config = AppConfig(
        settings=Settings(cache_dir=str(tmp_path / ".cache")),
        feeds=[FeedConfig(name="Example", url="https://example.com/rss", tags=["tech"])],
    )
    return config


SAMPLE_FEED = """<?xml version='1.0' encoding='UTF-8'?>
<rss version='2.0'>
  <channel>
    <title>Example Feed</title>
    <item>
      <title>Story One</title>
      <link>https://example.com/one</link>
      <guid>1</guid>
      <description>Summary 1</description>
    </item>
    <item>
      <title>Story Two</title>
      <link>https://example.com/two</link>
      <guid>2</guid>
      <description>Summary 2</description>
    </item>
  </channel>
</rss>
"""


def test_cache_filters_seen_links(tmp_path, feeds_config):
    cache_dir = tmp_path / "state"
    cache = CacheStore(cache_dir)
    options = PipelineOptions(filters=FilterOptions())

    def fake_fetch_all(feeds, settings, session_factory=None):  # noqa: ARG001
        return []

    # TODO: replace with run_pipeline once we can inject fetch behavior
