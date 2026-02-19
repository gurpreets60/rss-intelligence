from __future__ import annotations

import pytest
import requests

from news.config import FeedConfig, Settings
from news.feeds import FeedError, fetch_feed

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


class DummyResponse:
    def __init__(self, content: str):
        self.content = content.encode()

    def raise_for_status(self) -> None:
        return None


class DummySession:
    def __init__(self, content: str, failures: int = 0):
        self.content = content
        self.closed = False
        self.failures = failures

    def get(self, *_args, **_kwargs):
        if self.failures > 0:
            self.failures -= 1
            raise requests.RequestException("temporary failure")
        return DummyResponse(self.content)

    def close(self):
        self.closed = True


def test_fetch_feed_parses_entries():
    feed = FeedConfig(name="Example", url="https://example.com/rss", tags=["tech"])
    settings = Settings()
    session = DummySession(SAMPLE_FEED)
    items = fetch_feed(feed, settings, session=session)
    assert len(items) == 2
    assert items[0].title == "Story One"
    assert "tech" in items[0].tags


def test_fetch_feed_retries_on_failure():
    feed = FeedConfig(name="Example", url="https://example.com/rss", tags=["tech"])
    settings = Settings()
    session = DummySession(SAMPLE_FEED, failures=1)
    items = fetch_feed(feed, settings, session=session, max_retries=2)
    assert len(items) == 2


class ErrorSession(DummySession):
    def get(self, *_args, **_kwargs):
        raise requests.RequestException("boom")


def test_fetch_feed_raises_feed_error_on_http_failure():
    feed = FeedConfig(name="Example", url="https://example.com/rss")
    settings = Settings()
    with pytest.raises(FeedError):
        fetch_feed(feed, settings, session=ErrorSession(SAMPLE_FEED))
