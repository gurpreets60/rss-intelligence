from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Sequence

import feedparser
import requests

from .config import FeedConfig, Settings
from .models import NewsItem

log = logging.getLogger(__name__)


class FeedError(RuntimeError):
    pass


def fetch_feed(
    feed: FeedConfig,
    settings: Settings,
    *,
    session: requests.Session | None = None,
) -> list[NewsItem]:
    sess = session or requests.Session()
    try:
        response = sess.get(
            feed.url,
            headers={"User-Agent": settings.user_agent},
            timeout=settings.timeout_s,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        log.warning("Failed to fetch %s: %s", feed.url, exc)
        raise FeedError(str(exc)) from exc
    finally:
        if session is None:
            sess.close()

    parsed = feedparser.parse(response.content)
    if parsed.bozo and parsed.bozo_exception:
        log.warning("Feed parser warning for %s: %s", feed.url, parsed.bozo_exception)

    items: list[NewsItem] = []
    for entry in parsed.entries[: settings.max_items_per_feed]:
        item = _entry_to_news_item(feed, entry)
        if item:
            items.append(item)
    return items


def fetch_all_feeds(
    feeds: Sequence[FeedConfig],
    settings: Settings,
    session_factory: Callable[[], requests.Session] | None = None,
) -> list[NewsItem]:
    items: list[NewsItem] = []
    for feed in feeds:
        sess = session_factory() if session_factory else None
        try:
            items.extend(fetch_feed(feed, settings, session=sess))
        except FeedError:
            continue
        finally:
            if sess is not None:
                sess.close()
    return items


def _entry_to_news_item(feed: FeedConfig, entry: Any) -> NewsItem | None:
    title = entry.get("title") or "Untitled"
    link = entry.get("link") or entry.get("id")
    if not link:
        return None
    entry_id = entry.get("id") or link
    published = _parse_datetime(entry)
    summary = entry.get("summary")
    content = _extract_content(entry)
    entry_tags = [tag.get("term", "").lower() for tag in entry.get("tags", [])]
    tags = tuple({tag for tag in (*entry_tags, *feed.tags) if tag})
    authors = tuple(author.get("name", "") for author in entry.get("authors", []))
    return NewsItem(
        id=str(entry_id),
        title=title.strip(),
        link=link.strip(),
        source=feed.name,
        published=published,
        summary=summary.strip() if summary else None,
        content=content,
        tags=tuple(tag for tag in tags if tag),
        authors=tuple(author for author in authors if author),
    )


def _parse_datetime(entry: Any) -> datetime | None:
    struct_time = entry.get("published_parsed") or entry.get("updated_parsed")
    if not struct_time:
        return None
    return datetime(*struct_time[:6], tzinfo=timezone.utc)


def _extract_content(entry: Any) -> str | None:
    contents = entry.get("content")
    if isinstance(contents, list) and contents:
        text = contents[0].get("value")
        if text:
            return text.strip()
    return None
