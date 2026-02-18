from __future__ import annotations

from datetime import datetime
from typing import Iterable, Sequence
from urllib.parse import urlparse

from .models import FilterOptions, NewsItem


class FilterError(RuntimeError):
    pass


def apply_filters(items: Sequence[NewsItem], options: FilterOptions) -> list[NewsItem]:
    opts = options.normalized()
    filtered: list[NewsItem] = []
    for item in items:
        if opts.since and item.published_dt and item.published_dt < opts.since:
            continue
        if opts.include and not _matches_keywords(item, opts.include):
            continue
        if opts.exclude and _matches_keywords(item, opts.exclude):
            continue
        if opts.domains and not _matches_domain(item, opts.domains):
            continue
        if opts.tags and not _matches_tags(item, opts.tags):
            continue
        filtered.append(item)
        if opts.max_items and len(filtered) >= opts.max_items:
            break
    return filtered


def _matches_keywords(item: NewsItem, keywords: Iterable[str]) -> bool:
    text = item.text_blob().lower()
    return any(keyword in text for keyword in keywords)


def _matches_domain(item: NewsItem, domains: Iterable[str]) -> bool:
    host = _extract_host(item.link)
    if not host:
        return False
    host = host.lower()
    return any(host == domain or host.endswith(f".{domain}") for domain in domains)


def _matches_tags(item: NewsItem, tags: Iterable[str]) -> bool:
    item_tags = {tag.lower() for tag in item.tags}
    return any(tag in item_tags for tag in tags)


def _extract_host(url: str) -> str:
    try:
        return urlparse(url).hostname or ""
    except ValueError:
        return ""
